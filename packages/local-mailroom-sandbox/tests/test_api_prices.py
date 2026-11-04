"""Tiered API pricing: config/api_prices.yaml, call_price/call_cost, task_agents, budget tiers."""
from __future__ import annotations

import sys

import pytest
import yaml

from mailroom_sandbox.job import metrics
from mailroom_sandbox.job.api_budget import task_agents
from mailroom_sandbox.paths import repo_root

ROOT = repo_root()
sys.path.insert(0, str(ROOT / "scripts"))
import refresh_api_prices  # noqa: E402


@pytest.fixture(autouse=True)
def _no_override(monkeypatch):
    for env in ("SANDBOX_TOKEN_PRICE", "SANDBOX_TOKEN_PRICE_USD_PER_1M", "OPENROUTER_TOKEN_PRICE"):
        monkeypatch.delenv(env, raising=False)
    monkeypatch.setattr(metrics, "_token_price_override", lambda: None)


def _prices() -> dict:
    return yaml.safe_load((ROOT / "config" / "api_prices.yaml").read_text(encoding="utf-8"))


def test_qwen37_flash_full_sheet_is_listed():
    row = _prices()["models"]["qwen/qwen3.7-flash"]
    assert row["context_length"] == 1_000_000 and row["max_completion_tokens"] == 65536
    assert [t["min_prompt_tokens"] for t in row["tiers"]] == [0, 32000, 256000]
    assert {"prompt", "completion", "cache_read", "cache_write"} <= set(row["tiers"][0])


def test_profile_api_models_all_priced():
    profile = yaml.safe_load((ROOT / "config" / "profiles" / "openrouter.yaml").read_text(encoding="utf-8"))
    assert "qwen/qwen3.7-flash" in profile["api_models"]
    for model in profile["api_models"]:
        assert metrics.price_sheet(model), model


def test_file_sheets_match_builtin_fallback():
    file_sheets = {k: [{f: t[f] for f in ("min_prompt_tokens", "prompt", "completion")} for t in v["tiers"]]
                   for k, v in _prices()["models"].items()}
    for model, sheet in metrics.API_PRICE_SHEETS.items():
        assert file_sheets[model] == [{f: t[f] for f in ("min_prompt_tokens", "prompt", "completion")} for t in sheet]


@pytest.mark.parametrize("tokens,price", [(0, (0.03, 0.13)), (31_999, (0.03, 0.13)), (32_000, (0.10, 0.40)),
                                          (255_999, (0.10, 0.40)), (256_000, (0.20, 0.80))])
def test_call_price_tiers(tokens, price):
    assert metrics.call_price("qwen/qwen3.7-flash", tokens) == pytest.approx(price)


def test_decisions_id_not_priced_as_chat_model():
    assert metrics.call_price("openai/gpt-6-luna-decisions-20261006", 300_000) == (0.10, 0.0)
    assert metrics.call_price("openai/gpt-6-luna-20261006", 300_000) == (0.20, 0.75)


def test_call_cost_prices_each_call_at_its_tier():
    one_long = metrics.call_cost("qwen/qwen3.7-flash", 100_000, 1_000)
    ten_short = metrics.call_cost("qwen/qwen3.7-flash", 100_000, 1_000, calls=10)
    assert one_long == pytest.approx((100_000 * 0.10 + 1_000 * 0.40) / 1e6)
    assert ten_short == pytest.approx((100_000 * 0.03 + 1_000 * 0.13) / 1e6)


def test_missing_file_falls_back_to_builtin(monkeypatch):
    monkeypatch.setattr(metrics, "_FILE_SHEETS", {})
    assert metrics.call_price("qwen/qwen3.7-flash", 40_000) == pytest.approx((0.10, 0.40))


@pytest.mark.parametrize("lock,expected", [
    ({"task": "isolated", "job": {}}, {"sorter"}),
    # The isolated runner always runs the sorter spec, so job.task cannot hide its model.
    ({"task": "isolated", "job": {"task": "judge"}}, {"sorter"}),
    ({"task": "contract_specialist"}, {"contract_specialist"}),
    ({"task": "pipeline"}, None),
])
def test_task_agents(lock, expected):
    assert task_agents(lock) == expected


def test_refresh_sheet_from_catalog_and_drift():
    entry = {"id": "x/m", "context_length": 1000, "top_provider": {"max_completion_tokens": 10},
             "pricing": {"prompt": "0.00000003", "completion": "0.00000013",
                         "overrides": [{"min_prompt_tokens": 32000, "prompt": "0.0000001", "completion": "0.0000004"}]}}
    row = refresh_api_prices.sheet_from_catalog(entry)
    assert row["tiers"] == [{"min_prompt_tokens": 0, "prompt": 0.03, "completion": 0.13},
                            {"min_prompt_tokens": 32000, "prompt": 0.1, "completion": 0.4}]
    doc = {"models": {"x/m": row, "y/decisions": {"endpoint": "/d", "tiers": []}}}
    same, changed = refresh_api_prices.refresh(doc, {"x/m": entry}, today="2026-11-02")
    assert changed == [] and same == doc
    entry["pricing"]["prompt"] = "0.00000005"
    _, changed = refresh_api_prices.refresh(doc, {"x/m": entry}, today="2026-11-02")
    assert changed == ["x/m"]
