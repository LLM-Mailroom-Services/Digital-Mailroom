"""DMR-091 source regressions. Offline SDK/transport fixtures, no live accounts."""
import argparse
import hashlib
import io
import json
from collections import deque
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from rich.console import Console

from mailroom_ui.langfuse_source import LangfuseSource, LangfuseUnavailable
from mailroom_ui.trace_cache import load_traces
from operator_desk import db
from operator_desk.auth import create_access_token
from server.main import create_app
from server.poller import PollHub
from tests.fake_langfuse import FakeClient, FakeList, Obj, make_trace


def trace(tid='doc', **kw):
    return make_trace(tid, base_time=datetime.now(timezone.utc)-timedelta(minutes=5), **kw)


def source(*rows, run_ttl=60):
    return LangfuseSource(client=FakeClient(list(rows)), cache_ttl=0,
                          poll_cache_ttl=0, run_cache_ttl=run_ttl)


def offline(*args, **kw):
    raise LangfuseUnavailable('offline SDK fixture')


def judge_miss(row):
    row['scores']=[s for s in row['scores'] if s.name!='mailroom-pipeline-judge']
    row['scores'].append(Obj(name='mailroom-pipeline-judge', value='MISS', data_type='CATEGORICAL'))


@pytest.mark.parametrize('changed_user',[False, True])
def test_public_reused_store_stays_locked_despite_new_seed_env(monkeypatch, changed_user):
    db.migrate()
    before=db.lookup_user('admin')['password_hash']
    monkeypatch.setenv('MAILROOM_OPERATOR_ADMIN_PASSWORD','fixture-new-seed-password')
    if changed_user:
        monkeypatch.setenv('MAILROOM_OPERATOR_ADMIN_USER','new-seed-admin')
    monkeypatch.setenv('MAILROOM_EDITION','hosted')
    client=TestClient(create_app(source()))
    response=client.post('/v1/auth/login',json={'username':'admin','password':'changeme'})
    assert response.status_code==503
    assert db.lookup_user('admin')['password_hash']==before  # no implicit rotation


def test_public_fresh_seed_and_explicit_rotation_can_login(monkeypatch):
    monkeypatch.setenv('MAILROOM_OPERATOR_ADMIN_PASSWORD','fixture-private-password')
    monkeypatch.setenv('MAILROOM_EDITION','hosted')
    client=TestClient(create_app(source()))
    assert client.post('/v1/auth/login',json={'username':'admin','password':'fixture-private-password'}).status_code==200
    # Rotated stored password remains authoritative even when env is the old default.
    monkeypatch.setenv('MAILROOM_OPERATOR_ADMIN_PASSWORD','changeme')
    assert client.post('/v1/auth/login',json={'username':'admin','password':'fixture-private-password'}).status_code==200
    assert client.post('/v1/auth/login',json={'username':'admin','password':'changeme'}).status_code==401


@pytest.mark.parametrize('stage,ttl_name',[('review','review_ttl'),('archived','detail_ttl')])
def test_expiry_refreshes_unchanged_identity_through_sdk_cache(monkeypatch,stage,ttl_name):
    row=trace(stage=stage,verdict='CORRECT')
    src=source(row)
    hub=PollHub(src,**{ttl_name:60})
    assert hub._fetch()[0]['verdict']=='CORRECT'
    judge_miss(row)
    assert hub._fetch()[0]['verdict']=='CORRECT'  # still inside poller TTL
    ts,payload,fp=hub._details['doc']
    hub._details['doc']=(ts-61,payload,fp)
    assert hub._fetch()[0]['verdict']=='MISS'  # source cache is also bypassed


def test_new_fingerprint_fetches_real_detail_before_marking_enriched():
    row=trace(stage='archived',verdict='CORRECT')
    hub=PollHub(source(row))
    assert hub._fetch()[0]['verdict']=='CORRECT'
    row['updated_at']+=timedelta(seconds=1)
    judge_miss(row)
    assert hub._fetch()[0]['verdict']=='MISS'
    assert hub.runs[0].verdict=='MISS'


@pytest.mark.parametrize('query',['?stage=review','?environment=absent','?limit=1','?since=1',''])
def test_get_never_replaces_poller_canonical_snapshot(monkeypatch,query):
    src=source(trace('parked',stage='review'),trace('done',stage='archived'))
    PollHub(src)._fetch()  # canonical cache owner, independently of request window
    before=load_traces()
    client=TestClient(create_app(src))
    assert client.get('/api/traces'+query).status_code==200
    assert load_traces()==before
    monkeypatch.setattr(src.client.api.trace,'list',offline)
    response=client.get('/api/traces')
    assert response.status_code==200
    assert {r['trace_id'] for r in response.json()['runs']}=={'parked','done'}
    assert response.json()['source']=='langfuse-cache'


@pytest.mark.asyncio
async def test_reconnect_retains_outage_and_last_success_timestamp(monkeypatch):
    import server.poller as poller
    src=source(trace())
    hub=PollHub(src)
    messages=[]
    async def capture(message):
        messages.append(message)
        hub._stop.set()
    monkeypatch.setattr(hub,'_broadcast',capture)
    monkeypatch.delenv('MAILROOM_PIPELINE_URL',raising=False)
    monkeypatch.delenv('MAILROOM_PIPELINE_API',raising=False)
    await hub._run()
    first=messages[-1]
    assert first['stale'] is False
    monkeypatch.setattr(src.client.api.trace,'list',offline)
    hub._stop.clear()
    await hub._run()
    failed=messages[-1]
    assert failed['stale'] is True
    assert failed['fetched_at']==first['fetched_at']
    class Socket:
        async def accept(self): pass
        async def send_json(self,message): self.message=message
    ws=Socket()
    await hub.connect(ws)
    assert ws.message['stale'] is True
    assert ws.message['fetched_at']==first['fetched_at']
    assert ws.message['runs']==first['runs']


@pytest.mark.parametrize('path',['/status','/throughput','/distribution'])
def test_operator_total_outage_is_503_and_real_empty_is_200(monkeypatch,path):
    src=source()
    client=TestClient(create_app(src))
    headers={'Authorization':'Bearer '+create_access_token('fixture','viewer')}
    assert client.get('/v1/ops'+path,headers=headers).status_code==200
    monkeypatch.setattr(src.client.api.trace,'list',offline)
    assert client.get('/v1/ops'+path,headers=headers).status_code==503


def stale_socket(monkeypatch):
    import websockets.sync.client
    from tui import mailroom_console as console
    class Socket:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def recv(self,**kw): return json.dumps({'type':'snapshot','stale':True,'runs':[{'trace_id':'old'}]})
    monkeypatch.setattr(websockets.sync.client,'connect',lambda *a,**kw:Socket())


def test_tui_rejects_stale_ws_frame(monkeypatch):
    from tui import mailroom_console as console
    stale_socket(monkeypatch)
    assert console.fetch_snapshot() is None


def test_tui_cached_http_is_closed_in_actual_once_render(monkeypatch):
    from tui import mailroom_console as console
    stale_socket(monkeypatch)
    monkeypatch.setattr(console,'fetch',lambda path,**kw:{'runs':[{'trace_id':'old'}],'source':'langfuse-cache'})
    assert console.fetch_floor_runs() is None
    output=io.StringIO()
    console._run_once(argparse.Namespace(view='floor'),Console(file=output,color_system=None))
    assert 'CLOSED' in output.getvalue()
    assert 'no Langfuse connection' in output.getvalue()


def test_tui_fresh_empty_floor_is_not_closed(monkeypatch):
    from tui import mailroom_console as console
    monkeypatch.setattr(console,'fetch_snapshot',lambda:None)
    monkeypatch.setattr(console,'fetch',lambda path,**kw:{'runs':[],'source':'langfuse'})
    assert console.fetch_floor_runs()==[]


def test_history_empty_and_editor_dispatch_share_bounded_history():
    from tui import commands as cmds
    from tui import mailroom_console as console
    ctx=cmds.CommandContext()
    assert '(no history yet)' in str(cmds.run_command(ctx,'history')[0])
    editor=console.LineEditor(Console(file=io.StringIO()),history=ctx.history)
    for i in range(205):
        editor.buf=f'echo {i}'
        assert editor.handle('\r',deque())
        console._dispatch(ctx,editor.submitted,editor.console,None)
    result=console._dispatch(ctx,'history',editor.console,None)
    assert len(ctx.history)==200
    assert ctx.history[0]=='echo 5'
    assert 'echo 204' in str(result[0])
    assert 'echo 5\n' not in str(result[0])  # display remains the last 40
    editor.handle('\x1b',deque(['[','A']))
    assert editor.text()=='echo 204'


def test_catalog_uses_independent_gt_indices_and_marks_missing(monkeypatch):
    from mailroom_ui import hf_corpus
    from scripts.export_corpus_catalog import build_catalog
    def rows(*,config,split,**kw):
        if split=='test': return []
        if config==hf_corpus.DEFAULT_CONFIG:
            return [{'filename':'A','doc_text':'a'},{'filename':'B','doc_text':'bb'},{'filename':'C'}]
        return [{'filename':'B','expected':'contract','content_sha256':'b'},
                {'filename':'A','expected':'correspondence','content_sha256':'a'}]
    monkeypatch.setattr(hf_corpus,'fetch_rows',rows)
    rows=build_catalog(pace_s=0)['rows']
    assert [(r['filename'],r['gt_index'],r['doc_class']) for r in rows]==[
        ('A',1,'correspondence'),('B',0,'contract'),('C',-1,None)]


def test_union_sorts_newest_before_limit_and_primary_wins_duplicates():
    from mailroom_ui.multi_source import MultiSource
    class Backend:
        def __init__(self,rows): self.rows=rows
        def list_traces(self,**kw): return self.rows
    primary=[{'id':'dup','timestamp':'2026-10-20T00:00:00Z','label':'primary'},
             {'id':'old','timestamp':datetime(2026,10,19)},
             {'id':'missing'},{'id':'malformed','updatedAt':'bad'}]
    secondary=[{'id':'new','updated_at':'2026-10-23T02:00:00+02:00'},
               {'id':'dup','updatedAt':'2026-10-24T00:00:00Z','label':'secondary'},
               {'id':'naive','timestamp':'2026-10-21T00:00:00'}]
    src=MultiSource([Backend(primary),Backend(secondary)])
    assert [r['id'] for r in src.list_traces(limit=1)]==['new']
    result=src.list_traces(limit=10)
    assert [r['id'] for r in result]==['new','naive','dup','old','missing','malformed']
    assert result[2]['label']=='primary'


@pytest.mark.parametrize('checksum,valid,reason',[
    (None,False,'No expected checksum'),('',False,'No expected checksum'),
    (hashlib.sha256(b'fixture bytes').hexdigest(),True,None),
    ('0'*64,False,'Checksum mismatch'),
])
def test_archive_verification_requires_reference_and_audits_result(tmp_path,checksum,valid,reason):
    client=TestClient(create_app(source()))
    path=tmp_path/'archive'/'doc.txt'
    path.write_bytes(b'fixture bytes')
    db.upsert_archive_entry(doc_id='doc',matter_id='m',doc_type='contract',
                           archive_path=str(path),checksum_sha256=checksum)
    headers={'Authorization':'Bearer '+create_access_token('fixture','reviewer')}
    response=client.get('/v1/archive/doc/verify',headers=headers)
    assert response.status_code==200
    data=response.json()
    assert data['valid'] is valid
    assert data.get('reason')==reason
    assert data['expected']==checksum
    conn=db.connect()
    try:
        audit=conn.execute("SELECT metadata FROM ui_audit WHERE action='archive_verify' ORDER BY id DESC").fetchone()
    finally:
        conn.close()
    assert json.loads(audit['metadata'])['valid'] is valid


def test_budget_deferred_and_failed_details_retry_before_ttl(monkeypatch):
    monkeypatch.setenv('MAILROOM_POLL_ENRICH_BUDGET','1')
    now=datetime.now(timezone.utc)-timedelta(minutes=5)
    rows=[make_trace('first',stage='archived',base_time=now),
          make_trace('second',stage='archived',base_time=now-timedelta(minutes=1))]
    rows[1]['observations']=[]  # no embedded detail can mask a provider failure
    src=source(*rows)
    hub=PollHub(src)
    hub._fetch()
    assert len(hub._enriched_fp)==1
    api=src.client.api.observations
    real=api.get_many
    def fail_second(trace_id,**kw):
        if trace_id=='second': return offline()
        return real(trace_id,**kw)
    monkeypatch.setattr(api,'get_many',fail_second)
    hub._fetch()
    assert 'second' not in hub._enriched_fp
    monkeypatch.setattr(api,'get_many',real)
    hub._fetch()
    assert set(hub._enriched_fp)=={'first','second'}



def test_actual_repl_wires_editor_history_to_command_context():
    import queue
    from tui import mailroom_console as console
    keys=queue.Queue()
    for ch in 'echo fixture-history\rhistory\rquit\r':
        keys.put(ch)
    output=io.StringIO()
    console._repl_loop(argparse.Namespace(),Console(file=output,color_system=None),keys,queue.Queue())
    assert console._ctx.history==['echo fixture-history','history','quit']


@pytest.mark.parametrize("stage,ttl_key,ttl", [("review", "review_ttl", 15), ("archived", "detail_ttl", 60)])
def test_failed_expired_detail_retries_after_provider_recovers(monkeypatch, stage, ttl_key, ttl):
    """A failed refresh cannot renew the prior successful enrichment marker."""
    row = make_trace("retry", stage=stage, verdict="CORRECT",
                     base_time=datetime.now(timezone.utc)-timedelta(minutes=5))
    src = source(row)
    trace_api = src.client.api.trace
    list_traces = trace_api.list

    def light(**kwargs):
        return FakeList(data=[{k: v for k, v in trace.items() if k not in ("scores", "observations")}
                              for trace in list_traces(**kwargs).data])

    monkeypatch.setattr(trace_api, "list", light)
    hub = PollHub(src, **{ttl_key: ttl})
    assert hub._fetch()[0]["verdict"] == "CORRECT"
    timestamp, payload, fingerprint = hub._details["retry"]
    hub._details["retry"] = (timestamp-ttl-1, payload, fingerprint)
    score_api = src.client.api.scores_v3
    fetch_scores = score_api.get_many_v3
    failed_calls, recovered_calls = [], []

    def fail(**kwargs):
        failed_calls.append(kwargs)
        raise LangfuseUnavailable("expired-refresh fixture outage")

    monkeypatch.setattr(score_api, "get_many_v3", fail)
    assert hub._fetch()[0]["verdict"] is None
    assert len(failed_calls) == 1
    row["scores"] = [score for score in row["scores"] if score.name != "mailroom-pipeline-judge"] + [
        Obj(name="mailroom-pipeline-judge", value="MISS", data_type="CATEGORICAL")]

    def recovered(**kwargs):
        recovered_calls.append(kwargs)
        return fetch_scores(**kwargs)

    monkeypatch.setattr(score_api, "get_many_v3", recovered)
    assert hub._fetch()[0]["verdict"] == "MISS"
    assert len(recovered_calls) == 1
