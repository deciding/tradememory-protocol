import pytest
import sys
from unittest.mock import patch, MagicMock


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
