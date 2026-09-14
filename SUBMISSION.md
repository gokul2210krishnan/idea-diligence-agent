# Devpost Submission — Idea Diligence Agent

**Hackathon:** AWS Strands Agents SDK Hackathon  
**Track:** Professional Agents  
**Team:** Edmund & Gokul

---

## Tagline

An autonomous multi-agent system that researches a raw product idea and returns an evidence-backed **GO**, **MODIFY**, or **KILL** verdict — without babysitting the founder.

## Inspiration

Founders waste days Googling competitors and talking themselves into ideas that the market already killed. We wanted an agent that does the opposite of a cheerleader: it investigates the problem, the competitive set, and the economics, then makes a decision a skeptical partner would make.

The AWS Strands Agents SDK let us treat specialist researchers as tools and keep a single orchestrator in charge. Phase 2 added the governance layer so the system cannot be jailbroken, cannot loop forever, and cannot treat scraped web pages as instructions. Phase 3 and 4 turn that research into a verdict a judge (or a founder) can actually use.

## What it does

You submit a product idea in plain English. The system:

1. Screens the idea at a **Safety & Scope Gate** (jailbreaks and off-topic requests never reach the researchers).
2. Runs an **adaptive investigation** with three Strands specialist agents — Problem, Competition, and Economics — under a hard **budget governor**.
3. Isolates every web page inside `<untrusted_external_evidence>` tags so third-party sites cannot inject instructions.
4. Accepts findings only through a **propose → validate → merge** state layer. FACTs without sources are rejected or downgraded.
5. Classifies remaining evidence, scores problem / competition / economics, and renders **GO / MODIFY / KILL** with confidence, unknowns, risks, and next steps.
6. Delivers a professional diligence report in the CLI, as JSON, or in a local web UI.

The user does not steer the research. Submit an idea → get a dossier.

## How we built it

- **Strands Agents SDK** with a Python-owned dispatch loop. Specialists (`problem_agent`, `competition_agent`, `economics_agent`) research; the budget governor decides whether they run.
- **Configurable model provider** (Amazon Bedrock or Gemini) so the same architecture runs on AWS or a zero-wait local key.
- **Pydantic v2** `DiligenceState` as the single source of truth per session.
- **Five defense boundaries:** safety gate, budget governor, untrusted-web envelope, state authority layer, decision-impact unknown triage.
- **Verdict engine:** deterministic scoring first, optional LLM prose second. The model cannot override a KILL that the evidence already supports.
- **Demo surfaces:** rich CLI (`python -m src.main`) and FastAPI UI (`python -m src.main --web`), plus a canned `--demo` dossier for walkthroughs that cannot wait on live research.

## Challenges we ran into

- Specialist agents over-label findings as FACT. We added a second-pass classifier that downgrades unsourced or hedged claims.
- A free-text orchestrator verdict is not a product. The synthesis engine had to produce a structured `VerdictReport` even when the LLM rambles.
- Live investigations take minutes. The demo UI therefore has a one-click canned dossier so judges can see the full report immediately, then optionally run a live idea.

## Accomplishments that we're proud of

- A complete governed multi-agent loop, not a single prompt wrapper.
- Evidence that carries type, source, confidence, and category into the final report.
- A verdict the system is allowed to say **KILL**.
- A test suite covering governance, classification, verdict rules, report rendering, CLI, and the web API — without requiring live model credentials.

## What we learned

Professional agents are less about clever prompts and more about **authority**: who may write state, what counts as a fact, when research must stop, and how a decision is justified. Strands made the specialist split natural; Python governance made it safe.

## What's next

- Optional AWS AgentCore deploy for a hosted demo.
- Stronger contradiction detection across evidence.
- Batch mode: drop in ten ideas, get ten dossiers.

## Built with

Python, Strands Agents SDK, Pydantic, Amazon Bedrock / Gemini, DuckDuckGo search, FastAPI, Rich, pytest.

## How to try it

```bash
pip install -r requirements.txt
# add .env with Gemini or Bedrock credentials for live runs

python -m src.main --demo
python -m src.main --web
python -m pytest
```
