"""Fresh-process contract imports: sibling src must not leak into sys.path."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
import subprocess
import sys
import textwrap

import pydantic
import pytest

ROOT = Path(__file__).resolve().parent.parent


def _write(root, name, code):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(code), encoding="utf-8")


def _contract(src):
    _write(src, "pipeline/__init__.py", "")
    _write(src, "pipeline/review_resolve.py", '''
        DISPOSITIONS = {"resume", "record", "requeue", "complete"}
        DECISIONS = {"approved", "rejected"}
        def serialize_document(doc):
            return {"doc_id": doc.doc_id}
        def tray_actions_for(stage):
            return []
        def validate_operator_extraction(kind, data):
            from observability.scores import validate_extraction
            if not validate_extraction(kind, data)["schema_valid"]:
                raise ValueError("invalid extraction")
            return dict(data)
    ''')
    _write(src, "schemas/__init__.py", "")
    _write(src, "schemas/manifest.py", '''
        class DocumentManifest:
            pass
        class PipelineStage:
            REVIEW = "review"
    ''')
    _write(src, "schemas/documents.py", '''
        from pydantic import BaseModel, Field, field_validator
        class Contract(BaseModel):
            parties: list[str] = Field(default_factory=list)
            @field_validator("parties")
            @classmethod
            def runtime_failure(cls, value):
                if value == ["explode"]:
                    raise RuntimeError("schema implementation failed")
                return value
        class Correspondence(BaseModel):
            sender: str | None = None
        EXTRACTION_SCHEMAS = {"contract": Contract, "correspondence": Correspondence}
    ''')


def _isolated(tmp_path, mode, code):
    # The source checkout can have a real sibling. Copy only the exact adapter
    # and its pure contract boundary into an isolated layout for each mode.
    isolated_root = tmp_path / "visualizer"
    for relative in ("mailroom_ui/__init__.py", "mailroom_ui/producer.py",
                     "mailroom_ui/pipeline_schema.py", "mailroom_ui/models.py", "scripts/__init__.py",
                     "scripts/export_corpus_catalog.py"):
        target = isolated_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    checkout = tmp_path / "llm-mailroom"
    if mode == "sibling":
        src = checkout / "src"
        _contract(src)
        _write(src, "observability/__init__.py", "")
        _write(src, "observability/scores.py", '''
            from schemas.documents import EXTRACTION_SCHEMAS
            def validate_extraction(kind, data):
                EXTRACTION_SCHEMAS[kind].model_validate(data)
                return {"schema_valid": True}
        ''')
        _write(src, "scripts/__init__.py", 'raise AssertionError("sibling scripts shadowed visualizer")')
    elif mode == "pin":
        # The real archive intentionally contains pipeline + schemas only.
        src = tmp_path / "the-mailroom-pin-959bb0bce152" / "src"
        _contract(src)
    else:
        src = checkout / "src"
    env = dict(os.environ, MAILROOM_PIPELINE_ROOT=str(checkout), TMPDIR=str(tmp_path), HOME=str(tmp_path))
    bootstrap = '''
        import importlib.abc, pathlib, socket, sys
        sys.dont_write_bytecode = True
        sys.path[:0] = [sys.argv[1], sys.argv[2]]
        def offline(event, args):
            if event in ("socket.connect", "socket.getaddrinfo"):
                raise AssertionError("network access forbidden")
        sys.addaudithook(offline)
        class Forbidden(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname.split(".")[0] in {"api", "llm_dojo_scoring", "langfuse"}:
                    raise AssertionError("forbidden service import: " + fullname)
        sys.meta_path.insert(0, Forbidden())
        before = list(sys.path)
        from mailroom_ui import producer
        assert pathlib.Path(producer.__file__).resolve() == pathlib.Path(sys.argv[1]) / "mailroom_ui/producer.py"
        assert sys.path == before
        assert str(pathlib.Path(sys.argv[3])) not in sys.path
        assert producer.producer_status()["origin"] == sys.argv[4]
    '''
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-c", textwrap.dedent(bootstrap) + textwrap.dedent(code),
         str(isolated_root), str(Path(pydantic.__file__).parent.parent), str(src),
         {"sibling": "checkout", "pin": "pin", "fallback": "fallback"}[mode]],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("mode", ["sibling", "pin"])
def test_delayed_schema_import_after_src_cleanup(tmp_path, mode):
    _isolated(tmp_path, mode, '''
        assert "schemas.documents" not in sys.modules
        payload = {"parties": ["A", "B"], "confidence": 0.8, "_note": "kept"}
        assert producer.validate_operator_extraction("contract", payload) == payload
        assert "schemas.documents" in sys.modules
        catalog = importlib.util.find_spec("scripts.export_corpus_catalog")
        assert pathlib.Path(catalog.origin).resolve().is_relative_to(pathlib.Path(sys.argv[1]))
        assert "observability.scores" not in sys.modules
        assert sys.path == before
    ''')


@pytest.mark.parametrize("mode", ["sibling", "pin"])
def test_schema_rejections_and_runtime_errors_remain_loud(tmp_path, mode):
    _isolated(tmp_path, mode, '''
        for kind, payload, message in [
            ("contract", {"sender": "foreign"}, "another specialist"),
            ("contract", {"parties": 42}, "does not match"),
            ("contract", {"_parse_error": True}, "does not match"),
            ("unknown", {"parties": ["A"]}, "does not match"),
            ("contract", {}, "does not match"),
        ]:
            try:
                producer.validate_operator_extraction(kind, payload)
            except ValueError as exc:
                assert message in str(exc), str(exc)
            else:
                raise AssertionError("invalid extraction accepted")
            assert sys.path == before
        try:
            producer.validate_operator_extraction("contract", {"parties": ["explode"]})
        except RuntimeError as exc:
            assert str(exc) == "schema implementation failed"
        else:
            raise AssertionError("schema runtime error swallowed")
        # A broken producer dependency must not degrade to bundled success.
        del sys.modules["schemas.documents"]
        pathlib.Path(sys.argv[3], "schemas/documents.py").write_text("import missing_schema_dependency\\n")
        try:
            producer.validate_operator_extraction("contract", {"parties": ["A"]})
        except ModuleNotFoundError as exc:
            assert exc.name == "missing_schema_dependency"
        else:
            raise AssertionError("schema import error swallowed")
        assert sys.path == before
    ''')


def test_bundled_validation_without_a_producer(tmp_path):
    _isolated(tmp_path, "fallback", '''
        payload = {"parties": ["A", "B"]}
        assert producer.validate_operator_extraction("contract", payload) == payload
        try:
            producer.validate_operator_extraction("contract", {"sender": "foreign"})
        except ValueError as exc:
            assert "another specialist" in str(exc)
        else:
            raise AssertionError("bundled field guard bypassed")
        assert sys.path == before
    ''')
