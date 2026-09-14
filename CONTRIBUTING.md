# Contributing to Idea Diligence Agent

Welcome to the **Idea Diligence Agent** project! We are thrilled that you want to contribute. Whether you are fixing a typo in documentation, adding a new specialist agent, strengthening governance checks, or refining our web workspace, your contributions are invaluable.

This guide provides everything you need to understand the architecture, set up your development environment, run the application, execute tests, and submit a pull request.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Architecture & Mental Model](#architecture--mental-model)
  - [Core Concept: Skeptical Due Diligence](#core-concept-skeptical-due-diligence)
  - [The 5 Governance Boundaries](#the-5-governance-boundaries)
  - [Where Things Live in `src/`](#where-things-live-in-src)
- [Setting Up Your Development Environment](#setting-up-your-development-environment)
  - [Prerequisites](#prerequisites)
  - [Option A: Automated Setup Script](#option-a-automated-setup-script)
  - [Option B: Manual Setup](#option-b-manual-setup)
- [Configuring Model Providers](#configuring-model-providers)
  - [Option 1: Google Gemini (Fastest & Free Tier)](#option-1-google-gemini-fastest--free-tier)
  - [Option 2: Amazon Bedrock (Production AWS)](#option-2-amazon-bedrock-production-aws)
  - [Option 3: Zero-Key Development Mode](#option-3-zero-key-development-mode)
- [Running the Project Locally](#running-the-project-locally)
  - [Interactive Web Workspace](#interactive-web-workspace)
  - [Instant CLI Demo](#instant-cli-demo)
  - [Live Governed Investigation](#live-governed-investigation)
  - [Machine-Readable JSON Output](#machine-readable-json-output)
- [Testing Guide](#testing-guide)
  - [Running the Test Suite](#running-the-test-suite)
  - [Writing New Tests](#writing-new-tests)
- [Coding Standards & Invariants](#coding-standards--invariants)
  - [1. Windows Console Safety (CP1252 / ASCII Encoding)](#1-windows-console-safety-cp1252--ascii-encoding)
  - [2. The 5 Governance Invariants](#2-the-5-governance-invariants)
  - [3. Type Safety & Pydantic v2](#3-type-safety--pydantic-v2)
  - [4. Agent & Tool Isolation](#4-agent--tool-isolation)
- [Development & Git Workflow](#development--git-workflow)
  - [1. Fork & Branch](#1-fork--branch)
  - [2. Keep Commits Focused](#2-keep-commits-focused)
  - [3. Run Quality Checks](#3-run-quality-checks)
  - [4. Submit a Pull Request](#4-submit-a-pull-request)
- [Ideas for Contributions (Good First Issues)](#ideas-for-contributions-good-first-issues)
- [Getting Help & Maintainers](#getting-help--maintainers)

---

## Code of Conduct

This project is governed by the [Contributor Covenant v2.1](CODE_OF_CONDUCT.md). By contributing, you agree to uphold a welcoming, respectful, and inclusive environment for all community members.

---

## Architecture & Mental Model

### Core Concept: Skeptical Due Diligence

Unlike typical LLM chat applications that uncritically validate user assumptions, **Idea Diligence Agent** is designed as a skeptical, analytical partner. Its job is to find the hidden risks, flawed unit economics, and competitive roadblocks in a startup idea before the founder invests months of effort.

### The 5 Governance Boundaries

Every feature or change must respect the five architectural security boundaries:

```text
[User Prompt]
      │
      ▼
Boundary 1: Safety & Scope Gate (Regex blocklist + semantic classifier)
      │
      ▼
Boundary 2: Hard Runtime Budget Governor (Deterministic loop/tool/time caps)
      │
      ▼
[Specialist Agents: Problem, Competition, Economics]
      │
      ▼
Boundary 3: Untrusted Web Data Quarantine (<untrusted_external_evidence> XML)
      │
      ▼
Boundary 4: State Authority Layer (Propose-Validate-Policy-Merge pipeline)
      │
      ▼
Boundary 5: Decision-Impact Unknown Triage (CRITICAL vs LOW dealbreakers)
      │
      ▼
[Verdict Synthesis Engine] (Deterministic scoring rules + narrative synthesis)
```

### Where Things Live in `src/`

- [`src/models.py`](src/models.py): Canonical Pydantic v2 schemas: `DiligenceState`, `Evidence`, `EvidenceType`, `VerdictReport`, `UnknownItem`, and `DecisionImpact`.
- [`src/model_provider.py`](src/model_provider.py): Centralized model factory supporting Google Gemini and Amazon Bedrock with role-specific routing.
- [`src/prompts.py`](src/prompts.py): System prompts with prompt-injection defense directives (`_INJECTION_DEFENSE`) across all specialist agents.
- [`src/session.py`](src/session.py): Isolated per-investigation `ResearchSession` tracking state, governor, dispatched specialists, and follow-ups without process-global mutable state.
- [`src/tools.py`](src/tools.py): Custom research tools (`search_web`, `read_webpage`, `save_finding`) with data sanitization, bound per investigation session via `create_research_tools` for in-flight budget checks and merge validation.
- [`src/governance/`](src/governance/):
  - `safety_gate.py`: Pre-flight prompt screening (fails closed on errors).
  - `budget_governor.py`: Deterministic circuit breakers (`begin_iteration`, `try_consume_tool`).
  - `data_sanitizer.py`: Web scraping quarantine and Unicode cleaning.
  - `state_updater.py`: State mutation validator ensuring agents cannot write unauthorized data (fails closed for unknown agents).
- [`src/agents/`](src/agents/):
  - `orchestrator.py`: Python-owned research loop managing specialist selection, dispatch, and handoff to the verdict engine.
  - `problem_agent.py`: Specialist evaluating problem pain, customer segments, and demand.
  - `competition_agent.py`: Specialist mapping direct/indirect competitors and market gaps.
  - `economics_agent.py`: Specialist analyzing pricing, unit economics, and TAM/SAM.
- [`src/evidence.py`](src/evidence.py): Second-pass epistemic classifier downgrading unsourced FACTs and recalibrating confidence.
- [`src/verdict.py`](src/verdict.py): Synthesis engine combining dimensional scoring (problem, competition, economics) with deterministic GO / MODIFY / KILL decision trees.
- [`src/report.py`](src/report.py): Dossier rendering for terminal (Rich panels), Markdown, and JSON.
- [`src/demo_data.py`](src/demo_data.py): Loader for pre-computed sample investigations.
- [`src/web/`](src/web/):
  - `app.py`: FastAPI server with `/api/health`, `/api/demo`, and `/api/diligence` (with semaphore-based concurrency limiting).
  - `static/`: Modern, responsive dark-mode workspace UI (HTML/CSS/vanilla JS).
- [`src/main.py`](src/main.py): Single CLI and web server entry point.

---

## Setting Up Your Development Environment

### Prerequisites

- **Python 3.12 or higher**
- **Git**
- A terminal (PowerShell, Bash, or Zsh)

### Option A: Automated Setup Script

We provide onboarding scripts that set up the virtual environment, install all packages, configure your environment file, and run the test suite in one step:

**On Windows (PowerShell):**
```powershell
.\scripts\setup.ps1
```

**On Linux / macOS (Bash):**
```bash
chmod +x ./scripts/setup.sh
./scripts/setup.sh
```

### Option B: Manual Setup

1. **Clone your fork:**
   ```bash
   git clone https://github.com/<your-username>/idea-diligence-agent.git
   cd idea-diligence-agent
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # Linux / macOS
   python3 -m venv .venv
   source .venv/bin/activate

   # Windows PowerShell
   python -m venv .venv
   .venv\Scripts\Activate.ps1

   # Windows Command Prompt
   .venv\Scripts\activate.bat
   ```

3. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Verify installation by running the test suite:**
   ```bash
   python -m pytest
   ```
   All 54 tests should pass immediately.

---

## Configuring Model Providers

Copy the example environment configuration:
```bash
cp .env.example .env
```

### Option 1: Google Gemini (Fastest & Free Tier)

Gemini 3.6 Flash is ideal for development due to fast inference and a generous free tier:

1. Obtain an API key from [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Configure `.env`:
   ```env
   DEFAULT_MODEL_PROVIDER=gemini
   DEFAULT_MODEL_ID=gemini-3.6-flash
   GEMINI_API_KEY=your_actual_gemini_key_here
   ```

### Option 2: Amazon Bedrock (Production AWS)

To use Amazon Bedrock with Anthropic Claude models:

1. Ensure your AWS credentials have permission for `bedrock:InvokeModel`.
2. Configure `.env`:
   ```env
   DEFAULT_MODEL_PROVIDER=bedrock
   DEFAULT_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0
   AWS_REGION=us-east-1
   AWS_ACCESS_KEY_ID=your_aws_key
   AWS_SECRET_ACCESS_KEY=your_aws_secret
   ```

### Option 3: Zero-Key Development Mode

**You do NOT need an API key to contribute!**
- The entire test suite (`python -m pytest`) runs offline without API keys.
- You can test the CLI with `--demo` (`python -m src.main --demo`).
- You can test and modify the Web UI with `--web` (`python -m src.main --web`), using the "Load demo dossier" button.
- You can test the Safety Gate regex blocklist without external API calls.

---

## Running the Project Locally

### Interactive Web Workspace
```bash
python -m src.main --web
```
Open **http://127.0.0.1:8000** in your browser. You can click "Load demo dossier" to populate the full workspace immediately.

### Instant CLI Demo
```bash
python -m src.main --demo
```
Renders a colorized terminal dossier using Rich, showing the verdict stamp, dimension meters, epistemic breakdown, and executive summary.

### Live Governed Investigation
Requires a configured `.env` file with Gemini or Bedrock:
```bash
python -m src.main "An AI-powered automated inventory auditor for independent restaurants"
```

### Machine-Readable JSON Output
```bash
python -m src.main --demo --json
python -m src.main --demo --output report.json
```

---

## Testing Guide

### Running the Test Suite

We use `pytest`. All tests are self-contained and mock external LLM and network interactions:

```bash
# Run all tests
python -m pytest

# Run with verbose output and test names
python -m pytest -v

# Run a specific test module
python -m pytest test/test_governance.py
python -m pytest test/test_loop.py

# Run a single test function
python -m pytest test/test_verdict.py -k test_deterministic_kill_weak_problem
```

### Writing New Tests

When adding a feature or bug fix:
1. Place tests in the `test/` directory matching the module name (e.g. `test/test_governance.py`).
2. Utilize shared fixtures from [`test/conftest.py`](test/conftest.py):
   - `sample_state`: A pre-populated `DiligenceState` object.
   - `sample_investigation_dict`: Raw dictionary data for integration testing.
3. **Important:** Never make live HTTP or LLM calls in unit tests. Mock external calls or use offline data structures.

---

## Coding Standards & Invariants

### 1. Windows Console Safety (CP1252 / ASCII Encoding)

A common issue in Python command-line tools is using fancy Unicode characters (such as box-drawing characters `─`, `┌`, `└` or emojis `🛡️`, `✅`, `❌`) directly in `print()` statements. On standard Windows Command Prompt or PowerShell, the default encoding is often `cp1252`, which raises `UnicodeEncodeError`.

**Rule:** Always use ASCII fallback strings in CLI output and logs:
- Use `[SAFETY GATE]`, not `🛡️`
- Use `[ACCEPTED]`, `[REJECTED]`, not `✅`, `❌`
- Use `---`, `===`, or `***`, not `───` or `┌───`
- Use `>`, `*`, or `-`, not `•` or `└`

Rich panels handle terminal encoding cleanly, but raw strings printed to standard output or exceptions must remain ASCII-safe.

### 2. The 5 Governance Invariants

Never introduce code that bypasses the governance boundaries:
- **No Direct State Mutation:** Agents must never write directly to `DiligenceState`. They must submit candidate findings through `validate_and_merge()`, and unauthorized or unknown agents are rejected (fail-closed).
- **No Unsanitized Web Text:** Content fetched from DuckDuckGo or web scraping must be passed through `sanitize_web_content()` before entering prompt context.
- **Circuit Breaker Enforcement:** The Python control loop must call `BudgetGovernor.begin_iteration(agent_name)` before dispatching any specialist, and tools must call `BudgetGovernor.try_consume_tool(agent_name)` to enforce iteration, tool-call, and time limits.
- **Pre-Flight Safety Gate:** The entry point in `orchestrator.py` must run `evaluate_scope_and_safety()` before instantiating specialist agents. The gate fails closed if the classifier errors.

### 3. Type Safety & Pydantic v2

- Use Python 3.12 type hints: `list[str]`, `dict[str, Any]`, `str | None`.
- Use Pydantic v2 idioms: `model_dump()`, `model_validate()`, `Field(description=...)`.
- Keep data models in `src/models.py` strictly validated with defaults where appropriate.

### 4. Agent & Tool Isolation

- Specialist agents should be created lazily inside their respective factories, not at Python module import time.
- Tools must be decorated with `@tool` from `strands_agents.tools` and include comprehensive docstrings describing inputs and return values for the LLM.

---

## Development & Git Workflow

### 1. Fork & Branch

1. Fork the repository to your GitHub account.
2. Clone your fork locally:
   ```bash
   git clone https://github.com/<your-username>/idea-diligence-agent.git
   cd idea-diligence-agent
   ```
3. Set up upstream tracking:
   ```bash
   git remote add upstream https://github.com/gokul2210krishnan/idea-diligence-agent.git
   ```
4. Create a descriptive feature branch from `main`:
   ```bash
   git checkout -b feat/add-compliance-agent
   # or
   git checkout -b fix/sanitizer-entity-decoding
   ```

### 2. Keep Commits Focused

- Make atomic, meaningful commits with concise messages:
  - `feat(governance): add regex check for system prompt extraction`
  - `fix(verdict): prevent divide-by-zero when evidence list is empty`
  - `docs(readme): clarify Bedrock IAM permissions`

### 3. Run Quality Checks

Before pushing, verify that all tests pass:
```bash
python -m pytest
```

### 4. Submit a Pull Request

1. Push your branch to your GitHub fork:
   ```bash
   git push origin feat/your-feature-name
   ```
2. Open a Pull Request against the `main` branch of `gokul2210krishnan/idea-diligence-agent`.
3. Fill out the pull request template:
   - What problem does this PR solve?
   - What changes were made?
   - How was this tested?
4. A maintainer will review your PR and provide constructive feedback.

---

## Ideas for Contributions (Good First Issues)

Looking for something to work on? Here are high-impact areas open for contribution:

1. **New Specialist Agents:**
   - **Regulatory & Compliance Agent:** Researches legal, privacy (GDPR/HIPAA), and licensing barriers for sensitive verticals (health, fintech, food).
   - **Technical Feasibility Agent:** Analyzes API dependencies, infrastructure costs, and technical barriers to entry.
2. **Alternative Search & Scraper Providers:**
   - Add Tavily, Serper, or SearXNG search providers to `src/tools.py` with fallback mechanisms.
3. **Advanced Contradiction Detection:**
   - Enhance `src/governance/state_updater.py` to flag contradictory claims (e.g. one agent claims market is $10M and another claims $10B).
4. **Report Export Capabilities:**
   - Add clean PDF export support or Notion workspace export to `src/report.py`.
5. **Web UI Enhancements:**
   - Add historical session comparison in the web UI.
   - Add interactive radar/spider charts for the three diligence dimensions.

---

## Getting Help & Maintainers

If you have questions, run into issues, or want to discuss a feature idea before writing code:

- **Open a GitHub Discussion / Issue:** [Issues Page](https://github.com/gokul2210krishnan/idea-diligence-agent/issues)
- **Project Maintainers:**
  - **Edmund Dogbe** ([@GeekKwame](https://github.com/GeekKwame))
  - **Gokul Krishnan** ([@gokul2210krishnan](https://github.com/gokul2210krishnan))

Thank you for contributing to make startup due diligence smarter, faster, and more rigorous!
