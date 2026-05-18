"""0G Storage integration for TradeMemory Protocol."""

from dataclasses import dataclass
import json
import logging
import os
import sys
import types
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

ZEROG_REQUIRED_ENV_VARS = [
    "ZEROG_TESTNET_RPC_URL",
    "ZEROG_TESTNET_PRIVATE_KEY",
    "ZEROG_INDEXER_RPC",
]


@dataclass(frozen=True)
class ZerogStatus:
    enabled: bool
    reason: str
    missing: list[str]


def get_zerog_status() -> ZerogStatus:
    """Return whether the optional 0G integration is fully configured."""
    missing = [name for name in ZEROG_REQUIRED_ENV_VARS if not os.getenv(name)]

    if missing:
        return ZerogStatus(enabled=False, reason="missing_env", missing=missing)

    return ZerogStatus(enabled=True, reason="configured", missing=[])


def print_zerog_startup_notice(logger: logging.Logger | None = None) -> ZerogStatus:
    """Emit a clear startup message describing 0G availability."""
    status = get_zerog_status()
    if status.enabled:
        message = "0G Storage enabled (SQLite + 0G dual-write)"
    else:
        missing = ", ".join(status.missing) or "none"
        message = f"0G Storage disabled ({status.reason}); missing: {missing}"

    if logger is None:
        print(message)
    else:
        logger.info(message)

    return status


def _install_zerog_config_shim() -> None:
    """Install a minimal config module for the 0G SDK import path.

    The current storage SDK publishes top-level `core.*` modules that import a
    top-level `config` module, but that module is not shipped in the wheel.
    This shim provides the constants required by the storage SDK so imports work
    from a normal installed environment.
    """
    if "config" in sys.modules:
        return

    config = types.ModuleType("config")
    config.DEFAULT_CHUNK_SIZE = 256
    config.DEFAULT_SEGMENT_MAX_CHUNKS = 1024
    config.DEFAULT_SEGMENT_SIZE = config.DEFAULT_CHUNK_SIZE * config.DEFAULT_SEGMENT_MAX_CHUNKS
    config.DEFAULT_BATCH_SIZE = config.DEFAULT_SEGMENT_SIZE
    config.EMPTY_CHUNK_HASH = bytes(32)
    config.ZERO_HASH = "0x" + "00" * 32
    sys.modules["config"] = config


_install_zerog_config_shim()

try:
    from core.file import ZgFile
    from core.indexer import Indexer
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
        if enabled is None:
            self._enabled = os.environ.get("OG_ENABLED", "").lower() == "true"
        else:
            self._enabled = enabled

        if private_key is None:
            self._private_key = os.environ.get("OG_PRIVATE_KEY")
        else:
            self._private_key = private_key

        if blockchain_rpc is None:
            self._blockchain_rpc = os.environ.get("OG_BLOCKCHAIN_RPC")
        else:
            self._blockchain_rpc = blockchain_rpc

        if indexer_rpc is None:
            self._indexer_rpc = os.environ.get("OG_INDEXER_RPC")
        else:
            self._indexer_rpc = indexer_rpc

    def is_available(self) -> bool:
        """Check if 0G storage is configured and available."""
        if not self._enabled:
            return False
        return bool(self._private_key and self._indexer_rpc)

    def validate_config(self) -> Tuple[bool, str]:
        """Validate 0G configuration.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self._enabled:
            return True, "disabled"

        if not self._private_key:
            return False, "OG_PRIVATE_KEY is required when OG_ENABLED=true"

        if not self._indexer_rpc:
            return False, "OG_INDEXER_RPC is required when OG_ENABLED=true"

        return True, "ok"

    def upload(self, data: dict, network: str = "testnet") -> Optional[Tuple[str, str]]:
        """Upload data to 0G storage.

        Args:
            data: Dictionary to upload as JSON
            network: Network to use (testnet/mainnet)

        Returns:
            Tuple of (root_hash, tx_hash) or None if unavailable
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
                {
                    "tags": b"\x00",
                    "finalityRequired": True,
                    "expectedReplica": 1,
                    "account": account,
                },
            )

            if err:
                logger.warning(f"0G upload failed: {err}")
                return None

            root_hash = result.get("rootHash") if result else None
            tx_hash = result.get("txHash") if result else None

            if not root_hash:
                return None

            return root_hash, tx_hash or ""

        except Exception as e:
            logger.warning(f"0G upload error: {e}")
            return None

    def download(self, root_hash: str, output_path: str) -> bool:
        """Download data from 0G storage."""
        if not self.is_available():
            return False
        raise NotImplementedError("0G download not yet implemented")
