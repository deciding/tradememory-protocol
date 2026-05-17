# 0G Storage Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 0G decentralized storage as dual-write layer for L1/L2/L3 memory systems, providing immutable audit trail and cross-agent sharing.

**Architecture:** Layer-based dual-write where each memory layer (Episodic, Semantic, Procedural) writes to SQLite + 0G simultaneously. 0G provides audit hash stored in SQLite `og_hash` column. Graceful degradation if 0G fails.

**Tech Stack:** Python, `0g-storage-sdk` (PyPI), SQLite, Environment variables

---

## File Structure

```
src/tradememory/
├── og_storage.py        # NEW: OgStorage wrapper class
└── db.py               # MODIFY: Add og_hash columns + dual-write

tests/
├── test_og_storage.py  # NEW: Unit tests for OgStorage
```

---

## Task 1: Add 0g-storage-sdk to pyproject.toml

**Files:**
- Modify: `pyproject.toml:20-28`

- [ ] **Step 1: Add 0g-storage-sdk dependency**

Edit pyproject.toml to add the dependency in the main dependencies section:

```toml
dependencies = [
    "fastmcp>=2.0.0",
    "fastapi>=0.109.0",
    "uvicorn>=0.27.0",
    "pydantic>=2.5.3",
    "python-dotenv>=1.0.0",
    "requests>=2.31.0",
    "click>=8.0.0",
    "0g-storage-sdk>=0.1.0",
    "eth-account>=0.9.0",
]
```

- [ ] **Step 2: Commit**

```bash
git add pyproject.toml
git commit -m "feat: add 0g-storage-sdk dependency"
```

---

## Task 2: Create OgStorage module

**Files:**
- Create: `src/tradememory/og_storage.py`
- Test: `tests/test_og_storage.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_og_storage.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_og_storage.py -v
```

Expected: FAIL - module not found

- [ ] **Step 3: Write minimal implementation**

Create `src/tradememory/og_storage.py`:

```python
"""0G Storage integration for TradeMemory Protocol."""

import os
from typing import Optional, Tuple


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
        raise NotImplementedError("0G upload not yet implemented")

    def download(self, root_hash: str, output_path: str) -> bool:
        """Download data from 0G storage.

        Args:
            root_hash: 0G root hash
            output_path: Local path to save downloaded file

        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            return False
        raise NotImplementedError("0G download not yet implemented")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_og_storage.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tradememory/og_storage.py tests/test_og_storage.py
git commit -m "feat: add OgStorage module with basic structure"
```

---

## Task 3: Implement 0G upload in OgStorage

**Files:**
- Modify: `src/tradememory/og_storage.py`
- Modify: `tests/test_og_storage.py`

- [ ] **Step 1: Write the failing test**

Update `tests/test_og_storage.py`:

```python
    def test_upload_with_mock_success(self):
        from tradememory.og_storage import OgStorage
        storage = OgStorage(enabled=True, private_key="0x123", indexer_rpc="http://test")
        
        with patch('tradememory.og_storage.Indexer') as mock_indexer:
            mock_instance = MagicMock()
            mock_instance.upload.return_value = ({"rootHash": "0xabc"}, None)
            mock_indexer.return_value = mock_instance
            
            result = storage.upload({"test": "data"})
            assert result == "0xabc"
            mock_instance.upload.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_og_storage.py::TestOgStorage::test_upload_with_mock_success -v
```

Expected: FAIL - upload not implemented

- [ ] **Step 3: Write implementation**

Update `src/tradememory/og_storage.py` - add imports and implement upload:

```python
import json
import logging
import os
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


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
        self._blockchain_rpc = blockchain_rpc or os.environ.get("OG_BLOCKCHAIN_RPC", "https://evmrpc-testnet.0g.ai")
        self._indexer_rpc = indexer_rpc or os.environ.get("OG_INDEXER_RPC", "https://indexer-storage-testnet-turbo.0g.ai")

    def is_available(self) -> bool:
        """Check if 0G storage is configured and available."""
        if not self._enabled:
            return False
        return bool(self._private_key and self._indexer_rpc)

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
            from core.indexer import Indexer
            from core.file import ZgFile
            from eth_account import Account

            indexer = Indexer(self._indexer_rpc)
            account = Account.from_key(self._private_key)

            json_str = json.dumps(data, ensure_ascii=False)
            file = ZgFile.from_bytes(json_str.encode("utf-8"))

            result, err = indexer.upload(
                file,
                self._blockchain_rpc,
                account,
                {"expectedReplica": 1, "finalityRequired": True}
            )

            if err:
                logger.warning(f"0G upload failed: {err}")
                return None

            root_hash = result.get("rootHash") if result else None
            tx_hash = result.get("txHash") if result else None
            return (root_hash, tx_hash) if root_hash else None

        except Exception as e:
            logger.warning(f"0G upload error: {e}")
            return None

    def download(self, root_hash: str, output_path: str) -> bool:
        """Download data from 0G storage.

        Args:
            root_hash: 0G root hash
            output_path: Local path to save downloaded file

        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            return False

        try:
            from core.indexer import Indexer

            indexer = Indexer(self._indexer_rpc)
            indexer.download(root_hash, output_path)
            return True

        except Exception as e:
            logger.warning(f"0G download error: {e}")
            return False
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_og_storage.py::TestOgStorage::test_upload_with_mock_success -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tradememory/og_storage.py tests/test_og_storage.py
git commit -m "feat: implement OgStorage.upload() with 0G SDK"
```

---

## Task 4: Add og_hash columns to database schema

**Files:**
- Modify: `src/tradememory/db.py:64-335`

- [ ] **Step 1: Read current schema initialization**

Read `src/tradememory/db.py` around lines 170-215 to see episodic_memory table definition.

- [ ] **Step 2: Add ALTER TABLE for og_hash columns**

After line 214 (after episodic_memory indexes), add:

```python
            # Add og_hash column for 0G audit trail
            try:
                conn.execute(
                    "ALTER TABLE episodic_memory ADD COLUMN og_hash TEXT"
                )
            except Exception:
                pass  # Column already exists

            try:
                conn.execute(
                    "ALTER TABLE semantic_memory ADD COLUMN og_hash TEXT"
                )
            except Exception:
                pass  # Column already exists

            try:
                conn.execute(
                    "ALTER TABLE procedural_memory ADD COLUMN og_hash TEXT"
                )
            except Exception:
                pass  # Column already exists
```

- [ ] **Step 3: Commit**

```bash
git add src/tradememory/db.py
git commit -m "feat: add og_hash columns for 0G audit trail"
```

---

## Task 5: Integrate dual-write to insert_episodic

**Files:**
- Modify: `src/tradememory/db.py:734-768`

- [ ] **Step 1: Read current insert_episodic method**

Read `src/tradememory/db.py` lines 734-768 to understand the current implementation.

- [ ] **Step 2: Modify insert_episodic to add dual-write**

After the conn.execute INSERT, add:

```python
    def insert_episodic(self, data: Dict[str, Any]) -> bool:
        """Insert an episodic memory record."""
        import os
        og_hash = None
        
        # Try to upload to 0G storage
        if os.environ.get("OG_ENABLED", "").lower() == "true":
            try:
                from .og_storage import OgStorage
                og_storage = OgStorage()
                result = og_storage.upload({
                    "type": "episodic",
                    "id": data.get("id"),
                    "timestamp": data.get("timestamp"),
                    "context_json": data.get("context_json"),
                    "strategy": data.get("strategy"),
                    "direction": data.get("direction"),
                    "entry_price": data.get("entry_price"),
                    "exit_price": data.get("exit_price"),
                    "pnl": data.get("pnl"),
                    "pnl_r": data.get("pnl_r"),
                })
                if result:
                    og_hash = result[0]
            except Exception:
                pass  # Don't block on 0G failure

        data["og_hash"] = og_hash

        try:
            with self.get_connection() as conn:
                # ... rest of existing code ...
```

- [ ] **Step 3: Commit**

```bash
git add src/tradememory/db.py
git commit -m "feat: add 0G dual-write to insert_episodic"
```

---

## Task 6: Add dual-write to insert_semantic

**Files:**
- Modify: `src/tradememory/db.py:840-868`

- [ ] **Step 1: Read insert_semantic method**

- [ ] **Step 2: Add 0G upload similar to Task 5**

- [ ] **Step 3: Commit**

---

## Task 7: Add dual-write to upsert_procedural

**Files:**
- Modify: `src/tradememory/db.py:961-985`

- [ ] **Step 1: Read upsert_procedural method**

- [ ] **Step 2: Add 0G upload similar to Task 5**

- [ ] **Step 3: Commit**

---

## Task 8: Add environment variable validation

**Files:**
- Modify: `src/tradememory/og_storage.py`

- [ ] **Step 1: Add validate_config method**

```python
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
```

- [ ] **Step 2: Write test for validation**

- [ ] **Step 3: Commit**

---

## Task 9: Final verification

**Files:**
- Run: pytest

- [ ] **Step 1: Run all og_storage tests**

```bash
pytest tests/test_og_storage.py -v
```

- [ ] **Step 2: Run general tests to ensure no regression**

```bash
pytest tests/ -v --ignore=tests/test_owm_context.py --ignore=tests/test_dqs.py -x
```

- [ ] **Step 3: Commit final**

```bash
git commit -m "feat: complete 0G storage integration for L1/L2/L3"
```

---

## Implementation Complete

Once all tasks are done, the system will:
- Support dual-write to 0G for L1 (episodic), L2 (semantic), L3 (procedural) memory layers
- Store 0G root hash in SQLite `og_hash` column for audit trail
- Gracefully degrade if 0G fails (SQLite still works)
- Be togglable via `OG_ENABLED` environment variable