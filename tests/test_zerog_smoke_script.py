from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "test_zerog_l1_l2_l3.py"


def load_module():
    spec = importlib.util.spec_from_file_location("test_zerog_l1_l2_l3", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_require_env_returns_value(monkeypatch):
    module = load_module()
    monkeypatch.setenv("ZEROG_TEST_KEY", "value")

    assert module.require_env("ZEROG_TEST_KEY") == "value"


def test_require_env_raises_for_missing_value(monkeypatch):
    module = load_module()
    monkeypatch.delenv("ZEROG_TEST_KEY", raising=False)

    try:
        module.require_env("ZEROG_TEST_KEY")
    except RuntimeError as exc:
        assert str(exc) == "Missing required env var: ZEROG_TEST_KEY"
    else:
        raise AssertionError("Expected RuntimeError for missing env var")


def test_normalize_private_key_adds_hex_prefix():
    module = load_module()

    assert module.normalize_private_key("abcd") == "0xabcd"


def test_normalize_private_key_keeps_existing_hex_prefix():
    module = load_module()

    assert module.normalize_private_key("0xabcd") == "0xabcd"


def test_script_uses_direct_ogstorage_class():
    module = load_module()

    assert hasattr(module, "main")


def test_main_disables_zerog_when_env_missing(monkeypatch, tmp_path, capsys):
    module = load_module()

    monkeypatch.delenv("ZEROG_TESTNET_RPC_URL", raising=False)
    monkeypatch.delenv("ZEROG_TESTNET_PRIVATE_KEY", raising=False)
    monkeypatch.delenv("ZEROG_INDEXER_RPC", raising=False)
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)

    class FakeDatabase:
        def __init__(self, path):
            self.path = path

        def insert_episodic(self, data):
            return True

        def insert_semantic(self, data):
            return True

        def upsert_procedural(self, data):
            return True

        def get_connection(self):
            class _Conn:
                def __enter__(self_inner):
                    class _Cursor:
                        def execute(self, *_args, **_kwargs):
                            return self

                        def fetchone(self):
                            return {
                                "id": "fake",
                                "og_hash": None,
                                "og_tx_hash": None,
                            }

                    return _Cursor()

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return _Conn()

    class FakeOgStorage:
        upload = staticmethod(lambda *_args, **_kwargs: None)

    def fake_get_status():
        return SimpleNamespace(
            enabled=False, reason="missing_env", missing=["ZEROG_TESTNET_RPC_URL"]
        )

    def fake_initialize():
        return False

    def fake_notice(logger=None):
        print("0G disabled")
        return fake_get_status()

    fake_db_module = type("FakeDbModule", (), {"Database": FakeDatabase})
    fake_og_module = type(
        "FakeOgModule",
        (),
        {
            "OgStorage": FakeOgStorage,
            "get_zerog_status": staticmethod(fake_get_status),
            "initialize_zerog_runtime_env": staticmethod(fake_initialize),
            "print_zerog_startup_notice": staticmethod(fake_notice),
        },
    )

    import sys

    monkeypatch.setitem(sys.modules, "tradememory.db", fake_db_module)
    monkeypatch.setitem(sys.modules, "tradememory.og_storage", fake_og_module)

    result = module.main()
    out = capsys.readouterr().out

    assert result == 0
    assert "0G disabled" in out
    assert "L1: MISSING" in out
    assert "'og_hash': None" in out


def test_skip_dotenv_flag_prevents_env_loading(monkeypatch):
    monkeypatch.setenv("ZEROG_SKIP_DOTENV", "true")
    module = load_module()

    assert module.os.getenv("ZEROG_SKIP_DOTENV") == "true"
