"""0G Storage integration for TradeMemory Protocol."""

import json
import logging
import os
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from core.indexer import Indexer
    from core.file import ZgFile
    from eth_account import Account
except ImportError:
    Indexer = None
    ZgFile = None
    Account = None


class OgStorage:
    """0G Storage wrapper providing dual-write capability."""

    def __init__(
        self,
        enabled: bool = None,
        private_key: str = None,
        blockchain_rpc: str = None,
        indexer_rpc: str = None,
    ):
        self._enabled = enabled or os.environ.get("OG_ENABLED", "").lower() == "true"
        self._private_key = private_key or os.environ.get("OG_PRIVATE_KEY")
        self._blockchain_rpc = blockchain_rpc or os.environ.get("OG_BLOCKCHAIN_RPC")
        self._indexer_rpc = indexer_rpc or os.environ.get("OG_INDEXER_RPC")

    def is_available(self) -> bool:
        """Check if 0G storage is configured and available."""
        if not self._enabled:
            return False
        return bool(self._private_key and self._indexer_rpc)

    def upload(self, data: dict, network: str = "testnet") -> Optional[str]:
        """Upload data to 0G storage.

        Args:
            data: Dictionary to upload as JSON
            network: Network to use (testnet/mainnet)

        Returns:
            Root hash string or None if unavailable
        """
        if not self.is_available():
            return None

        try:
            if Indexer is None:
                raise ImportError("0G SDK not installed")

            indexer = Indexer(self._indexer_rpc)
            account = Account.from_key(self._private_key)

            json_str = json.dumps(data, ensure_ascii=False)
            file = ZgFile.from_bytes(json_str.encode("utf-8"))

            result, err = indexer.upload(
                file,
                self._blockchain_rpc,
                account,
                {"expectedReplica": 1, "finalityRequired": True},
            )

            if err:
                logger.warning(f"0G upload failed: {err}")
                return None

            root_hash = result.get("rootHash") if result else None
            return root_hash

        except Exception as e:
            logger.warning(f"0G upload error: {e}")
            return None

    def download(self, root_hash: str, output_path: str) -> bool:
        """Download data from 0G storage."""
        if not self.is_available():
            return False
        raise NotImplementedError("0G download not yet implemented")
