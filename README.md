# Idea Diligence Agent

> An autonomous AI agent that takes a raw product idea, researches competitors, markets, pricing, and revenue in the background, challenges your assumptions, and delivers an evidence-backed **GO**, **MODIFY**, or **KILL** verdict.

**Hackathon:** AWS Strands Agents SDK Hackathon  
**Track:** Professional Agents  
**Deadline:** Sep 15, 2026 @ 1:00am GMT+1  
**Team:** Edmund & Gokul

---

## What It Does

You give the agent a product idea in plain English. It:

1. **Researches the problem** — who has it, how painful it is, how they currently cope
2. **Finds competitors** — direct competitors, indirect alternatives, their pricing, their weaknesses
3. **Evaluates the economics** — can it make money? what should it charge? how big is the market?
4. **Challenges assumptions** — it doesn't just agree with you; if the idea has a fatal flaw, it says so
5. **Delivers a verdict** — **GO** (build it), **MODIFY** (pivot this specific thing), or **KILL** (don't waste your time)

The user does nothing during the investigation. Submit an idea → get a verdict. Zero babysitting.

---

## Architecture Overview

```
User submits idea
        │
        ▼
┌──────────────────────┐
│ Safety & Scope Gate  │  ← Boundary 1: Rejects adversarial prompts & out-of-scope ideas
└──────────┬───────────┘
           │ ACCEPT
           ▼
┌──────────────────────┐
│   DiligenceState     │  ← Canonical state for the session
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│    Orchestrator      │  ← Controlled by Hard Runtime & Budget Governor (Boundary 2)
└──────────┬───────────┘     Triage unknowns by decision impact (Boundary 5)
           │
     ┌─────┴─────┐  ┌───────────┐  ┌───────────────┐
     │  Problem  │  │Competition│  │  Economics     │
     │   Agent   │  │   Agent   │  │    Agent       │
     └─────┬─────┘  └─────┬─────┘  └──────┬────────┘
           │              │               │
           └──────────────┼───────────────┘
                          │ Calls tools (Web search / Scraper)
                          ▼
            [Untrusted Web Content Boundary]  ← Boundary 3: Envelopes external text as inert XML
                          │
                          ▼
             Candidate Finding Proposals
                          │
                          ▼
            [State Authority & Update Layer]  ← Boundary 4: Validate Schema ➔ Policy ➔ Merge
                          │
                          ▼
                Update DiligenceState
                          │
                          ▼
                 Enough evidence?
                    ╱          ╲
                  NO           YES
                   │             │
            Loop back to      Render
            Orchestrator      Verdict
```

### Key Design & Governance Invariants

- **Adaptive loop, not a fixed pipeline.** The orchestrator decides what to research next based on what's currently unknown — not a rigid sequential chain.
- **Canonical DiligenceState & Session Isolation.** Single source of truth per investigation. No state leakage between sessions.
- **Evidence classification.** Every finding is classified as `FACT`, `ASSUMPTION`, `INFERENCE`, or `UNKNOWN`, preserving provenance and source URLs.
- **5 Defense-in-Depth Boundaries (Phase 2):**
  1. **Safety & Scope Gate:** Pre-flight screen rejects jailbreaks, malicious prompts, and off-topic requests before agent invocation.
  2. **Hard Runtime Budget Governor:** Deterministic limits in Python (`MAX_ITERATIONS = 5`, `MAX_TOOL_CALLS = 25`, `MAX_WALLCLOCK_SECONDS = 180s`) prevent runaway loops and cloud bill spikes.
  3. **Untrusted Web Content Boundary:** Web scrape content is quarantined in `<untrusted_external_evidence>` XML tags so third-party sites cannot perform indirect prompt injections.
  4. **Restricted Authority (Propose-Validate-Merge):** Specialist agents propose candidate findings; a deterministic Python layer validates schema, checks domain authorization, and verifies provenance before merging into state.
  5. **Decision-Impact Unknown Triage:** Unknowns are prioritized by decision impact (`CRITICAL` vs `LOW`), ensuring research targets thesis dealbreakers rather than trivia.

---

## Tech Stack

| Component | Technology | Why |
|---|---|---|
| Agent framework | **Strands Agents SDK** (Python) | Required by hackathon. We use the "agents-as-tools" pattern. |
| Foundation model | **Configurable model provider** — Amazon Bedrock / Gemini | Provider and model selection are configurable through environment variables, while keeping the Strands agent architecture unchanged. |
| Data models | **Pydantic v2** | Type-safe, validated, serializable state. |
| Web research | **DuckDuckGo** (via `http_request`) | Free, no API key, works immediately. |
| Interface | **Rich CLI + local web UI** | `python -m src.main` for the terminal dossier; `python -m src.main --web` for the demo UI. |

---

## Project Structure

```
idea-diligence-agent/
├── requirements.txt              # Python dependencies
├── CHANGELOG.md                  # Phase progress tracking
├── SUBMISSION.md                 # Devpost submission copy
├── DEMO.md                       # 5-minute hackathon video script
├── pytest.ini                    # Test discovery
├── examples/
│   └── sample_investigation.json # Canned demo dossier
├── brainstorming/                # Project design & discussion documents
├── scripts/                      # Utility and document generation scripts
├── test/                         # Governance, verdict, report, CLI, and UI tests
├── src/
│   ├── main.py                   # CLI + --web / --demo / --json entry point
│   ├── models.py                 # DiligenceState + verdict models
│   ├── evidence.py               # FACT/ASSUMPTION/INFERENCE/UNKNOWN classifier
│   ├── verdict.py                # GO / MODIFY / KILL synthesis engine
│   ├── report.py                 # Markdown, JSON, and rich terminal reports
│   ├── demo_data.py              # Loader for the canned investigation
│   ├── model_provider.py         # Bedrock / Gemini configuration
│   ├── prompts.py                # Specialist, orchestrator, and verdict prompts
│   ├── tools.py                  # search_web, read_webpage, save_finding
│   ├── governance/               # Safety gate, budget, sanitizer, state updater
│   ├── agents/                   # Orchestrator + three specialists
│   └── web/                      # FastAPI demo UI
└── LICENSE                       # Apache 2.0
```

---

## Phase 1 Status: ✅ COMPLETE — Walking Skeleton

> **Goal:** Get the full project structure built end-to-end with all agents wired up, all imports verified, and a configurable model provider path working. Prove the SDK and research flow work before adding complexity.

### What Was Built

#### 1. Model Provider Abstraction ([`src/model_provider.py`](src/model_provider.py))

Model configuration is centralized so agents do not need to hard-code a specific foundation-model provider.

- Supports **Amazon Bedrock** and **Gemini** model providers.
- Provider/model selection is controlled through environment variables.
- Supports role-specific model configuration for `PROBLEM`, `COMPETITION`, `ECONOMICS`, and `ORCHESTRATOR`.
- Falls back to `DEFAULT_MODEL_PROVIDER` / `DEFAULT_MODEL_ID` when a role-specific configuration is not provided.
- Keeps provider-specific construction isolated from the specialist agents and orchestrator.

#### 2. Data Models ([`src/models.py`](src/models.py))

The `DiligenceState` — our canonical research state (Gokul's core architecture recommendation). Contains:

| Model | Purpose |
|---|---|
| `DiligenceState` | Top-level state: holds the idea, all findings, audit trail, and final verdict |
| `Evidence` | A single finding tagged with `EvidenceType` (FACT / ASSUMPTION / INFERENCE / UNKNOWN) |
| `CustomerSegment` | A target persona with pain points and size estimate |
| `Competitor` | A competing product with pricing, strengths, weaknesses, URL |
| `BusinessModel` | A revenue model option (subscription, freemium, etc.) with reasoning |
| `ProblemAnalysis` | Problem statement, severity, existing workarounds, demand signals |
| `EconomicAnalysis` | Market size, revenue potential, unit economics |
| `VerdictReport` | Final GO/MODIFY/KILL decision with confidence, evidence, unknowns, assumptions |
| `ResearchAction` | Audit trail entry: which agent did what and when |

Helper methods on `DiligenceState`:
- `is_research_complete()` — check if a verdict has been rendered
- `has_budget_remaining()` — check if we're under the 5-cycle safety limit
- `get_critical_unknowns()` — collect all UNKNOWN evidence for the orchestrator
- `add_evidence()` / `log_action()` — structured helpers for agents to update state

#### 3. Custom Research Tools ([`src/tools.py`](src/tools.py))

Three `@tool`-decorated functions that the specialist agents call during research:

| Tool | What It Does |
|---|---|
| `search_web(query)` | Searches DuckDuckGo for competitors, pricing, market data. No API key needed. |
| `read_webpage(url)` | Fetches and extracts text from a URL. Truncates to 15K chars to stay within context limits. |
| `save_finding(category, content, evidence_type, source, confidence)` | Records a structured finding tagged as FACT/ASSUMPTION/INFERENCE/UNKNOWN with a source URL and confidence score (0.0–1.0). Returns JSON for the orchestrator to collect. |

#### 4. Agent System Prompts ([`src/prompts.py`](src/prompts.py))

Each agent has a detailed system prompt telling it exactly what to research and how to report findings:

| Prompt | Key Instructions |
|---|---|
| `PROBLEM_AGENT_PROMPT` | Research the problem, identify specific customer segments (not "small businesses" — "independent restaurants with 1-3 locations"), assess severity, find demand signals. Mark everything with evidence types. |
| `COMPETITION_AGENT_PROMPT` | Search for "[category] software", visit pricing pages, check G2/Capterra/Reddit reviews. Finding many competitors validates the market. Pay attention to pricing ranges. |
| `ECONOMICS_AGENT_PROMPT` | Be realistic, not optimistic. Base pricing on competitor data, not wishful thinking. "The market is huge" is useless; "$4.2B TAM based on [source]" is useful. |
| `ORCHESTRATOR_PROMPT` | Coordinate all three agents, synthesize findings, render a verdict. Be honest — don't default to GO because the user wants to hear it. |

#### 5. Specialist Agents ([`src/agents/`](src/agents/))

Three agent factory functions, each returning a configured `strands.Agent`:

| File | Agent | Model | Tools |
|---|---|---|---|
| `problem_agent.py` | Problem Analysis | Claude Sonnet 4 (Bedrock, us-east-1) | `search_web`, `read_webpage`, `save_finding` |
| `competition_agent.py` | Competition Analysis | Claude Sonnet 4 (Bedrock, us-east-1) | `search_web`, `read_webpage`, `save_finding` |
| `economics_agent.py` | Economics Analysis | Claude Sonnet 4 (Bedrock, us-east-1) | `search_web`, `read_webpage`, `save_finding` |

#### 6. Orchestrator ([`src/agents/orchestrator.py`](src/agents/orchestrator.py))

Uses the **agents-as-tools** pattern from Strands SDK:
- Each specialist agent is wrapped in a `@tool` function (`problem_agent`, `competition_agent`, `economics_agent`)
- The orchestrator LLM calls these tools to dispatch research tasks
- `run_diligence(idea: str) -> str` is the main entry point — give it an idea, get a verdict

#### 7. CLI Entry Point ([`src/main.py`](src/main.py))

```bash
# Pass idea as argument
python -m src.main "An app that helps small restaurants track food inventory"

# Or interactive mode (prompts for input)
python -m src.main
```

### What Was Verified

| Check | Status |
|---|---|
| Pydantic models import and instantiate correctly | ✅ |
| `EvidenceType` and `Verdict` enums work | ✅ |
| Strands SDK `Agent` and `@tool` imports work | ✅ |
| Model-provider abstraction imports and initializes correctly | ✅ |
| Amazon Bedrock model path remains supported | ✅ |
| Gemini model-provider path works with environment configuration | ✅ |
| `strands_tools.http_request` import works | ✅ |
| Custom tools (`search_web`, `read_webpage`, `save_finding`) import | ✅ |
| System prompts import | ✅ |
| Orchestrator creation chain imports | ✅ |
| End-to-end Phase 1 investigation runs successfully | ✅ |
| All dependencies installed (`strands-agents`, `strands-agents-tools`, `pydantic`, `python-dotenv`) | ✅ |

### What Was NOT Done Yet (Phase 2+)

These gaps were closed in later phases. Phase 2 wired governance and `DiligenceState`. Phase 3 added the verdict engine and professional report. Phase 4 added the demo UI and submission pack.

---

## Phase 2 Status: ✅ COMPLETE — Governed Multi-Agent Loop

Defense-in-depth is implemented in `src/governance/`: safety gate, budget governor, untrusted-web sanitizer, propose-validate-merge state updater, and decision-impact unknowns. The orchestrator runs an adaptive investigation and merges specialist findings into `DiligenceState`.

---

## Phase 3 Status: ✅ COMPLETE — Verdict & Polish

### Verdict synthesis engine ([`src/verdict.py`](src/verdict.py))

After research, the engine:

1. Reclassifies every finding ([`src/evidence.py`](src/evidence.py)) — unsourced FACTs are downgraded, hedging language cannot stay a FACT, confidence is recalibrated.
2. Scores three dimensions: **problem**, **competition**, **economics**.
3. Applies deterministic rules: weak problem or unviable economics → **KILL**; strong scores, sourced facts, no critical unknowns → **GO**; otherwise **MODIFY** with concrete changes.
4. Optionally blends orchestrator/LLM prose when it **agrees** with the scored decision. The model cannot override a KILL the evidence already supports.

The output is a `VerdictReport`: decision, confidence, summary, key evidence, modifications, unknowns, assumptions, risks, next steps, and evidence mix.

### Professional report ([`src/report.py`](src/report.py))

The same investigation renders as:

- Markdown dossier (CLI default / `--output report.md`)
- JSON (`--json` or `--output report.json`)
- Colorized terminal panel via Rich

### Demo surfaces

```bash
python -m src.main --demo                  # canned restaurant-inventory dossier, no LLM
python -m src.main --json --demo           # machine-readable
python -m src.main --web                   # local UI at http://127.0.0.1:8000
python -m src.main "Your product idea"     # live governed investigation
```

The web UI (`src/web/`) shows the verdict stamp, dimension bars, evidence ledger, governance chips, and the full markdown report. **Load demo dossier** is instant; **Run live investigation** calls the real pipeline.

---

## Phase 4 Status: ✅ COMPLETE — Demo & Submission Pack

| Deliverable | Location |
|---|---|
| Devpost submission copy | [`SUBMISSION.md`](SUBMISSION.md) |
| 5-minute video script | [`DEMO.md`](DEMO.md) |
| Canned walkthrough data | [`examples/sample_investigation.json`](examples/sample_investigation.json) |
| Automated tests | `test/` — run with `python -m pytest` |

Recording the Devpost video and posting to builder.aws.com are operator steps (see `DEMO.md`). Optional AWS AgentCore hosting is not part of this branch.

---

## What's Next (post-hackathon)

- Hosted demo on AWS AgentCore
- Stronger cross-finding contradiction detection
- Batch mode: many ideas → many dossiers

---

## How to Run

### Prerequisites

- Python 3.12+
- Credentials for the model provider you choose:
  - **Amazon Bedrock**, or
  - **Gemini API**

### Setup

**1. Install Python dependencies:**

```bash
pip install -r requirements.txt
```

**2. Configure the model provider:**

Create a `.env` file in the project root.

**Gemini example:**

```env
DEFAULT_MODEL_PROVIDER=gemini
DEFAULT_MODEL_ID=<your-gemini-model-id>
GEMINI_API_KEY=<your-gemini-api-key>
```

**Amazon Bedrock example:**

```env
DEFAULT_MODEL_PROVIDER=bedrock
DEFAULT_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0
AWS_REGION=us-east-1
```

For Bedrock, configure AWS credentials using your normal AWS credential chain (for example `aws configure`) and make sure the IAM user/role has permission to invoke the selected Bedrock model.

> `.env` is loaded automatically by the application for local development. Do not commit API keys or AWS secrets to source control.

**3. Run:**

```bash
# Live investigation (needs model credentials)
python -m src.main "An app that helps small restaurants track food inventory to reduce waste"

# Instant demo dossier (no model calls)
python -m src.main --demo

# Local web UI
python -m src.main --web
```

The same CLI entry point works with either configured provider. Provider/model selection is handled by `src/model_provider.py` rather than being hard-coded inside individual agents.

**4. Test:**

```bash
pip install -r requirements.txt
python -m pytest
```

Tests cover the safety gate, budget governor, sanitizer, state updater, evidence classifier, verdict rules, report renderer, CLI, and web API. They do not require API keys.

---

## License

Apache 2.0 — see [LICENSE](LICENSE)