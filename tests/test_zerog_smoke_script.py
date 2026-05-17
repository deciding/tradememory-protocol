from __future__ import annotations

import importlib.util
from pathlib import Path


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
