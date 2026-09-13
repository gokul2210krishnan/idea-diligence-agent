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

## Phase 2: Multi-Agent Loop & Governance Layer — ✅ COMPLETE

**Goal:** Implement defense-in-depth governance (`src/governance/`), upgrade `DiligenceState` with decision-impact unknowns, and wire the adaptive loop.

### Added
- `src/governance/safety_gate.py` — deterministic + semantic pre-screen
- `src/governance/budget_governor.py` — iteration, tool-call, and wall-clock caps
- `src/governance/data_sanitizer.py` — untrusted web envelopes
- `src/governance/state_updater.py` — propose / validate / merge
- Decision-impact `UnknownItem` and adaptive orchestrator dispatch

---

## Phase 3: Verdict & Polish — ✅ COMPLETE (Sep 13, 2026)

**Goal:** Build the verdict synthesis engine, format a professional diligence report, and add demo UI.

### Added
- `src/evidence.py` — second-pass FACT/ASSUMPTION/INFERENCE/UNKNOWN classifier and confidence scoring
- `src/verdict.py` — deterministic GO/MODIFY/KILL engine with optional hybrid prose
- `src/report.py` — markdown, JSON, and Rich terminal dossiers
- `src/web/` — FastAPI demo UI with verdict stamp, dimension scores, and evidence ledger
- CLI flags: `--demo`, `--json`, `--output`, `--web`
- `VerdictReport` now includes dimension scores, evidence mix, risks, and next steps
- Evidence items carry a `category` through the state updater

### Verified
- Unit tests for classifier, scoring rules, GO/MODIFY/KILL paths, and report rendering
- Web API health, demo, and mocked live endpoints
- CLI `--demo` JSON and markdown export

---

## Phase 4: Demo & Submission — ✅ COMPLETE (Sep 13, 2026)

**Goal:** Make the project demoable and submission-ready.

### Added
- `SUBMISSION.md` — Devpost copy (inspiration, build, challenges, what's next)
- `DEMO.md` — timed 5-minute walkthrough script
- `examples/sample_investigation.json` — canned restaurant-inventory investigation
- `test/` suite + `pytest.ini` (no API keys required)
- README updated for verdict engine, web UI, and test commands

### Operator follow-ups (not in repo)
- Record the Devpost video from `DEMO.md`
- Optional AWS AgentCore deploy / builder.aws.com post
