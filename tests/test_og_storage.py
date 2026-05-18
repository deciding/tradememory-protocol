import os
import pytest
import sys
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def clear_zerog_env(monkeypatch):
    for name in [
        "ZEROG_TESTNET_RPC_URL",
        "ZEROG_TESTNET_PRIVATE_KEY",
        "ZEROG_INDEXER_RPC",
        "OG_ENABLED",
        "OG_BLOCKCHAIN_RPC",
        "OG_PRIVATE_KEY",
        "OG_INDEXER_RPC",
    ]:
        monkeypatch.delenv(name, raising=False)


def test_config_status_disabled_when_missing_env(monkeypatch):
    monkeypatch.delenv("ZEROG_TESTNET_RPC_URL", raising=False)
    monkeypatch.delenv("ZEROG_TESTNET_PRIVATE_KEY", raising=False)
    monkeypatch.delenv("ZEROG_INDEXER_RPC", raising=False)

    from tradememory.og_storage import get_zerog_status

    status = get_zerog_status()

    assert status.enabled is False
    assert status.reason == "missing_env"
    assert "ZEROG_TESTNET_RPC_URL" in status.missing
    assert "ZEROG_TESTNET_PRIVATE_KEY" in status.missing
    assert "ZEROG_INDEXER_RPC" in status.missing


def test_get_zerog_status_does_not_mutate_runtime_env(monkeypatch):
    monkeypatch.setenv("ZEROG_TESTNET_RPC_URL", "https://evmrpc-testnet.0g.ai")
    monkeypatch.setenv("ZEROG_TESTNET_PRIVATE_KEY", "0xabc")
    monkeypatch.setenv("ZEROG_INDEXER_RPC", "https://indexer-storage-testnet-turbo.0g.ai")

    from tradememory.og_storage import OgStorage, get_zerog_status

    status = get_zerog_status()
    storage = OgStorage()

    assert status.enabled is True
    assert status.reason == "configured"
    assert status.missing == []
    assert storage._enabled is False
    assert storage._blockchain_rpc is None
    assert storage._private_key is None
    assert storage._indexer_rpc is None


def test_initialize_zerog_runtime_env_enables_default_og_storage_path(monkeypatch):
    monkeypatch.setenv("ZEROG_TESTNET_RPC_URL", "https://evmrpc-testnet.0g.ai")
    monkeypatch.setenv("ZEROG_TESTNET_PRIVATE_KEY", "0xabc")
    monkeypatch.setenv("ZEROG_INDEXER_RPC", "https://indexer-storage-testnet-turbo.0g.ai")

    from tradememory.og_storage import OgStorage, initialize_zerog_runtime_env

    synced = initialize_zerog_runtime_env()
    storage = OgStorage()

    assert synced is True
    assert os.environ["OG_ENABLED"] == "true"
    assert os.environ["OG_BLOCKCHAIN_RPC"] == "https://evmrpc-testnet.0g.ai"
    assert os.environ["OG_PRIVATE_KEY"] == "0xabc"
    assert os.environ["OG_INDEXER_RPC"] == "https://indexer-storage-testnet-turbo.0g.ai"
    assert storage._enabled is True
    assert storage._blockchain_rpc == "https://evmrpc-testnet.0g.ai"
    assert storage._private_key == "0xabc"
    assert storage._indexer_rpc == "https://indexer-storage-testnet-turbo.0g.ai"


def test_print_zerog_startup_notice_prints_clear_disabled_message(monkeypatch, capsys):
    monkeypatch.delenv("ZEROG_TESTNET_RPC_URL", raising=False)
    monkeypatch.delenv("ZEROG_TESTNET_PRIVATE_KEY", raising=False)
    monkeypatch.delenv("ZEROG_INDEXER_RPC", raising=False)

    from tradememory.og_storage import print_zerog_startup_notice

    status = print_zerog_startup_notice()
    captured = capsys.readouterr()

    assert status.enabled is False
    assert "0G Storage disabled" in captured.out
    assert "ZEROG_TESTNET_RPC_URL" in captured.out


def test_print_zerog_startup_notice_logs_enabled_message(monkeypatch):
    monkeypatch.setenv("ZEROG_TESTNET_RPC_URL", "https://evmrpc-testnet.0g.ai")
    monkeypatch.setenv("ZEROG_TESTNET_PRIVATE_KEY", "0xabc")
    monkeypatch.setenv("ZEROG_INDEXER_RPC", "https://indexer-storage-testnet-turbo.0g.ai")

    from tradememory.og_storage import print_zerog_startup_notice

    mock_logger = MagicMock()
    status = print_zerog_startup_notice(logger=mock_logger)

    assert status.enabled is True
    mock_logger.info.assert_called_once()
    assert "0G Storage enabled" in mock_logger.info.call_args.args[0]


class TestOgStorage:
    def test_initialization_defaults(self):
        from tradememory.og_storage import OgStorage

        storage = OgStorage()
        assert storage._enabled is False
        assert storage._private_key is None
        assert storage._indexer_rpc is None

    def test_is_available_returns_false_when_disabled(self):
        from tradememory.og_storage import OgStorage

        storage = OgStorage()
        assert storage.is_available() is False

    def test_upload_returns_none_when_disabled(self):
        from tradememory.og_storage import OgStorage

        storage = OgStorage()
        result = storage.upload({"test": "data"})
        assert result is None

    def test_upload_with_mock_success(self):
        import tradememory.og_storage as og_module
        from tradememory.og_storage import OgStorage

        storage = OgStorage(enabled=True, private_key="0x123", indexer_rpc="http://test")

        mock_indexer = MagicMock()
        mock_indexer.upload.return_value = ({"rootHash": "0xabc"}, None)

        mock_file = MagicMock()
        mock_account = MagicMock()

        with (
            patch.object(og_module, "Indexer", return_value=mock_indexer),
            patch.object(og_module, "ZgFile", return_value=mock_file),
            patch.object(og_module, "Account"),
        ):
            result = storage.upload({"test": "data"})
            assert result == ("0xabc", "")
            mock_indexer.upload.assert_called_once()

    def test_upload_with_mock_tx_hash(self):
        import tradememory.og_storage as og_module
        from tradememory.og_storage import OgStorage

        storage = OgStorage(enabled=True, private_key="0x123", indexer_rpc="http://test")

        mock_indexer = MagicMock()
        mock_indexer.upload.return_value = ({"rootHash": "0xabc", "txHash": "0xdef"}, None)

        mock_file = MagicMock()

        with (
            patch.object(og_module, "Indexer", return_value=mock_indexer),
            patch.object(og_module, "ZgFile", return_value=mock_file),
            patch.object(og_module, "Account"),
        ):
            result = storage.upload({"test": "data"})
            assert result == ("0xabc", "0xdef")

    def test_upload_passes_account_in_options(self):
        import tradememory.og_storage as og_module
        from tradememory.og_storage import OgStorage

        storage = OgStorage(enabled=True, private_key="0x123", indexer_rpc="http://test")

        mock_indexer = MagicMock()
        mock_indexer.upload.return_value = ({"rootHash": "0xabc", "txHash": "0xdef"}, None)

        mock_file = MagicMock()
        mock_account = MagicMock()
        mock_account.from_key.return_value = mock_account

        with (
            patch.object(og_module, "Indexer", return_value=mock_indexer),
            patch.object(og_module, "ZgFile", return_value=mock_file),
            patch.object(og_module, "Account", mock_account),
        ):
            result = storage.upload({"test": "data"})
            assert result == ("0xabc", "0xdef")
            _, _, _, upload_opts = mock_indexer.upload.call_args[0]
            assert upload_opts["account"] is mock_account

    def test_validate_config_disabled(self):
        from tradememory.og_storage import OgStorage

        storage = OgStorage(enabled=False)
        is_valid, msg = storage.validate_config()
        assert is_valid is True
        assert msg == "disabled"

    def test_validate_config_missing_key(self):
        from tradememory.og_storage import OgStorage

        storage = OgStorage(enabled=True, private_key=None, indexer_rpc="http://test")
        is_valid, msg = storage.validate_config()
        assert is_valid is False
        assert "OG_PRIVATE_KEY" in msg

    def test_validate_config_valid(self):
        from tradememory.og_storage import OgStorage

        storage = OgStorage(enabled=True, private_key="0x123", indexer_rpc="http://test")
        is_valid, msg = storage.validate_config()
        assert is_valid is True
        assert msg == "ok"
