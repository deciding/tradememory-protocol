# 0G Storage Integration Design

## Overview

Add 0G decentralized storage as dual-write layer for TradeMemory Protocol's L1/L2/L3 memory systems, providing immutable audit trail and cross-agent sharing capability.

## Architecture

```
┌─────────────────────────────────────────────────┐
│                 TradeMemory Protocol            │
├─────────────────────────────────────────────────┤
│  MCP Server → remember_trade / recall_trades    │
├──────────────┬──────────────┬──────────────────┤
│   L1 Episodic│   L2 Semantic│   L3 Procedural  │
│   (Trades)   │  (Patterns)  │  (Behavior)      │
├──────────────┼──────────────┼──────────────────┤
│   SQLite DB  │   SQLite DB  │   SQLite DB      │
│   + 0G JSON  │   + 0G JSON  │   + 0G JSON       │
│   (Dual-wrt) │  (Dual-write)│   (Dual-write)    │
├──────────────┴──────────────┴──────────────────┤
│            OgStorage Wrapper                   │
│   - upload() / download() / get_audit_hash()   │
└─────────────────────────────────────────────────┘
```

## Data Mapping

| Layer | SQLite Table | 0G Storage Format | Key Benefit |
|-------|-------------|-------------------|-------------|
| L1 | `episodic_memory` | Full trade with context JSON | Immutable audit trail |
| L2 | `semantic_memory` | Pattern propositions + metrics | Cross-agent sharing |
| L3 | `procedural_memory` | Behavioral metrics JSON | Strategy behavior proof |

## Components

### 1. OgStorage Module (`src/tradememory/og_storage.py`)

**Environment Variables:**
- `OG_ENABLED` (bool): Toggle 0G writes, default false
- `OG_PRIVATE_KEY`: EVM private key for signing
- `OG_BLOCKCHAIN_RPC`: Blockchain RPC URL
- `OG_INDEXER_RPC`: Indexer RPC URL

**Public API:**
```python
class OgStorage:
    def upload(self, data: dict, network: str = "testnet") -> tuple[str, str]:  # (root_hash, tx_hash)
    def download(self, root_hash: str, output_path: str) -> bool:
    def get_audit_hash(self, root_hash: str) -> Optional[str]:
    def is_available(self) -> bool:
```

### 2. Database Schema Changes

Add `og_hash` column to relevant tables:
```sql
ALTER TABLE episodic_memory ADD COLUMN og_hash TEXT;
ALTER TABLE semantic_memory ADD COLUMN og_hash TEXT;
ALTER TABLE procedural_memory ADD COLUMN og_hash TEXT;
```

### 3. Dual-Write Integration

Modify db.py methods:
- `insert_episodic()`: Write SQLite → upload to 0G → store 0G hash in `og_hash`
- `insert_semantic()`: Same pattern
- `upsert_procedural()`: Same pattern

### 4. Error Handling

- If 0G upload fails: Log warning, don't block SQLite commit
- If `OG_ENABLED=false`: Skip 0G operations entirely
- Graceful degradation: SQLite remains primary, 0G is audit-only

## Implementation Steps

1. Add `0g-storage-sdk` to pyproject.toml dependencies
2. Create `src/tradememory/og_storage.py` with OgStorage class
3. Add `og_hash` columns via ALTER TABLE in db.py `_init_schema()`
4. Add dual-write to insert methods with OG_ENABLED flag
5. Add env var validation and error handling
6. Write unit tests for OgStorage

## Testing

- Mock 0G API for unit tests
- Integration test with testnet (requires OG_PRIVATE_KEY)

## Trade-offs

- ✅ Immutable audit trail for compliance
- ✅ Cross-agent sharing via 0G root hashes
- ✅ Graceful degradation (0G failure doesn't break SQLite)
- ✅ Gradual rollout via `OG_ENABLED` flag
- ⚠️ Additional storage cost (both SQLite + 0G)
- ⚠️ 0G propagation delay consideration for reads