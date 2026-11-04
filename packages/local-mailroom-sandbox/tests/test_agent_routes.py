"""Native and LangChain agents share explicit, isolated per-agent transports."""

import pytest

from mailroom_sandbox import agent_routes as routes
from mailroom_sandbox.job.spec import AgentRoute, RunSpec
from mailroom_sandbox.overlay import build_merged_taxonomy, load_profile
from mailroom_sandbox.runtime import activate
from mailroom_sandbox.services._exec import ServiceError


@pytest.fixture(autouse=True)
def environment(monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY', 'api-test-secret')
    monkeypatch.setenv('VLLM_API_KEY', 'gpu-test-secret')
    monkeypatch.setenv('MODAL_WORKSPACE', 'test-ws')
    monkeypatch.setenv('MAILROOM_LLM_FREE_ONLY', '0')
    monkeypatch.setattr(routes, '_ROUTES', {})
    yield
    routes._ROUTES = {}


def test_native_clients_route_by_agent_despite_default_provider(monkeypatch):
    activate('modal-vllm', load_env_file=False, agent_routes={
        'sorter': {'provider': 'openrouter', 'model': 'api-sorter'},
        'boss': {'provider': 'vllm', 'model': 'gpu-boss', 'base_url': 'https://gpu.test/v1'},
    })
    from llm.client import get_llm
    first, model = get_llm('sorter')
    second, other_model = get_llm('boss')
    assert model == 'api-sorter' and str(first.base_url) == 'https://openrouter.ai/api/v1/'
    assert first.api_key == 'api-test-secret'
    assert other_model == 'gpu-boss' and str(second.base_url) == 'https://gpu.test/v1/'
    assert second.api_key == 'gpu-test-secret'


def test_langchain_and_native_resolution_agree():
    activate('modal-vllm', load_env_file=False, agent_routes={
        'contracts_specialist': {'provider': 'openrouter', 'model': 'api-contracts'},
    })
    from langchain_agents.specialist_agents import ContractsSpecialist
    agent = ContractsSpecialist()
    llm = agent.llm()
    assert llm.model_name == 'api-contracts'
    assert str(llm.openai_api_base).rstrip('/') == 'https://openrouter.ai/api/v1'
    assert llm.openai_api_key.get_secret_value() == 'api-test-secret'


def test_routes_are_cleared_on_next_activation():
    activate('modal-vllm', load_env_file=False, agent_routes={'sorter': {'provider': 'openrouter', 'model': 'api-sorter'}})
    activate('ollama', load_env_file=False)
    from llm.client import resolve_agent_model
    assert resolve_agent_model('sorter').provider.name == 'ollama'


def test_agent_model_override_wins_on_route():
    activate('modal-vllm', load_env_file=False,
        agent_routes={'sorter': {'provider': 'openrouter', 'model': 'old-model'}}, agent_models={'sorter': 'new-model'})
    from llm.client import resolve_agent_model
    assert resolve_agent_model('sorter').model == 'new-model'


def test_model_only_override_survives_served_model_pinning():
    taxonomy = build_merged_taxonomy(load_profile('modal-vllm'), model_override='Qwen/default', agent_models={'sorter': 'Qwen/custom'})
    assert taxonomy['agents']['sorter']['model'] == 'Qwen/custom'


def test_route_changes_affect_spec_hash():
    spec = RunSpec(agent_routes={'sorter': AgentRoute(provider='openrouter', model='api-model')})
    changed = spec.model_copy(deep=True)
    changed.agent_routes['sorter'].model = 'other'
    assert spec.spec_hash() != changed.spec_hash()


@pytest.mark.parametrize('name', ['reporter', 'compile_report', 'unknown_agent'])
def test_retired_or_unknown_agent_rejected(name):
    with pytest.raises(ServiceError):
        routes.parse_routes([name + '=openrouter:model'])


@pytest.mark.parametrize('url', ['https://user:secret@host/v1', 'https://host/v1?key=secret', 'file:///tmp/socket'])
def test_credentials_cannot_be_embedded_in_route_url(url):
    with pytest.raises(ValueError):
        AgentRoute(provider='api', model='m', base_url=url, api_key_env='API_TOKEN')
