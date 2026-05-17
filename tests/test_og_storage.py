import pytest
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
