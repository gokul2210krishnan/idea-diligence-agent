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

---

## Open Source Contributor & Documentation Overhaul — ✅ COMPLETE (Sep 13, 2026)

**Goal:** Provide comprehensive, accessible, and crystal-clear documentation so any open-source contributor can understand, run, test, and contribute to the project.

### Added & Updated
- `README.md` — Total rewrite with architecture diagram, 5 governance boundaries breakdown, 60-second zero-key quickstart, detailed setup guides for Bedrock and Gemini, CLI reference, and full directory map.
- `CONTRIBUTING.md` — Comprehensive contributor guide:
  - Mental model and architecture overview
  - Automated and manual environment setup across Windows, macOS, and Linux
  - Zero-key development mode and model provider setup
  - 42-test testing guide and instructions for writing new tests
  - Coding standards: Windows console CP1252 ASCII encoding safety rules, Pydantic v2 conventions, and governance invariants
  - Step-by-step GitHub PR workflow and checklist
  - High-impact contribution ideas and good first issues
- `CODE_OF_CONDUCT.md` — Contributor Covenant v2.1 with explicit maintainer contacts and enforcement guidelines.
- `scripts/setup.ps1` — Automated Windows PowerShell onboarding script (venv, dependencies, .env setup, test verification).
- `scripts/setup.sh` — Automated Linux/macOS Bash onboarding script.
- `.github/PULL_REQUEST_TEMPLATE.md` — Structured PR template for contributor submissions.

### Verified
- All automated tests passing via `python -m pytest` ✅
- Interactive web workspace verified via `python -m src.main --web` ✅
- Instant CLI demo verified via `python -m src.main --demo` ✅

---

## Control-plane fix (Gokul review) — ✅ COMPLETE (Sep 14, 2026)

Python now owns the research loop and budget. Governance fails closed.

### Changed
- Removed process-global `_session_state` / `_session_governor` and shared agent singletons
- `ResearchSession` isolates each investigation
- `run_research_loop` dispatches specialists only after `BudgetGovernor.begin_iteration`
- Session-bound tools refuse search/read once `try_consume_tool` denies
- Safety gate rejects when the semantic classifier errors (fails closed)
- State updater rejects unknown agents (fails closed)
- Live web investigations are capped (HTTP 429) and return HTTP 500 on failure
- Added `test/test_loop.py` covering dispatch order, budget stops, session isolation, and tool acknowledgement ingestion

---

## Model Provider & Runtime Resilience — ✅ COMPLETE (Sep 14, 2026)

Keep live investigations working reliably through current model IDs and third-party provider outages.

### Changed
- Upgraded default Google Gemini model from `gemini-2.5-flash` to `gemini-3.6-flash`
- Added provider resilience with 3-attempt exponential backoff for transient rate limits and outages (503, 429, UNAVAILABLE)
- Added graceful specialist skip handling: if an external model provider fails, the pipeline logs the failure, skips that specialist, and continues with remaining gathered evidence
- Enforced explicit `GEMINI_API_KEY` validation on initialization and enabled dotenv overriding
- Expanded test suite to **54 automated tests** with 100% offline pass rate
- Updated documentation and setup scripts (`README.md`, `CONTRIBUTING.md`, `setup.ps1`, `setup.sh`) to reflect 54 tests and architecture enhancements


