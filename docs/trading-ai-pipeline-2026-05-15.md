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

### 2.1 Polymarket BTC 15-Minute Trading Bot

Submodule added at `thirdparty/Polymarket-BTC-15-Minute-Trading-Bot`.

#### Architecture
- **Nautilus Trader** as the core trading engine (with Polymarket adapter)
- **6 signal processors** feeding a fusion engine:
  - SpikeDetection — probability deviation from 20-period MA
  - SentimentProcessor — Fear & Greed index integration
  - PriceDivergence — BTC spot vs Polymarket price divergence
  - OrderBookImbalance — CLOB order book skew detection
  - TickVelocity — 30s/60s price momentum in probability space
  - DeribitPCR — institutional options sentiment (Put/Call Ratio)
- **Risk engine** — $1 fixed position size, max exposure limits
- **Learning engine** — adapts fusion weights based on win rate
- **Paper trading** — `paper_trades.json` output with simulated P&L
- **Grafana exporter** — live metrics dashboard

#### Trade logic
- Triggers at **minute 13–14** of each 15-min Polymarket interval (minutes 780–840)
- Trend filter: price > 0.60 → buy YES; price < 0.40 → buy NO; 0.40–0.60 → skip
- Trades once per sub-interval using market start timestamp as key

#### Running the bot
```bash
cd thirdparty/Polymarket-BTC-15-Minute-Trading-Bot
python test.py                          # Test Gamma API connectivity
python 15m_bot_runner.py                # Paper trade (simulation mode)
python 15m_bot_runner.py --live         # Live trading (real money)
python view_paper_trades.py              # View simulation results
```

#### Integration point with TradeMemory
After each paper or live trade, the outcome should be stored in TradeMemory:
```python
from tradememory.mcp_server import remember_trade
import asyncio

asyncio.run(remember_trade(
    trade_id=f"POLY-{market_slug}-{sub_interval}",
    symbol="BTC-USD-15m",
    direction="long" if direction == "long" else "short",
    lot_size=1.0,          # $1 fixed
    strategy="polymarket-trend-filter",
    confidence=price_float,  # price = confidence proxy
    reasoning=f"Late-window trade at {price_float:.2%}, signal_score={signal.score}",
    market_context={
        "price": float(current_price),
        "sub_interval": sub_interval,
        "market_slug": market_slug,
        "fusion_score": fused.score,
        "fusion_confidence": fused.confidence,
    },
    outcome={
        "exit_price": float(exit_price),
        "pnl": float(pnl),
        "outcome": outcome,
    },
))
```

---

### 2.2 Polymarket + TradeMemory Test Plan

**Objective:** Validate the full pipeline — Polymarket BTC bot trades → TradeMemory records + recalls → OWM patterns surface.

#### Phase A: Unit Tests (no real money)

**A1. Signal Processor Isolation**
- Feed synthetic price series to each processor (SpikeDetection, TickVelocity, etc.)
- Verify signal output format matches `TradingSignal` schema
- Verify fusion engine weight application

**A2. Paper Trade → TradeMemory Integration**
- Run bot in paper-trading mode (`test_mode=True`, trades every 1 min)
- After each paper trade, call `remember_trade()` with full context
- Assert: trade appears in DB, all 5 memory layers written
- Assert: `get_strategy_performance(strategy="polymarket-trend-filter")` returns updated stats

**A3. OWM Recall from Polymarket Trades**
- Record 20+ paper trades across different market conditions
- Call `recall_memories(current_context)` with a new hypothetical context
- Assert: returns relevant past trades weighted by OWM scoring
- Assert: context drift detection fires when market regime changes

**A4. Reflection Engine on Polymarket Data**
- Call `run_daily_reflection()` with 20 paper trades
- Assert: returns pattern insights (e.g., "win rate higher when price > 0.65")
- Assert: adjustment recommendations are actionable

#### Phase B: Integration Tests (no real money)

**B1. End-to-End Paper Pipeline**
- `test.py` → verify Gamma API returns BTC 15-min markets
- `bot.py` (paper mode) → 50 paper trades
- `view_paper_trades.py` → verify win rate, P&L
- `remember_trade()` → all 50 trades in TradeMemory DB
- `recall_memories()` → verify recall relevance scoring > 0.5
- `get_strategy_performance()` → verify metrics match paper trades

**B2. Market Switch Resilience**
- Let bot cycle through multiple markets (wait for 3+ market switches)
- Assert: no crashes, trades fire correctly after each switch
- Assert: `remember_trade` trade IDs are unique per (market, sub_interval)

**B3. Performance Tracker vs TradeMemory Parity**
- Compare `paper_trades.json` (from bot) vs TradeMemory DB query
- Assert: trade count, win rate, total P&L all match
- Assert: `performance_tracker` metrics mirror TradeMemory computed metrics

#### Phase C: Live Tests (real money, small stakes)

**C1. Single Real Trade + Memory**
- Execute one live Polymarket trade ($1)
- Record outcome in TradeMemory
- Recall previous paper trades to verify OWM still works with mixed live/paper data

**C2. Live Trading Session (1 hour)**
- Run 4+ live trades in sequence
- After each trade: `remember_trade` → `recall_memories` → `get_strategy_performance`
- Log all responses for post-session analysis

#### Test Data Requirements

| Data | Source | When Needed |
|---|---|---|
| Polymarket BTC 15-min markets | Gamma API (`test.py`) | Always |
| Fear & Greed index | `NewsSocialDataSource` | A1, B1 |
| Coinbase BTC spot price | `CoinbaseDataSource` | A1, B1 |
| Order book (CLOB) | Polymarket CLOB API | A1 (OrderBookImbalance) |
| Deribit BTC options PCR | `DeribitPCRProcessor` | A1 (optional) |
| Paper trade outcomes | `bot.py` simulation | A2, B1, B3 |
| Live trade outcomes | Real Polymarket execution | C1, C2 |

#### Success Criteria

| Test | Pass Condition |
|---|---|
| A1 Signal processors | All 6 processors emit valid `TradingSignal` objects |
| A2 Paper → TradeMemory | 100% of paper trades appear in TradeMemory DB |
| A3 OWM recall | Recall returns 5+ relevant trades, top result score > 0.6 |
| A4 Reflection | Returns ≥ 1 pattern insight, ≥ 1 actionable adjustment |
| B1 End-to-end | All 50 trades mirrored between `paper_trades.json` and TradeMemory |
| B2 Market switch | 0 crashes across 5+ market switches |
| B3 Metrics parity | Win rate, P&L differ by < 1% between bot and TradeMemory |
| C1 Live + memory | Live trade accessible via `recall_memories` within 1 second |
| C2 1-hour session | All trades recorded, strategy win rate converges to ±5% of paper |

---

### 2.3 Binance Trade Test Cases

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