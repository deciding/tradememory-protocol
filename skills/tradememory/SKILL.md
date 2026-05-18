---
name: tradememory
description: |
  Compliance-grade decision audit trail for AI trading agents. Records every trading
  decision with full context (conditions, filters, indicators, risk state), SHA-256
  tamper detection, and structured export for MiFID II / EU AI Act readiness.
  
  Automatically integrates with Binance skills — records WHY each trade was made,
  recalls similar past setups before new trades, detects behavioral biases, and
  tracks strategy performance across sessions.
metadata:
  version: 0.5.1
  author: mnemox-ai
  requires:
    bins: [tradememory-api]
  install:
    - id: tradememory
      kind: pipx
      package: tradememory-protocol
      bins: [tradememory, tradememory-api]
      label: Install TradeMemory Protocol
license: MIT
---

# TradeMemory — Decision Audit Trail for AI Trading Agents

Every Binance skill executes trades. None of them record **why**.

TradeMemory is the compliance layer. When your AI agent opens a position, TradeMemory captures the full decision context: what conditions triggered the signal, which filters passed or blocked, the market indicators at that moment, risk state, and execution details. Every record is SHA-256 hashed for tamper detection.

**Why it matters:** MiFID II Article 17 mandates algorithmic trading audit trails. The EU AI Act (August 2025) requires high-risk AI systems to maintain systematic logging. ESMA's February 2026 supervisory briefing targets AI-driven trading. Non-compliance fines reach up to 15M EUR or 3% of global turnover.

## Installation

```bash
pipx install tradememory-protocol
```

Start the server:

```bash
tradememory-api
# Server running at http://127.0.0.1:8000
```

Or add to MCP config:

```json
{
  "mcpServers": {
    "tradememory": {
      "command": "uvx",
      "args": ["tradememory-protocol"]
    }
  }
}
```

## Storage

SQLite is the default storage backend. Optional 0G dual-write is enabled only when all three environment variables are set: `ZEROG_TESTNET_RPC_URL`, `ZEROG_TESTNET_PRIVATE_KEY`, and `ZEROG_INDEXER_RPC`.

If any of those variables are unset, TradeMemory falls back to SQLite-only storage and prints a startup notice.

## What TradeMemory Records

| Field | Description |
|-------|-------------|
| `timestamp` | UTC decision time |
| `agent_id` | Which agent/EA made the decision |
| `model_version` | Software version at decision time |
| `decision_type` | ENTRY, EXIT, HOLD, SKIP |
| `strategy` | Strategy name (e.g. VolBreakout) |
| `conditions` | Entry conditions evaluated (passed/failed with thresholds) |
| `filters` | Risk filters checked (spread gate, regime gate, portfolio limits) |
| `indicators` | Market snapshot (ATR, EMA, spread, session range) |
| `execution` | Ticket, price, slippage, latency |
| `regime` | Market regime at decision time (trending/ranging/transitioning) |
| `risk_state` | Consecutive losses, cooldown status, daily P&L |
| `memory_context` | Past trades recalled via Outcome-Weighted Memory |
| `data_hash` | SHA-256 of all inputs for tamper detection |

---

## REST API

### Record a Decision

```bash
POST http://127.0.0.1:8000/trade/record_decision
Content-Type: application/json

{
  "trade_id": "VB_20260326_0755",
  "symbol": "BTCUSDT",
  "direction": "long",
  "lot_size": 0.01,
  "strategy": "BreakoutEntry",
  "confidence": 0.75,
  "reasoning": "BTC broke above 87000 resistance with volume spike",
  "market_context": {
    "price": 87500.00,
    "session": "london",
    "regime": {"regime": "TRENDING", "atr_h1": 26.66, "atr_d1": 171.16},
    "decision_data": {
      "indicators": {"atr_d1": 171.16, "atr_m5": 8.53, "spread_pts": 12}
    }
  }
}
```

**Response:**

```json
{
  "success": true,
  "trade_id": "VB_20260326_0755",
  "timestamp": "2026-03-26T07:55:00Z"
}
```

### Get Decision Record

```bash
GET http://127.0.0.1:8000/audit/decision-record/{trade_id}
```

Returns a complete Trading Decision Record (TDR) with decision context, memory context, market snapshot, and SHA-256 data hash.

### Verify Integrity

```bash
GET http://127.0.0.1:8000/audit/verify/{trade_id}
```

```json
{
  "trade_id": "VB_20260326_0755",
  "verified": true,
  "stored_hash": "a3f8c9...",
  "computed_hash": "a3f8c9...",
  "match": true
}
```

Recomputes SHA-256 from stored inputs. If any field was tampered with, `match` will be `false`.

### Bulk Export

```bash
GET http://127.0.0.1:8000/audit/export?strategy=BreakoutEntry&start=2026-03-01&end=2026-03-31&format=jsonl
```

Export all TDRs as JSON or JSONL for regulatory submission.

---

## MCP Tools

When using MCP, these tools are available:

### remember_trade

Store a completed trade into memory. Automatically updates all memory layers.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| symbol | string | Yes | Trading pair (e.g. "BTCUSDT") |
| direction | string | Yes | "long" or "short" |
| entry_price | number | Yes | Entry price |
| exit_price | number | Yes | Exit price |
| pnl | number | Yes | Profit/loss in account currency |
| strategy_name | string | Yes | Strategy name |
| market_context | string | Yes | Natural language description of market conditions |
| pnl_r | number | No | P&L as R-multiple |
| context_regime | string | No | Market regime: trending_up, trending_down, ranging, volatile |
| confidence | number | No | Confidence level 0-1 |
| reflection | string | No | Lessons learned |

### recall_memories

Recall past trades in similar market conditions before entering new positions.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| symbol | string | Yes | Trading pair to filter by |
| market_context | string | Yes | Current market conditions (natural language) |
| context_regime | string | No | Current regime |
| strategy_name | string | No | Filter by strategy |
| limit | number | No | Max results (default 10) |

Returns past trades ranked by relevance and outcome quality.

### get_agent_state

Check current trading state: confidence, risk appetite, drawdown, win/loss streaks.

Returns recommended action: `normal`, `reduce_size`, or `stop_trading`.

### get_behavioral_analysis

Detect trading biases: overtrading, revenge trading, disposition effect, lot sizing inconsistency.

### get_strategy_performance

Get win rate, profit factor, and aggregate stats per strategy.

### create_trading_plan

Set conditional plans that trigger on specific market conditions.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| trigger_type | string | Yes | "market_condition", "drawdown", or "time_based" |
| trigger_condition | string | Yes | JSON describing when to trigger |
| planned_action | string | Yes | JSON describing what to do |
| reasoning | string | Yes | Why this plan was created |

### check_active_plans

Check if any active plans match current market conditions.

---

## Agent Workflow

### Before Each Trade

```
1. Call recall_memories(symbol, market_context, regime)
2. Review similar past trades and outcomes
3. Check get_agent_state() for drawdown/streak warnings
```

### After Each Trade

```
1. Call remember_trade(symbol, direction, entry_price, exit_price, pnl, strategy, market_context)
2. Include rich market_context for better future recall
3. Optionally add reflection for lessons learned
```

### Periodically

```
1. Call get_behavioral_analysis() to detect biases
2. Call get_strategy_performance() to track strategy stats
```

---

## Regulatory Alignment

| Regulation | Requirement | TradeMemory Coverage |
|------------|-------------|---------------------|
| MiFID II Article 17 | Record every algorithmic trading decision factor | Full decision chain: conditions, filters, indicators, execution |
| EU AI Act Article 14 | Human oversight of high-risk AI systems | Explainable reasoning + memory context for every decision |
| EU AI Act Logging | Systematic logging of every AI action and decision path | Automatic per-decision TDR with structured JSON |
| ESMA 2026 Briefing | Algorithms must be distinguishable, testable, identifiable | agent_id + model_version + strategy per record |

---

## Security

- **Never touches API keys.** TradeMemory does not execute trades, move funds, or access wallets.
- **Read and record only.** The agent passes context; TradeMemory stores it.
- **SQLite by default.** 0G dual-write is opt-in and requires `ZEROG_TESTNET_RPC_URL`, `ZEROG_TESTNET_PRIVATE_KEY`, and `ZEROG_INDEXER_RPC`; otherwise startup warns and uses SQLite only.
- **No external network calls.** Server runs locally. No data sent to third parties.
- **SHA-256 tamper detection.** Verify integrity at any time with `/audit/verify`.

---

## Links

- **PyPI**: [tradememory-protocol](https://pypi.org/project/tradememory-protocol/)
- **GitHub**: [mnemox-ai/tradememory-protocol](https://github.com/mnemox-ai/tradememory-protocol)
- **Author**: [mnemox-ai](https://github.com/mnemox-ai)
