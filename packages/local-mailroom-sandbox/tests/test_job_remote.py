"""Modal remote transport contracts exercised with real locked stores."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import shutil

import pytest

from test_generation_protocol import modal_fs
from test_job_generation_residuals import source_root, spec_file, sdk
from mailroom_sandbox.job import preflight, remote

pytestmark = pytest.mark.usefixtures('job_data_dir')


def prepared(tmp_path, source_root):
    spec, _, store, _ = spec_file(tmp_path, source_root)
    assert preflight.preflight(spec, offline=True)['status'] == 'prepared'
    return store


def test_fire_persists_call_id(tmp_path, source_root, modal_fs):
    store = prepared(tmp_path, source_root)
    result = remote.fire(store)
    assert result['call_id'] == store.read_checkpoint()['remote']['call_id'] == 'fc-0'
    assert any(e['event'] == 'fired' for e in store.events())


def test_is_alive_reflects_input_state(tmp_path, source_root, modal_fs):
    store = prepared(tmp_path, source_root); remote.fire(store)
    assert remote.is_alive(store) is True
    modal_fs.calls['fc-0'] = 'SUCCESS'
    assert remote.is_alive(store) is False


def test_is_alive_exception_treated_as_alive(tmp_path, source_root, modal_fs, caplog):
    store = prepared(tmp_path, source_root); remote.fire(store)
    modal_fs.calls['fc-0'] = OSError('SDK transport failed')
    with caplog.at_level(logging.WARNING, logger='mailroom_sandbox.job.remote'):
        assert remote.is_alive(store) is True
    assert len(modal_fs.spawned) == 1


def test_ensure_running_refuses_young_refire(tmp_path, source_root, modal_fs):
    store = prepared(tmp_path, source_root); remote.fire(store)
    modal_fs.calls['fc-0'] = 'SUCCESS'
    with pytest.raises(RuntimeError, match='cooldown'): remote.ensure_running(store)
    assert len(modal_fs.spawned) == 1


def test_ensure_running_refires_after_cooldown(tmp_path, source_root, modal_fs):
    store = prepared(tmp_path, source_root); remote.fire(store)
    cp = store.read_checkpoint(); cp['remote']['fired_at'] = (datetime.now(timezone.utc)-timedelta(minutes=30)).isoformat()
    store.write_checkpoint(state='running', cursor=0, total=1, remote=cp['remote'])
    modal_fs.calls['fc-0'] = 'SUCCESS'
    assert remote.ensure_running(store) == {'action':'fired','call_id':'fc-1'}
    assert len([cmd for cmd in modal_fs.transfers if cmd[2]=='put']) == 1


def test_ensure_running_reattaches_live(tmp_path, source_root, modal_fs):
    store = prepared(tmp_path, source_root); remote.fire(store)
    assert remote.ensure_running(store) == {'action':'attached','call_id':'fc-0'}
    assert len(modal_fs.spawned) == 1


def test_cancel_calls_function_call(tmp_path, source_root, modal_fs):
    store = prepared(tmp_path, source_root); remote.fire(store); remote.cancel(store)
    assert modal_fs.calls['fc-0'] == 'TERMINATED'
    assert any(e['event']=='cancel_requested' for e in store.events())


def test_fire_sends_lock_mock_flag(tmp_path, source_root, modal_fs):
    spec,_,store,_ = spec_file(tmp_path, source_root); spec.job.mock=True
    assert preflight.preflight(spec,offline=True)['status']=='prepared'
    remote.fire(store)
    payload=modal_fs.spawned[-1]
    assert payload['mock'] is True and payload['run_id']==store.run_id
    assert payload['generation_id']==store.read_lock()['generation_id']


def test_fire_skips_upload_when_remote_lock_matches(tmp_path, source_root, modal_fs):
    store = prepared(tmp_path, source_root)
    shutil.copytree(store.dir, modal_fs.volume/store.run_id)
    remote.fire(store)
    assert not any(cmd[2]=='put' for cmd in modal_fs.transfers)
    assert modal_fs.spawned[-1]['run_path']==store.run_id


def test_fire_uploads_when_remote_lock_differs(tmp_path, source_root, modal_fs):
    import json
    store = prepared(tmp_path, source_root)
    dest=modal_fs.volume/store.run_id;shutil.copytree(store.dir,dest)
    foreign=store.read_lock();foreign['generation_id']='foreign';(dest/'spec.lock.json').write_text(json.dumps(foreign))
    remote.fire(store)
    assert len([cmd for cmd in modal_fs.transfers if cmd[2]=='put'])==1
    assert json.loads((dest/'spec.lock.json').read_text())==foreign


def test_pull_run_dir_copies_files(tmp_path, source_root, modal_fs, sdk):
    store = prepared(tmp_path, source_root);remote.fire(store)
    modal_fs.worker(modal_fs.spawned[-1])
    assert remote.pull_run_dir(store)==(0,'')
    assert [item['index'] for item in store.load_items()]==[0]
    assert store.state()=='done'


def test_pull_run_dir_refuses_busy_store_then_retries(tmp_path, source_root, modal_fs, sdk):
    store = prepared(tmp_path, source_root)
    remote.fire(store)
    modal_fs.worker(modal_fs.spawned[-1])
    before = {p.name: p.read_bytes() for p in store.dir.iterdir()
              if p.is_file() and p.name not in {'run.lock', 'cancel.lock'}}
    with store.acquire():
        rc, detail = remote.pull_run_dir(store)
    assert rc == 1 and 'busy' in detail
    assert {p.name: p.read_bytes() for p in store.dir.iterdir()
            if p.is_file() and p.name not in {'run.lock', 'cancel.lock'}} == before
    assert remote.pull_run_dir(store) == (0, '')
    assert store.state() == 'done'


def test_modal_job_state_dict_put_is_two_arg(tmp_path, source_root, modal_fs, sdk):
    store=prepared(tmp_path,source_root);remote.fire(store)
    modal_fs.worker(modal_fs.spawned[-1])
    # The fixture's Dict.put(key,value) signature is strict. Execute progress
    # and terminal publication and inspect the actual value the worker wrote.
    values=list(modal_fs.state.values())
    assert len(values)==1 and values[0]['state']=='done' and values[0]['cursor']==1
    assert values[0]['generation_id']==store.read_lock()['generation_id']
