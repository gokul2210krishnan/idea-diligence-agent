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

### Documentation & Governance Architecture
- `README.md` — Updated with complete architecture, defense-in-depth boundaries, and setup walkthrough
- `brainstorming/Idea Diligence Agent - Project.docx` & `.pdf` — Full project specification synthesized with Edmund + Gokul architecture review
- `brainstorming/SECURITY_AND_GOVERNANCE_ARCHITECTURE.md` & `.docx` — Comprehensive guide to the 5 defense boundaries (Safety Gate, Budget Governor, Untrusted Web Data Boundary, State Authority Layer, Decision-Impact Unknowns)
- `scripts/build_security_doc.py` — Automated styled Word doc generator for the governance spec

### Verified
- All Pydantic model imports and instantiation ✅
- All Strands SDK imports (`Agent`, `@tool`, `BedrockModel`, `http_request`) ✅
- All custom tool imports ✅
- All prompt imports ✅
- Full orchestrator creation chain ✅
- AWS credentials authenticated via `sts.get_caller_identity()` ✅
- Branch pushed and Pull Request #1 opened on GitHub ✅

### Not Yet Done (Deferred to Phase 2)
- Live end-to-end run with a real idea
- Governance package (`src/governance/`) implementation
- Wiring `DiligenceState` into the orchestrator loop via the propose-validate-merge layer
- Decision-impact unknown triage model
- Verdict formatting and demo UI

---

## Phase 2: Multi-Agent Loop & Governance Layer — ⬜ NOT STARTED

**Goal:** Implement defense-in-depth governance (`src/governance/`), upgrade `DiligenceState` with decision-impact unknowns, wire the adaptive loop, and run the first live investigation.

### Planned Deliverables
1. **Safety & Scope Gate (`safety_gate.py`):** Pre-screen ideas before LLM invocation to reject adversarial or off-topic prompts.
2. **Hard Runtime Budget Governor (`budget_governor.py`):** Deterministic caps on loops (max 5), tool calls (max 25), and runtime (180s).
3. **Untrusted Data Isolation (`data_sanitizer.py`):** Quarantining external web scrape results within inert XML tags against prompt injection.
4. **State Authority Layer (`state_updater.py`):** Propose-Validate-Policy-Merge pipeline ensuring agents cannot corrupt state.
5. **Decision-Impact Unknowns Model:** Typed `UnknownItem` (`CRITICAL` vs `LOW`) to focus the adaptive loop on thesis dealbreakers.
6. **Adaptive Orchestrator Loop:** Dynamic dispatch based on open critical unknowns with budget tracking.
7. **Live End-to-End Test:** Execution with a real business idea.

---

## Phase 3: Verdict & Polish — ⬜ NOT STARTED

**Goal:** Build the verdict synthesis engine (GO/MODIFY/KILL), format output as a rich diligence report, add demo UI.

---

## Phase 4: Demo & Submission — ⬜ NOT STARTED

**Goal:** Record 5-min video, write submission copy, deploy (optional), submit to Devpost.
