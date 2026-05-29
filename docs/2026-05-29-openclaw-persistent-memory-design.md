# OpenClaw Persistent Memory Integration Design

## Goal

Design a clean integration between TradeMemory and OpenClaw's persistent memory system so that:

- L1 trading events keep their structured, queryable, auditable storage
- L2 semantic patterns and L3 procedural rules become accessible through OpenClaw's native memory retrieval pipeline
- memory remains isolated by `agentId`
- the design respects OpenClaw's memory architecture instead of fighting it

This document proposes a hybrid model:

- **L1 stays in TradeMemory SQLite**
- **L2 and L3 are written into OpenClaw daily memory markdown as structured fenced blocks**

This is the recommended design because it uses each storage system for the type of memory it handles best.

---

## Motivation

TradeMemory and OpenClaw solve different memory problems.

TradeMemory is optimized for **structured trading memory**:

- event records
- timestamps
- strategy filters
- behavioral state
- audit hashes
- optional 0G dual-write

OpenClaw is optimized for **agent memory retrieval into the LLM context window**:

- per-agent memory isolation
- files as source of truth
- chunked retrieval
- vector search over persisted text
- automatic context injection before generation

The integration goal is not to force one system to become the other. The goal is to let them cooperate.

In practical terms:

- TradeMemory should continue to own the structured event layer
- OpenClaw should carry the distilled, reusable knowledge that the agent benefits from seeing in future prompts

That leads directly to the recommended split:

- **L1 episodic trade records -> SQLite**
- **L2 semantic patterns -> OpenClaw markdown memory**
- **L3 procedural rules -> OpenClaw markdown memory**

---

## Why Not Put Everything Into OpenClaw Memory

It is tempting to push all TradeMemory layers into the OpenClaw memory system because OpenClaw already has:

- `agentId` isolation
- persistent markdown memory
- SQLite-backed vector indexing

That would be the wrong tradeoff for L1.

### Why L1 does not fit well in OpenClaw text memory

L1 is not just narrative memory. It needs:

- exact timestamps
- structured numeric values
- filtering by strategy/symbol/regime
- ordering and querying
- auditability
- optional 0G hashes and tx hashes

These are database problems, not markdown problems.

If L1 were pushed into plain OpenClaw markdown memory, TradeMemory would lose too much:

- harder analytics
- harder filtering
- harder consistency guarantees
- worse audit story

So L1 should remain in SQLite.

---

## Why Not Write L2 and L3 Directly Into `MEMORY.md`

At first glance, `MEMORY.md` looks like the natural place for distilled agent knowledge.

That approach is not recommended.

### Reason 1: `MEMORY.md` has a practical size limit

`MEMORY.md` is used as long-term identity/core memory and has a practical limit of roughly **20,000 characters** in the target usage model.

L2 and L3 are not static. They accumulate over time:

- new patterns become active
- old patterns become invalidated
- procedural corrections evolve
- behavior rules get superseded

If L2/L3 are written directly into `MEMORY.md`, the file will grow into a maintenance problem quickly.

That creates pressure to:

- rewrite or compact the file constantly
- manually merge or delete old rules
- risk losing historical context

That is the wrong operational model for evolving trading memory.

### Reason 2: `MEMORY.md` is a poor fit for append-heavy updates

L2/L3 change incrementally. Daily markdown logs are naturally append-oriented. `MEMORY.md` is not.

Using `MEMORY.md` as the primary writable target would make every semantic/procedural update into a text-editing and compaction problem.

### Conclusion

Because of the size limit and update pattern, **we should not directly modify `MEMORY.md` for L2/L3 persistence**.

Instead, we should write L2/L3 entries into the daily memory timeline and let OpenClaw's existing memory system index and retrieve them.

---

## Why Daily Markdown Is the Right Target

OpenClaw already persists daily agent memory under a per-agent directory and indexes it into the agent-specific SQLite memory index.

That gives us four benefits immediately.

### 1. It matches OpenClaw's persistence model

Daily files are already the append target for ongoing memory. L2/L3 updates are incremental, so they fit naturally there.

### 2. It avoids the `MEMORY.md` ceiling

Because the content is distributed over daily files, the long-term memory stream can grow without turning a single file into a bottleneck.

### 3. It preserves history

TradeMemory should not only keep the latest rule. It should also preserve how the agent's understanding evolved over time.

Daily markdown makes that history explicit.

### 4. It feeds OpenClaw retrieval automatically

Once the daily files are indexed, OpenClaw can retrieve relevant L2/L3 memory blocks and inject them into future prompts using the agent's own `agentId`.

That is exactly what we want.

---

## Why Code Fence Protection Matters

OpenClaw chunks and indexes memory for retrieval. If L2/L3 are written as ordinary prose, they may be split in ways that damage meaning.

Examples of bad outcomes:

- a pattern header gets separated from its evidence
- a procedural rule gets separated from its status
- an invalidation note gets retrieved without the rule it invalidates

That is why **L2 and L3 should be written as fenced structured blocks**.

### Purpose of fenced blocks

Code fences provide chunk-protection semantics for the memory pipeline:

- keep a memory unit together
- keep metadata attached to content
- reduce partial retrieval of incomplete memory fragments
- make later parsing possible if TradeMemory wants to reconstruct typed memory from markdown

In other words, the code fence is not cosmetic. It is part of the memory design.

---

## Recommended Storage Model

### L1: SQLite only

L1 remains in TradeMemory's structured database.

It continues to store:

- raw trade event data
- timestamps
- symbol / strategy / regime context
- PnL / R-multiple
- audit data
- optional 0G hashes

### L2: OpenClaw daily markdown

L2 semantic memory is written as a fenced structured block into the current day's memory file.

This includes:

- pattern description
- conditions
- confidence or evidence summary
- status (`active`, `invalidated`, `superseded`)

### L3: OpenClaw daily markdown

L3 procedural memory is also written into the current day's memory file.

This includes:

- execution rule
- behavioral correction
- sizing adjustment
- stop/continue constraints
- status (`active`, `superseded`, `invalidated`)

---

## Role of `agentId`

OpenClaw `agentId` should be the namespace boundary for this integration.

That means:

- one OpenClaw `agentId` -> one agent memory directory
- one OpenClaw `agentId` -> one OpenClaw vector index database
- one OpenClaw `agentId` -> one TradeMemory `agent_id` namespace

The simplest compatible model is:

- **TradeMemory `agent_id` = OpenClaw `agentId`**

That makes memory isolation consistent across both systems.

---

## Proposed L2/L3 Block Format

The block format should be explicit, typed, and parseable later if needed.

### L2 semantic block

```text
```tm-memory
type: L2
agent_id: ng_gold_v1
timestamp: 2026-05-29T12:00:00Z
status: active
strategy: london_breakout
symbol: XAUUSD
pattern: Retest entries outperform chase entries after narrow Asian range compression.
conditions:
  - Asian range is narrow
  - London open breakout closes with momentum
  - H1 ATR is normal to expanding
evidence: 8 wins / 11 trades
confidence: medium
```
```

### L3 procedural block

```text
```tm-memory
type: L3
agent_id: ng_gold_v1
timestamp: 2026-05-29T12:05:00Z
status: active
strategy: london_breakout
rule: After two failed breakout trades, reduce size to 0.5R until the next confirmed winner.
reason: Recent losses cluster during low-conviction re-entry attempts.
```
```

### Why this format is good

It is:

- readable by humans
- retrievable by OpenClaw memory search
- protected by code fences during chunking
- parseable later by TradeMemory if reconstruction is needed

---

## Memory Semantics

### L2 answers

L2 should answer:

- what appears to be true?
- under what conditions?
- how confident are we?

### L3 answers

L3 should answer:

- what should the agent do differently now?
- what rule should govern execution?
- what behavior should be reinforced or prevented?

This distinction matters because it keeps semantic pattern knowledge separate from procedural action rules.

---

## Update and Invalidation Strategy

Because daily markdown is append-oriented, we should not pretend old L2/L3 entries disappear.

Instead, each block should support lifecycle states:

- `active`
- `superseded`
- `invalidated`

This solves an important problem.

If a pattern stops working, the system should not silently delete the old one. It should record that the pattern was invalidated.

That preserves reasoning history and helps future analysis.

---

## Retrieval Behavior

In this design, retrieval happens through OpenClaw's existing agent memory flow.

Before response generation:

1. user prompt arrives
2. OpenClaw memory search runs for the active `agentId`
3. relevant daily markdown chunks are retrieved
4. fenced L2/L3 blocks are injected into prompt context

That gives the agent access to:

- learned patterns
- active procedural rules
- historical semantic/procedural updates

without requiring TradeMemory itself to rebuild a second retrieval engine for those layers.

---

## Why This Is Better Than Full OpenClaw-Native Storage

You could try to push all TradeMemory memory into OpenClaw's memory system.

That would make the architecture look simpler on paper, but in practice it would weaken the most valuable part of TradeMemory: the structured L1 event/audit layer.

The hybrid model is better because it preserves both systems' strengths.

### TradeMemory keeps

- structure
- auditability
- filtering
- metrics
- precise event history

### OpenClaw keeps

- memory injection
- text retrieval
- agent-scoped persistence
- chunked search over long-lived knowledge

---

## Recommended Implementation Phases

### Phase 1: Identity alignment

- ensure TM `agent_id` is mapped directly from OpenClaw `agentId`
- document this as the canonical integration identity rule

### Phase 2: L2/L3 fenced block emitter

- when TM generates L2 or L3 memory updates, output them in fenced `tm-memory` blocks
- emit to user / session flow so OpenClaw records them into daily markdown

### Phase 3: Retrieval convention

- standardize L2/L3 block structure so OpenClaw retrieval returns coherent chunks
- add `status` lifecycle field

### Phase 4: Optional parser

- if needed later, add a parser that can read fenced `tm-memory` blocks back from markdown and reconstruct typed semantic/procedural memory views

This parser is optional. The retrieval value already exists before it.

---

## Final Recommendation

Use a **hybrid integration**:

- **L1 in SQLite**
- **L2 and L3 in OpenClaw daily markdown**
- **all keyed by the same `agentId` / `agent_id`**

Do **not** write L2/L3 directly into `MEMORY.md` because:

- `MEMORY.md` has a practical size ceiling
- it is a bad fit for append-heavy evolving rules and patterns
- daily markdown matches the persistence model better

Use **fenced `tm-memory` blocks** for L2/L3 because:

- they protect memory units from being broken apart by chunking
- they keep metadata attached to the memory content
- they support future typed parsing if needed

This gives TradeMemory the strongest compatibility with OpenClaw's persistent memory system without sacrificing structured trading memory.
