"""Smoke test L1/L2/L3 dual-write with SQLite + 0G Storage."""

from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))

load_dotenv(REPO_ROOT / ".env")


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def normalize_private_key(value: str) -> str:
    if value.startswith("0x"):
        return value
    return f"0x{value}"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    from tradememory.db import Database
    from tradememory.og_storage import OgStorage

    os.environ["OG_ENABLED"] = "true"
    os.environ["OG_BLOCKCHAIN_RPC"] = require_env("ZEROG_TESTNET_RPC_URL")
    os.environ["OG_INDEXER_RPC"] = require_env("ZEROG_INDEXER_RPC")
    os.environ["OG_PRIVATE_KEY"] = normalize_private_key(require_env("ZEROG_TESTNET_PRIVATE_KEY"))

    db_path = REPO_ROOT / "data" / f"zerog_smoke_{uuid.uuid4().hex}.db"
    db = Database(str(db_path))

    captured: dict[str, dict[str, str]] = {}

    original_upload = OgStorage.upload

    def recording_upload(self, data: dict, network: str = "testnet"):
        result = original_upload(self, data, network)
        if result:
            layer = data.get("type", "unknown")
            captured[layer] = {"txHash": result[1], "rootHash": result[0]}
        return result

    OgStorage.upload = recording_upload

    try:
        episodic_id = f"epi-{uuid.uuid4().hex[:8]}"
        semantic_id = f"sem-{uuid.uuid4().hex[:8]}"
        procedural_id = f"pro-{uuid.uuid4().hex[:8]}"

        ok_l1 = db.insert_episodic(
            {
                "id": episodic_id,
                "timestamp": utc_now(),
                "context_json": {
                    "symbol": "EURUSD",
                    "timeframe": "H1",
                    "setup": "breakout_retest",
                },
                "context_regime": "trend",
                "context_volatility_regime": "normal",
                "context_session": "london",
                "context_atr_d1": 0.0081,
                "context_atr_h1": 0.0012,
                "strategy": "smoke_test_strategy",
                "direction": "long",
                "entry_price": 1.1050,
                "lot_size": 0.10,
                "exit_price": 1.1075,
                "pnl": 25.0,
                "pnl_r": 1.5,
                "hold_duration_seconds": 3600,
                "max_adverse_excursion": -8.0,
                "reflection": "Smoke test L1 upload",
                "confidence": 0.72,
                "tags": ["smoke", "l1", "zerog"],
                "retrieval_strength": 1.0,
                "retrieval_count": 0,
                "last_retrieved": None,
                "created_at": utc_now(),
            }
        )

        ok_l2 = db.insert_semantic(
            {
                "id": semantic_id,
                "proposition": "Breakout retests in trend regime have positive expectancy on EURUSD H1",
                "alpha": 8.0,
                "beta": 3.0,
                "sample_size": 11,
                "strategy": "smoke_test_strategy",
                "symbol": "EURUSD",
                "regime": "trend",
                "volatility_regime": "normal",
                "validity_conditions": {
                    "session": "london",
                    "min_rr": 1.2,
                },
                "last_confirmed": utc_now(),
                "last_contradicted": None,
                "source": "zerog_smoke_test",
                "retrieval_strength": 1.0,
                "created_at": utc_now(),
                "updated_at": utc_now(),
            }
        )

        ok_l3 = db.upsert_procedural(
            {
                "id": procedural_id,
                "strategy": "smoke_test_strategy",
                "symbol": "EURUSD",
                "behavior_type": "risk_sizing",
                "sample_size": 20,
                "avg_hold_winners": 5400.0,
                "avg_hold_losers": 2100.0,
                "disposition_ratio": 2.57,
                "actual_lot_mean": 0.12,
                "actual_lot_variance": 0.01,
                "kelly_fraction_suggested": 0.18,
                "lot_vs_kelly_ratio": 0.67,
            }
        )

        print("SQLite results:")
        print(f"  L1 insert_episodic:   {ok_l1}")
        print(f"  L2 insert_semantic:   {ok_l2}")
        print(f"  L3 upsert_procedural: {ok_l3}")
        print()

        print("0G upload results:")
        for label, key in [("L1", "episodic"), ("L2", "semantic"), ("L3", "procedural")]:
            result = captured.get(key)
            if not result:
                print(f"  {label}: MISSING")
                continue
            print(f"  {label}:")
            print(f"    txHash:   {result['txHash']}")
            print(f"    rootHash: {result['rootHash']}")

        with db.get_connection() as conn:
            l1_row = conn.execute(
                "SELECT id, og_hash, og_tx_hash FROM episodic_memory WHERE id = ?",
                (episodic_id,),
            ).fetchone()
            l2_row = conn.execute(
                "SELECT id, og_hash, og_tx_hash FROM semantic_memory WHERE id = ?",
                (semantic_id,),
            ).fetchone()
            l3_row = conn.execute(
                "SELECT id, og_hash, og_tx_hash FROM procedural_memory WHERE id = ?",
                (procedural_id,),
            ).fetchone()

        print()
        print("SQLite og_hash values:")
        print(f"  L1: {dict(l1_row) if l1_row else None}")
        print(f"  L2: {dict(l2_row) if l2_row else None}")
        print(f"  L3: {dict(l3_row) if l3_row else None}")

        missing = [k for k in ("episodic", "semantic", "procedural") if k not in captured]
        if missing or not (ok_l1 and ok_l2 and ok_l3):
            return 1

        return 0

    finally:
        OgStorage.upload = original_upload


if __name__ == "__main__":
    raise SystemExit(main())
