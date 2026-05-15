# Trading AI Pipeline Report

**Date:** 2026-05-15
**Author:** TradeMemory Protocol

---

## 1. Current Implementation Status

### 1.1 MCP Service (TradeMemory Protocol)

TradeMemory Protocol is exposed as an MCP service via two access methods:

#### Local MCP (stdio transport)
```bash
pip install -e .
tradememory-protocol   # runs as local MCP server
```

Or via `.mcp.json` for AI clients:
```json
{
  "mcpServers": {
    "tradememory-protocol": {
      "command": "python",
      "args": ["-m", "tradememory"]
    }
  }
}
```

#### Web REST API (HTTP)
```bash
HOST=0.0.0.0 tradememory-api
```

- **35+ REST endpoints** including `/trade/record_decision`, `/trade/query_history`, `/owm/recall`, `/reflect/run_daily`, `/health`, etc.
- **Can be called via curl** — see `scripts/api_test.sh`
- Can be deployed via Docker for production: `docker compose -f docker-compose.hosted.yml up`
- MCP over HTTP transport layer is planned (not yet implemented — current web API is REST-only)

#### Python import (no server needed)
```python
from tradememory.mcp_server import remember_trade, recall_memories, get_strategy_performance
from tradememory.journal import TradeJournal
import asyncio

journal = TradeJournal()
result = asyncio.run(remember_trade(
    trade_id="T-001",
    symbol="BTCUSDT",
    direction="long",
    lot_size=0.1,
    strategy="breakout",
    confidence=0.8,
    reasoning="Volume spike + funding rate positive",
    market_context={"price": 95000, "atr": 500, "session": "asian"},
    outcome=None,
))
```

**Backend:** SQLite (`~/.tradememory/tradememory.db`) by default, backed by SQLAlchemy. Switch to PostgreSQL via `DATABASE_URL` env var.

---

### 1.2 Binance Skills (via Smithery)

Binance trading capabilities are available via the `binance-agentic-wallet` skill from Smithery's registry. Installed via:

```bash
npx -y @smithery/cli install @smithery/server-binance-agentic-wallet
```

Or from local skills folder at `skills/binance-skills-hub/binance-web3/binance-agentic-wallet/`.

Key capabilities:
- `baw market-order swap` — Token swap with quote preview
- `baw wallet send` — Send tokens to any address
- `baw wallet list` — View order history
- Market data, token audit, trading signals, address info, etc. (via additional skills in `skills/binance-skills-hub/binance-web3/`)

**Authentication:** Requires Binance Web3 login via OAuth link + wallet setup.

---

### 1.3 TradeMemory Integration with Binance

After each Binance trade executes, the trade record should be stored in TradeMemory for persistent memory. The workflow:

```
Binance Trade → remember_trade() → All 5 memory layers written
                           ↓
                   Semantic (patterns)
                   Episodic (trade history)
                   Procedural (execution quality)
                   Affective (emotional state)
                   Behavioral (disposition score)
```

Available MCP tools for integration:
- `remember_trade` — Record a new trade with full context
- `recall_memories` — OWM-weighted recall from all 5 layers
- `get_strategy_performance` — Performance stats per strategy
- `run_daily_reflection` — Pattern discovery and adjustment recommendations

Example integration point:
```python
# After Binance swap executes
import asyncio
from tradememory.mcp_server import remember_trade

asyncio.run(remember_trade(
    trade_id=f"BIN-{timestamp}",
    symbol="BTCUSDT",
    direction="long",
    lot_size=0.01,
    strategy="agentic-swap",
    confidence=0.75,
    reasoning="Smart money inflow signal + momentum breakout",
    market_context={"price": 96500, "funding_rate": 0.0001, "volume_24h": "high"},
    outcome={"entry_price": 96500, "swap_fee": 0.001},
))
```

---

## 2. Work in Progress

### 2.1 Binance Trade Test Cases

Currently developing test cases to validate the Binance trading skill integration:
- Verifying `baw market-order` quote accuracy
- Verifying swap execution and confirmation flow
- Verifying `baw wallet list` returns correct order status
- Error handling: insufficient balance, network timeout, invalid token

---

## 3. Open Question: Local Sandbox vs Web Service

### Option A: Local MCP (stdio transport)

**Pros:**
- Zero network latency — direct function calls within the same process
- No authentication needed — no security surface
- Works offline
- Simple `.mcp.json` config — works with Claude Code, Cursor, Windsurf, etc.
- No server infrastructure to maintain

**Cons:**
- Only accessible from the machine running it
- No multi-user sharing
- AI client (Claude Code) must be on the same machine

**Best for:** Personal use, single developer, offline environments.

---

### Option B: Web Service (HTTP/REST)

**Pros:**
- Accessible from anywhere — any AI client, any machine, any user
- Single deployment = unlimited AI agents can connect
- Built-in logging of all requests (audit trail)
- Easy to add authentication (API keys, OAuth)
- Scalable — run on cloud (Render, Railway, VPS)

**Cons:**
- Requires authentication for security
- Network latency per call
- Server infrastructure to maintain
- Need MCP-over-HTTP layer (not currently built — REST only)

**Best for:** Multi-user teams, cloud deployments, AI agents on remote machines.

---

### Recommendation

**Use both.** The architecture supports both simultaneously:

| Use Case | Method |
|---|---|
| Local development & testing | `pip install -e .` + local MCP stdio |
| Personal daily trading bot | Local MCP stdio (no network exposure) |
| Sharing with team / remote AI agents | Web REST API (deploy with Docker) |
| Future: MCP-over-HTTP for AI clients | Add MCP HTTP transport layer |

The web REST API is already implemented and working. If you want AI clients (Claude Code, etc.) to connect remotely via the standard MCP protocol over HTTP, an MCP HTTP transport layer would need to be added on top of the existing FastAPI server. This is a planned enhancement.

---

## 4. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     AI Trading Agent                         │
│              (Claude Code / Cursor / Custom)                 │
└──────────┬──────────────────────────────┬───────────────────┘
           │                              │
           │  MCP (stdio)                  │  HTTP/REST (curl)
           │  or MCP (HTTP)               │  or MCP-over-HTTP
           │                              │
┌──────────▼──────────────────────────────▼───────────────────┐
│                TradeMemory Protocol                          │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐   │
│  │  MCP Server  │  │  REST API    │  │  Python Import   │   │
│  │  (FastMCP)   │  │  (FastAPI)   │  │  (no server)     │   │
│  └──────┬───────┘  └──────┬───────┘  └─────────┬────────┘   │
│         │                 │                     │            │
│  ┌──────▼─────────────────▼─────────────────────▼────────┐  │
│  │              TradeMemory Core                          │  │
│  │  Journal · DB · OWM · Reflection · Adaptive Risk       │  │
│  └──────────────────────┬────────────────────────────────┘  │
│                         │                                    │
│              ┌──────────▼──────────┐                        │
│              │   SQLite / Postgres  │                        │
│              └─────────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
           │
           │  Binance API
           ▼
┌─────────────────────┐
│  Binance Web3      │
│  Agentic Wallet    │
│  (Smithery Skill)  │
└─────────────────────┘
```

---

## 5. Next Steps

- [ ] Complete Binance trade test cases
- [ ] Add MCP-over-HTTP transport layer for remote AI client connections
- [ ] Add API key authentication to web service
- [ ] Write integration tests: Binance trade → remember_trade → recall_memories
- [ ] Document deployment on cloud platforms (Render, Railway)