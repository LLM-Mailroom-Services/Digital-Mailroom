"""CodeAnt runtime boundaries use real password checks and poll broadcasts."""
import asyncio
import secrets
import pytest
from operator_desk import auth, db
from server import poller
from tests.fake_langfuse import FakeClient
from mailroom_ui.langfuse_source import LangfuseSource


def test_default_admin_hash_checks_are_cached_and_rotation_invalidates(monkeypatch):
    """Repeated checks reuse only the result for an exact stored hash."""
    db.migrate()
    original = auth.verify_password
    calls = []
    def observed(password, stored):
        """Count actual KDF checks without replacing password verification."""
        calls.append(stored)
        return original(password, stored)
    monkeypatch.setattr(auth, 'verify_password', observed)
    for _ in range(5):
        assert any('default password' in reason for reason in auth.insecure_config_reasons())
    assert len(calls) == 1
    rotated = db.hash_password(secrets.token_urlsafe(24))
    with db.connect() as conn:
        conn.execute('UPDATE ui_users SET password_hash=? WHERE username=?', (rotated, 'admin'))
    for _ in range(5):
        assert auth.insecure_config_reasons() == []
    assert len(calls) == 2
    restored = db.hash_password(auth.DEFAULT_ADMIN_PASSWORD)
    with db.connect() as conn:
        conn.execute('UPDATE ui_users SET password_hash=? WHERE username=?', (restored, 'admin'))
    assert any('default password' in reason for reason in auth.insecure_config_reasons())
    assert len(calls) == 3


@pytest.mark.parametrize('component', ['runs', 'ops'])
def test_poll_iteration_exception_broadcasts_staleness_to_connected_clients(monkeypatch, component):
    """Either gathered failure sends an outage frame with the prior good bytes."""
    async def scenario():
        hub = poller.PollHub(LangfuseSource(client=FakeClient([])), interval=.001)
        hub.snapshot = [{'trace_id':'last-good'}]
        hub.fetched_at = '2026-10-23T00:00:00+00:00'
        hub.stale = False
        frames = []
        class Client:
            async def send_json(self, frame):
                """Receive the real broadcast without a network service."""
                frames.append(frame)
        hub.clients.add(Client())
        loop = asyncio.get_running_loop()
        def fail():
            """Fail one I/O boundary and end after the current iteration."""
            loop.call_soon_threadsafe(hub._stop.set)
            raise RuntimeError('fixture I/O failure')
        def runs():
            """Return the last known run from the successful boundary."""
            return hub.snapshot
        def ops():
            """Return the successful companion I/O response."""
            return {'configured':False}
        monkeypatch.setattr(hub, '_fetch', fail if component == 'runs' else runs)
        monkeypatch.setattr(poller, 'fetch_pipeline_ops', fail if component == 'ops' else ops)
        await asyncio.wait_for(hub._run(), timeout=2)
        assert frames and frames[-1]['stale'] is True
        assert frames[-1]['runs'] == [{'trace_id':'last-good'}]
        assert frames[-1]['fetched_at'] == '2026-10-23T00:00:00+00:00'
    asyncio.run(scenario())
