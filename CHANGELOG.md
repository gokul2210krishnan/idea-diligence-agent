# Changelog — Idea Diligence Agent

All notable progress on the hackathon build, tracked by phase.

---

## Phase 1: Walking Skeleton — ✅ COMPLETE (Sep 11, 2026)

**Goal:** Build the full project structure end-to-end. Prove the Strands SDK, Bedrock, and all imports work before adding real agent logic.

### Added

#### Project Foundation
- `requirements.txt` — Core dependencies: `strands-agents>=1.55.0`, `strands-agents-tools>=0.1.0`, `pydantic>=2.0.0`
- All dependencies installed and verified

#### Data Models (`src/models.py`)
- `DiligenceState` — The canonical research state (per Gokul's architecture)
  - Holds: idea, problem analysis, customer segments, competitors, economics, evidence list, unknowns, research history, and verdict
  - Helper methods: `is_research_complete()`, `has_budget_remaining()`, `get_critical_unknowns()`, `add_evidence()`, `log_action()`
- `EvidenceType` enum — `FACT`, `ASSUMPTION`, `INFERENCE`, `UNKNOWN`
- `Verdict` enum — `GO`, `MODIFY`, `KILL`
- `Evidence`, `CustomerSegment`, `Competitor`, `BusinessModel`, `ProblemAnalysis`, `EconomicAnalysis`, `VerdictReport`, `ResearchAction` — supporting Pydantic models

#### Custom Research Tools (`src/tools.py`)
- `search_web(query)` — DuckDuckGo search via `http_request` (no API key needed)
- `read_webpage(url)` — HTTP fetch + truncation to 15K chars for LLM context safety
- `save_finding(category, content, evidence_type, source, confidence)` — Structured finding recorder that outputs JSON tagged with evidence classification

#### Agent System Prompts (`src/prompts.py`)
- `PROBLEM_AGENT_PROMPT` — Research problem, customers, pain severity, demand signals
- `COMPETITION_AGENT_PROMPT` — Find competitors, pricing pages, reviews, market gaps
- `ECONOMICS_AGENT_PROMPT` — Evaluate pricing, revenue models, TAM, unit economics
- `ORCHESTRATOR_PROMPT` — Coordinate agents, synthesize evidence, render GO/MODIFY/KILL verdict

#### Specialist Agents (`src/agents/`)
- `problem_agent.py` — Factory creating a Strands Agent with Bedrock Claude Sonnet 4 + research tools
- `competition_agent.py` — Same pattern, competition-focused prompt
- `economics_agent.py` — Same pattern, economics-focused prompt

#### Orchestrator (`src/agents/orchestrator.py`)
- Agents-as-tools pattern: each specialist wrapped as a `@tool` callable by the orchestrator LLM
- `create_orchestrator()` — Returns a configured orchestrator Agent
- `run_diligence(idea)` — Main entry point: idea in → verdict out

#### CLI Entry Point (`src/main.py`)
- Command-line mode: `python -m src.main "Your idea here"`
- Interactive mode: prompts for input if no arguments given

### Verified
- All Pydantic model imports and instantiation ✅
- All Strands SDK imports (`Agent`, `@tool`, `BedrockModel`, `http_request`) ✅
- All custom tool imports ✅
- All prompt imports ✅
- Full orchestrator creation chain ✅
- AWS credentials authenticated via `sts.get_caller_identity()` ✅

### Not Yet Done
- No live end-to-end run with a real idea (agents wired but not exercised)
- DiligenceState not yet integrated into the orchestrator loop (agents return free-text, not structured state updates)
- No Strands Graph pattern (using agents-as-tools for now)
- No verdict formatting
- No web UI
- No demo video

---

## Phase 2: Multi-Agent Loop — ⬜ NOT STARTED

**Goal:** Wire DiligenceState into the orchestrator, implement the adaptive research loop, run the first real investigation.

---

## Phase 3: Verdict & Polish — ⬜ NOT STARTED

**Goal:** Build the verdict engine, format output as a diligence report, add demo UI.

---

## Phase 4: Demo & Submission — ⬜ NOT STARTED

**Goal:** Record video, write submission, deploy (optional), submit to Devpost.
