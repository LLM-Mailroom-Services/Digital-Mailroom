"""Independent DMR-091 frozen-source edge probes; no production substitutions."""
import os, json, shutil, types, subprocess, threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import pytest
import yaml
from test_job_generation_residuals import source_root, sdk, spec_file, worker_body  # noqa: F401 - pytest fixtures
from mailroom_sandbox import runtime
from mailroom_sandbox.cli import main
from mailroom_sandbox.job import preflight, runner, remote
from mailroom_sandbox.job.checkpoint import RunStore
from mailroom_sandbox.eval import experiment_log
pytestmark=pytest.mark.usefixtures('job_data_dir')

@pytest.fixture
def http_fixture():
 calls=[]
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*a):pass
  def do_GET(self):
   calls.append(self.path)
   if self.path=='/v1/models':code,body=200,{'data':[{'id':'engine-model'}]}
   else:code,body=400,{'error':'wrong configured endpoint'}
   self.send_response(code);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(body).encode())
  def do_POST(self):
   calls.append(self.path);self.rfile.read(int(self.headers.get('Content-Length') or 0));self.send_response(200);self.end_headers();self.wfile.write(b'{}')
 server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
 thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
 yield f'http://127.0.0.1:{server.server_port}',calls
 server.shutdown();server.server_close();thread.join(timeout=3)

def test_cli_loads_dotenv_endpoint_before_live_preflight(tmp_path,source_root,monkeypatch,http_fixture):
 monkeypatch.delenv("SANDBOX_SKIP_DOTENV", raising=False)
 spec,path,store,_=spec_file(tmp_path,source_root)
 spec.job.mock=True;path.write_text(yaml.safe_dump(spec.model_dump(mode='json')))
 base,calls=http_fixture
 profile_path=source_root/'config/profiles/ollama.yaml'
 profile=yaml.safe_load(profile_path.read_text());profile['base_url']=base+'/wrong';profile_path.write_text(yaml.safe_dump(profile))
 monkeypatch.delenv('VLLM_BASE_URL',raising=False)
 (source_root/'.env').write_text('VLLM_BASE_URL='+base+'/v1\n')
 rc=main(['run','start','--config',str(path),'--live','--offline'])
 print('DOTENV_ENDPOINT',json.dumps({'rc':rc,'requests':calls,'lock_exists':store.lock_path.exists()}))
 assert rc==0 and '/v1/models' in calls

def test_cli_loads_dotenv_trace_keys_before_preflight(tmp_path,source_root,monkeypatch,http_fixture):
 monkeypatch.delenv("SANDBOX_SKIP_DOTENV", raising=False)
 spec,path,store,_=spec_file(tmp_path,source_root)
 base,calls=http_fixture
 spec.job.mock=True;spec.trace.sink='langfuse';spec.trace.endpoint=base+'/api/public/otel';path.write_text(yaml.safe_dump(spec.model_dump(mode='json')))
 # The SDK guard is not under test here; CI installs [dev] without langfuse.
 real_find_spec=preflight.find_spec
 monkeypatch.setattr(preflight,'find_spec',lambda name:object() if name=='langfuse' else real_find_spec(name))
 for key in ('LANGFUSE_PUBLIC_KEY','LANGFUSE_SECRET_KEY','LANGFUSE_INIT_PROJECT_PUBLIC_KEY','LANGFUSE_INIT_PROJECT_SECRET_KEY'):
  monkeypatch.delenv(key,raising=False)
 (source_root/'.env').write_text('LANGFUSE_PUBLIC_KEY=pk-review-fixture\nLANGFUSE_SECRET_KEY=sk-review-fixture\nLANGFUSE_HOST='+base+'\n')
 rc=main(['run','start','--config',str(path)])
 print('DOTENV_TRACE',json.dumps({'rc':rc,'requests':calls,'lock_exists':store.lock_path.exists()}))
 assert rc==0

def test_legacy_reuse_refuses_foreign_record_task(tmp_path,source_root,sdk,monkeypatch):
 from api_evals.invoke import run_task
 spec,path,store,_=spec_file(tmp_path,source_root)
 assert preflight.preflight(spec,offline=True)['status']=='prepared'
 lock=store.read_lock();lock.pop('generation_id');store.lock_path.write_text(json.dumps(lock));store.write_checkpoint(state='prepared',cursor=0,total=1)
 with store.acquire():assert runner.run_job(store)['state']=='done'
 record=experiment_log.load()[-1];record.pop('run_generation');record.pop('run_state');record.pop('run_task',None);record['timestamp']=store.read_checkpoint()['updated_at']
 experiment_log.jsonl_path().write_text(json.dumps(record)+'\n')
 monkeypatch.delenv('OPENROUTER_API_KEY',raising=False)
 assert run_task(path,prices=(1.,2.))['resumed'] is True
 record['task']='unrelated-agent';record['scores']={'accuracy':-99}
 experiment_log.jsonl_path().write_text(json.dumps(record)+'\n')
 try:result=run_task(path,prices=(1.,2.))
 except RuntimeError:return
 print('LEGACY_TASK',json.dumps({'task':result['record']['task'],'lock_task':lock['task'],'scores':result['scores'],'resumed':result['resumed']}))
 pytest.fail('foreign-task legacy record reused')

@pytest.mark.parametrize('task',['isolated','extract','chained','pipeline'])
def test_whole_task_alias_has_reusable_task_identity(tmp_path,source_root,monkeypatch,task):
 from api_evals.invoke import run_task
 spec,path,store,_=spec_file(tmp_path,source_root,task=task)
 spec.job.mock=True;path.write_text(yaml.safe_dump(spec.model_dump(mode='json')))
 assert preflight.preflight(spec,offline=True)['status']=='prepared'
 with store.acquire():result=runner.run_job(store)
 print('ALIAS',json.dumps({'task':task,'state':result['state'],'record_task':experiment_log.load()[-1].get('task')}))
 assert result['state']=='done'
 monkeypatch.delenv('OPENROUTER_API_KEY',raising=False)
 assert run_task(path,prices=(1.,2.))['resumed'] is True

def test_named_posture_precedence_freezes_complete_map(tmp_path,source_root,monkeypatch):
 spec,_,_,_=spec_file(tmp_path,source_root)
 runid='sand42-50-merger-specialist-awq-1l4-c8'
 monkeypatch.setenv('SANDBOX_AGENT_KNOBS',json.dumps({'merger_agreement_specialist':{'model':'hostile-env','max_tokens':1},'sorter':{'model':'also-ignored'}}))
 assert preflight.preflight(spec,run_id=runid,offline=True)['status']=='prepared'
 from mailroom_sandbox.job.spec import run_dir
 store=RunStore(run_dir(runid))
 expected={'merger_agreement_specialist':{'max_tokens':6144,'max_input_chars':54000,'temperature':0.7,'top_p':0.8,'top_k':20,'presence_penalty':1.0,'length_retries':1,'chunk_chars':47000,'overlap_chars':6500}}
 assert store.verify_generation()['agent_knobs']==expected
 monkeypatch.setenv('SANDBOX_AGENT_KNOBS','{"sorter":{"model":"later-model"}}')
 with runtime.locked_runtime(store.read_lock(),store.read_prompt_lock()):
  assert runtime.activate().agent_knobs==expected

def test_cli_loads_dotenv_before_resolving_pinned_langfuse_prompt(tmp_path,source_root,monkeypatch):
 monkeypatch.delenv("SANDBOX_SKIP_DOTENV", raising=False)
 langfuse=pytest.importorskip('langfuse')
 spec,path,store,_=spec_file(tmp_path,source_root)
 spec.job.mock=True
 spec.prompt={'agents':{'sorter':{'source':'langfuse','version':7}}}
 path.write_text(yaml.safe_dump(spec.model_dump(mode='json')))
 for key in ('LANGFUSE_PUBLIC_KEY','LANGFUSE_SECRET_KEY','LANGFUSE_INIT_PROJECT_PUBLIC_KEY','LANGFUSE_INIT_PROJECT_SECRET_KEY'):
  monkeypatch.delenv(key,raising=False)
 (source_root/'.env').write_text('LANGFUSE_PUBLIC_KEY=pk-review-fixture\nLANGFUSE_SECRET_KEY=sk-review-fixture\n')
 calls=[]
 class SDK:
  def __init__(self,*a,**kw):pass
  def get_prompt(self,name,*,version=None,label=None):
   calls.append((name,version));return types.SimpleNamespace(prompt=(source_root/'config/prompts/sorter_local_v0.txt').read_text()+'\nDOTENV PINNED PROMPT\n',version=7)
 monkeypatch.setattr(langfuse,'Langfuse',SDK)
 try:rc=main(['run','start','--config',str(path)])
 except RuntimeError as exc:
  print('DOTENV_PROMPT',json.dumps({'error':str(exc),'sdk_calls':calls}))
  raise
 print('DOTENV_PROMPT',json.dumps({'rc':rc,'sdk_calls':calls}))
 assert rc==0
 assert calls==[('mailroom-sorter',7)]
 assert 'DOTENV PINNED PROMPT' in store.read_lock()['prompt']['agents']['sorter']['text']


@pytest.fixture
def modal_fs(tmp_path, monkeypatch):
    """SDK/CLI transport boundary with distinct local and remote filesystems.

    Respect full remote paths, missing files, no-force collisions and SDK
    polling failures; run the actual deployed worker and RunStore implementation.
    """
    volume = tmp_path / 'volume'
    volume.mkdir()
    state = {}; calls = {}; spawned = []; transfers = []; commits = []
    real_run = subprocess.run
    class PollTimeout(Exception): pass
    class FunctionTimeoutError(Exception): pass
    class OutputExpiredError(Exception): pass
    class RemoteError(Exception): pass
    class Call:
        def __init__(self, call_id): self.object_id = call_id
        def get_call_graph(self):
            status = calls[self.object_id]
            if isinstance(status, Exception): raise status
            return [types.SimpleNamespace(status=types.SimpleNamespace(name=status))]
        def get(self, timeout=None):
            assert timeout == 0
            status = calls[self.object_id]
            if isinstance(status, Exception): raise status
            if status == 'RUNNING': raise PollTimeout('input unfinished')
            if status == 'TERMINATED': raise RemoteError('input terminated')
            return {'state': 'done'}
        def cancel(self, **kwargs): calls[self.object_id] = 'TERMINATED'
    class Fn:
        def spawn(self, payload):
            call_id = 'fc-' + str(len(spawned))
            spawned.append(dict(payload)); calls[call_id] = 'RUNNING'
            return Call(call_id)
    class Dict:
        def get(self, key, default=None): return state.get(key, default)
        def put(self, key, value): state[key] = dict(value)
    boundary = types.SimpleNamespace(
        Function=types.SimpleNamespace(from_name=lambda *a: Fn()),
        FunctionCall=types.SimpleNamespace(from_id=Call),
        Dict=types.SimpleNamespace(from_name=lambda *a, **kw: Dict()),
        exception=types.SimpleNamespace(FunctionTimeoutError=FunctionTimeoutError,
            OutputExpiredError=OutputExpiredError, RemoteError=RemoteError))
    monkeypatch.setattr(remote, '_modal', lambda: boundary)
    def modal_cli(cmd, *args, **kwargs):
        if cmd[:2] != ['modal', 'volume']: return real_run(cmd, *args, **kwargs)
        verb = cmd[2]; transfers.append(list(cmd))
        def result(rc=0, error=''): return types.SimpleNamespace(returncode=rc, stdout='', stderr=error)
        if verb == 'get':
            source = volume / cmd[-2].removeprefix('/runs/')
            dest = Path(cmd[-1]); dest.mkdir(parents=True, exist_ok=True)
            if not source.exists(): return result(1, 'not found')
            if source.is_dir(): shutil.copytree(source, dest/source.name)
            else: shutil.copy2(source, dest/source.name)
            return result()
        assert verb == 'put'
        source = Path(cmd[-2]); dest = volume / cmd[-1].removeprefix('/runs/')
        if dest.exists() and '--force' not in cmd: return result(1, 'destination exists')
        shutil.copytree(source, dest, dirs_exist_ok='--force' in cmd)
        return result()
    monkeypatch.setattr(subprocess, 'run', modal_cli)
    def worker(payload):
        # Existing helper replaces only Modal deployment objects, not product code.
        dummy = RunStore(volume/payload['run_id'])
        body = worker_body(monkeypatch, dummy)
        body.__globals__['SANDBOX_ROOT'] = os.environ['SANDBOX_ROOT']
        body.__globals__['modal'].Dict = boundary.Dict
        body.__globals__['runs_volume'] = types.SimpleNamespace(
            reload=lambda: commits.append('reload'), commit=lambda: commits.append('commit'))
        return body(payload)
    return types.SimpleNamespace(volume=volume, state=state, calls=calls, spawned=spawned,
        transfers=transfers, worker=worker, commits=commits, boundary=boundary)


def reset_pair(tmp_path, source_root, sdk, *, modal=False):
    spec, path, store, prompt = spec_file(tmp_path, source_root)
    if modal:
        spec.job.mode = 'modal'; path.write_text(yaml.safe_dump(spec.model_dump(mode='json')))
    assert preflight.preflight(spec, offline=True)['status'] == 'prepared'
    with store.acquire(): assert runner.run_job(store)['state'] == 'done'
    old = store.read_lock()
    snapshot = tmp_path/'old'/store.run_id; shutil.copytree(store.dir, snapshot)
    prompt.write_text(prompt.read_text().replace('GENERATION ONE SENTINEL','GENERATION TWO SENTINEL'))
    assert preflight.preflight(spec, offline=True, force=True)['status'] == 'prepared'
    assert old['spec_hash'] == store.read_lock()['spec_hash']
    assert old['generation_id'] != store.read_lock()['generation_id']
    return spec, path, store, old, snapshot


def test_remote_reset_same_spec_executes_new_generation(tmp_path, source_root, sdk, modal_fs):
    spec, path, store, old, snapshot = reset_pair(tmp_path,source_root,sdk)
    legacy = modal_fs.volume/store.run_id; shutil.copytree(snapshot,legacy)
    old_bytes = {p.name:p.read_bytes() for p in legacy.iterdir() if p.is_file()}
    action = remote.ensure_running(store)
    payload = modal_fs.spawned[-1]
    assert payload['run_generation']['prompt_text_sha'] == store.read_lock()['prompt_text_sha']
    assert payload['generation_id'] == store.read_lock()['generation_id']
    assert payload['run_path'] != store.run_id
    before = len(sdk['requests']); modal_fs.worker(payload)
    assert len(sdk['requests'])-before == 2
    assert 'GENERATION TWO SENTINEL' in json.dumps(sdk['requests'][before:])
    new_remote = RunStore(modal_fs.volume/payload['run_path'])
    assert new_remote.state() == 'done'
    assert new_remote.read_lock() == store.read_lock()
    assert modal_fs.commits[0] == 'reload'
    assert {p.name:p.read_bytes() for p in legacy.iterdir() if p.is_file()} == old_bytes
    assert all('--force' not in cmd for cmd in modal_fs.transfers if cmd[2]=='put')
    assert remote.read_progress(store)['generation_id'] == store.read_lock()['generation_id']
    assert remote.pull_run_dir(store) == (0,'')
    assert store.state() == 'done'
    assert store.read_checkpoint()['remote']['call_id'] == action['call_id']


def test_remote_status_cannot_overwrite_reset_generation_from_old_done_cache(tmp_path,source_root,sdk,modal_fs):
    _,path,store,old,snapshot = reset_pair(tmp_path,source_root,sdk,modal=True)
    shutil.copytree(snapshot, modal_fs.volume/store.run_id)
    modal_fs.state[store.run_id] = {'run_id':store.run_id,'spec_hash':old['spec_hash'],
        'generation_id':old['generation_id'],'state':'done','cursor':1,'total':1}
    remote.ensure_running(store)
    before = store.lock_path.read_bytes()
    assert main(['run','status','--run-id',store.run_id]) == 0
    assert store.lock_path.read_bytes() == before and store.state() == 'running'
    assert not any(cmd[-2] == '/runs/'+store.run_id for cmd in modal_fs.transfers)


@pytest.mark.parametrize('damage',['old_generation','dataset','prompt','checkpoint','log'])
def test_pull_validates_staging_before_any_local_replace(tmp_path,source_root,sdk,modal_fs,damage):
    _,_,store,old,snapshot = reset_pair(tmp_path,source_root,sdk,modal=True)
    remote.ensure_running(store); payload=modal_fs.spawned[-1]
    remote_dir=modal_fs.volume/payload['run_path']
    modal_fs.worker(payload)
    if damage=='old_generation':
        shutil.rmtree(remote_dir);shutil.copytree(snapshot,remote_dir)
    elif damage=='dataset': (remote_dir/'dataset.jsonl').write_text('foreign\n')
    elif damage=='prompt': (remote_dir/'prompt.lock.json').write_text('{}')
    elif damage=='checkpoint': (remote_dir/'checkpoint.json').write_text('{')
    else: (remote_dir/'experiment_log.jsonl').write_text('{')
    before={p.name:p.read_bytes() for p in store.dir.iterdir() if p.is_file()}
    rc,err=remote.pull_run_dir(store)
    assert rc==1 and 'generation validation failed' in err
    assert {p.name:p.read_bytes() for p in store.dir.iterdir() if p.is_file()}==before


def test_worker_refuses_wrong_expectation_before_provider_or_progress(tmp_path,source_root,sdk,modal_fs):
    spec,_,store,_=spec_file(tmp_path,source_root)
    assert preflight.preflight(spec,offline=True)['status']=='prepared'
    remote.ensure_running(store); payload=dict(modal_fs.spawned[-1]);payload['generation_id']='foreign'
    with pytest.raises(RuntimeError,match='dispatch expectation'): modal_fs.worker(payload)
    assert sdk['requests']==[] and modal_fs.state=={}


@pytest.mark.parametrize('state',['prepared','running','paused','done','failed'])
def test_idle_local_cancel_does_not_poison_next_resume(tmp_path,source_root,sdk,state,capsys):
    spec,_,store,_=spec_file(tmp_path,source_root)
    assert preflight.preflight(spec,offline=True)['status']=='prepared'
    store.write_checkpoint(state=state,cursor=0,total=1)
    assert main(['run','cancel','--run-id',store.run_id])==0
    assert json.loads(capsys.readouterr().out)=={'run_id':store.run_id,'state':state,'detail':'no active local runner'}
    assert store.pending_cancel() is None
    assert store.state()==state
    if state in {'prepared','running','paused'}:
        assert main(['run','resume','--run-id',store.run_id])==0
        assert len(sdk['requests'])==2


@pytest.mark.parametrize('status,allowed',[('SUCCESS',True),('TERMINATED',True),('RUNNING',False),
    (OSError('transport unavailable'),False),(ValueError('ambiguous user error'),False)])
def test_force_remote_reset_requires_result_proof(tmp_path,source_root,modal_fs,status,allowed):
    spec,_,store,_=spec_file(tmp_path,source_root)
    assert preflight.preflight(spec,offline=True)['status']=='prepared'
    remote.ensure_running(store);call_id=store.read_checkpoint()['remote']['call_id']
    modal_fs.calls[call_id]=status
    before=store.lock_path.read_bytes()
    report=preflight.preflight(spec,offline=True,force=True)
    assert report['status']==('prepared' if allowed else 'busy_refused')
    if allowed: assert store.lock_path.read_bytes()!=before
    else: assert store.lock_path.read_bytes()==before


def test_matching_live_generation_attaches_without_upload_or_spawn(tmp_path,source_root,modal_fs):
    spec,_,store,_=spec_file(tmp_path,source_root)
    assert preflight.preflight(spec,offline=True)['status']=='prepared'
    first=remote.ensure_running(store);transfers=len(modal_fs.transfers)
    assert remote.ensure_running(store)=={'action':'attached','call_id':first['call_id']}
    assert len(modal_fs.spawned)==1 and len(modal_fs.transfers)==transfers


def test_legacy_matching_worker_progress_and_artifacts_still_finalize(tmp_path,source_root,sdk,modal_fs):
    spec,_,store,_=spec_file(tmp_path,source_root)
    assert preflight.preflight(spec,offline=True)['status']=='prepared'
    lock=store.read_lock();lock.pop('generation_id');store.lock_path.write_text(json.dumps(lock))
    store.write_checkpoint(state='prepared',cursor=0,total=1)
    with store.acquire():assert runner.run_job(store)['state']=='done'
    shutil.copytree(store.dir,modal_fs.volume/store.run_id)
    cp=store.read_checkpoint();cp['remote']={'call_id':'fc-old'};store.checkpoint_path.write_text(json.dumps(cp))
    modal_fs.calls['fc-old']='RUNNING'
    assert remote.ensure_running(store)['action']=='attached'
    modal_fs.state[store.run_id]={'run_id':store.run_id,'spec_hash':lock['spec_hash'],
        'state':'done','heartbeat_at':cp['updated_at']}
    assert remote.read_progress(store)['state']=='done'
    assert remote.pull_run_dir(store)==(0,'')
    assert not any(cmd[2]=='put' for cmd in modal_fs.transfers)


def test_generation_destination_mismatch_never_overwrites(tmp_path,source_root,sdk,modal_fs):
    _,_,store,old,snapshot=reset_pair(tmp_path,source_root,sdk)
    # Even an inconsistent content-addressed destination is refused, not seized.
    from mailroom_sandbox.job.remote import generation_path
    dest=modal_fs.volume/generation_path(store.read_lock());shutil.copytree(snapshot,dest)
    before=(dest/'spec.lock.json').read_bytes()
    with pytest.raises(RuntimeError,match='mismatched lock'):remote.ensure_running(store)
    assert (dest/'spec.lock.json').read_bytes()==before
    assert not modal_fs.spawned and not any(cmd[2]=='put' for cmd in modal_fs.transfers)


def test_finalization_filters_foreign_and_old_generation_records(tmp_path,source_root,sdk,modal_fs):
    from mailroom_sandbox.cli import _finalize_remote
    _,_,store,old,snapshot=reset_pair(tmp_path,source_root,sdk)
    remote.ensure_running(store);payload=modal_fs.spawned[-1];modal_fs.worker(payload)
    # Worker copied a global log containing A and B. Include a foreign task
    # with the otherwise correct generation and a distinctive poisoned score.
    path=modal_fs.volume/payload['run_path']/'experiment_log.jsonl'
    records=[json.loads(line) for line in path.read_text().splitlines()]
    current=next(rec for rec in records if rec.get('run_generation',{}).get('lock_sha256')==payload['run_generation']['lock_sha256'])
    bad=dict(current,task='unrelated-agent',scores={'accuracy':-99})
    path.write_text(path.read_text()+json.dumps(bad)+'\n')
    experiment_log.jsonl_path().write_text('')
    assert _finalize_remote(store) is True
    assert experiment_log.load()==[current]


def test_explicit_endpoint_environment_wins_dotenv(tmp_path,source_root,monkeypatch,http_fixture):
    spec,path,store,_=spec_file(tmp_path,source_root)
    spec.job.mock=True;path.write_text(yaml.safe_dump(spec.model_dump(mode='json')))
    base,calls=http_fixture
    monkeypatch.setenv('VLLM_BASE_URL',base+'/v1')
    (source_root/'.env').write_text('VLLM_BASE_URL='+base+'/wrong\n')
    assert main(['run','start','--config',str(path),'--live','--offline'])==0
    assert '/v1/models' in calls and '/wrong/v1/models' not in calls


@pytest.mark.parametrize('field',['task','run_task'])
def test_alias_reuse_keeps_foreign_task_rejection(tmp_path,source_root,monkeypatch,field):
    from api_evals.invoke import run_task
    spec,path,store,_=spec_file(tmp_path,source_root,task='isolated')
    spec.job.mock=True;path.write_text(yaml.safe_dump(spec.model_dump(mode='json')))
    assert preflight.preflight(spec,offline=True)['status']=='prepared'
    with store.acquire():assert runner.run_job(store)['state']=='done'
    record=experiment_log.load()[-1]
    assert record['run_task']=='isolated' and record['task']=='sorter'
    record[field]='unrelated-agent';experiment_log.jsonl_path().write_text(json.dumps(record)+'\n')
    monkeypatch.delenv('OPENROUTER_API_KEY',raising=False)
    with pytest.raises(RuntimeError,match='matching terminal record'):run_task(path,prices=(1.,2.))


def test_terminal_pull_rejects_old_generation_before_replace(tmp_path,source_root,sdk,modal_fs):
    _,_,store,old,snapshot=reset_pair(tmp_path,source_root,sdk,modal=True)
    shutil.copytree(snapshot,modal_fs.volume/store.run_id)
    # Same legacy location in both implementations; only downloaded content
    # differs. This test is red on the frozen base without any new API use.
    before={p.name:p.read_bytes() for p in store.dir.iterdir() if p.is_file()}
    rc,err=remote.pull_run_dir(store)
    assert rc==1 and 'generation' in err
    assert {p.name:p.read_bytes() for p in store.dir.iterdir() if p.is_file()}==before


def test_terminal_progress_rejects_old_generation(tmp_path,source_root,sdk,modal_fs):
    _,_,store,old,snapshot=reset_pair(tmp_path,source_root,sdk,modal=True)
    modal_fs.state[store.run_id]={'run_id':store.run_id,'spec_hash':old['spec_hash'],
        'generation_id':old['generation_id'],'state':'done','cursor':1,'total':1}
    assert remote.read_progress(store)['state']!='done'


def test_worker_expectation_prevents_wrong_generation(tmp_path,source_root,sdk,modal_fs):
    from mailroom_sandbox.job.checkpoint import generation_identity
    _,_,store,old,snapshot=reset_pair(tmp_path,source_root,sdk)
    shutil.copytree(snapshot,modal_fs.volume/store.run_id)
    lock=store.read_lock()
    payload={'run_id':store.run_id,'spec_hash':lock['spec_hash'],'generation_id':lock['generation_id'],
        'run_generation':generation_identity(lock),'mock':False}
    before=len(sdk['requests'])
    with pytest.raises(RuntimeError,match='dispatch expectation'):modal_fs.worker(payload)
    assert len(sdk['requests'])==before and modal_fs.state=={}


def test_worker_does_not_publish_terminal_for_changed_generation(tmp_path,source_root,sdk,modal_fs):
    spec,_,store,_=spec_file(tmp_path,source_root)
    assert preflight.preflight(spec,offline=True)['status']=='prepared'
    remote.ensure_running(store);payload=modal_fs.spawned[-1]
    remote_store=RunStore(modal_fs.volume/payload['run_path'])
    original=sdk['transport']
    def replace_lock_at_provider_boundary(request):
        response=original(request)
        lock=remote_store.read_lock();lock['generation_id']='replacement-generation'
        remote_store.lock_path.write_text(json.dumps(lock))
        return response
    sdk['transport']=replace_lock_at_provider_boundary
    with pytest.raises(RuntimeError,match='refusing stale terminal publication'):
        modal_fs.worker(payload)
    assert not any(value.get('state') in {'done','failed'} for value in modal_fs.state.values())


def test_failed_remote_worker_progress_keeps_generation_identity(tmp_path,source_root,sdk,modal_fs):
    spec,_,store,_=spec_file(tmp_path,source_root)
    assert preflight.preflight(spec,offline=True)['status']=='prepared'
    remote.ensure_running(store);payload=modal_fs.spawned[-1];sdk['fail_provider']=True
    modal_fs.worker(payload)
    progress=remote.read_progress(store)
    assert progress['state']=='failed'
    assert progress['run_generation']==payload['run_generation']
    assert remote.pull_run_dir(store)==(0,'') and store.state()=='failed'
