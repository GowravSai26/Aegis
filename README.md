# ⚔️ AEGIS — Autonomous Chargeback Defense System

> *Named after the aegis — the divine shield of Zeus and Athena in Greek mythology. Unbreakable. Carried into every battle.*

**Chargebacks cost merchants $125 billion annually. Responding to each one requires a paralegal-level understanding of card network rules, evidence law, and dispute strategy — taking hours per case. AEGIS replicates that entire defense workflow autonomously — classifying the dispute, gathering evidence, building a legal strategy, drafting a formal response, and reviewing it — producing a submission-ready `.docx` document with a **verdict (FIGHT / ACCEPT / ESCALATE), winability score, and full argument set** in about 10 seconds.**

[![CI](https://github.com/GowravSai26/Aegis/actions/workflows/ci.yml/badge.svg)](https://github.com/GowravSai26/Aegis/actions/workflows/ci.yml)
[![Live](https://img.shields.io/badge/Live-Demo-7C5CBF?style=flat)](https://aegis-zeta-ten.vercel.app)



## 🔴 Live Demo

**[aegis-zeta-ten.vercel.app](https://aegis-zeta-ten.vercel.app)** · API: [`aegis-api-qs66.onrender.com`](https://aegis-api-qs66.onrender.com/health)

> Hosted on free tiers (Vercel + Render). The API sleeps after 15 minutes idle, so the first request can take up to ~1 minute while it wakes up — the page shows a status message while it does.

---

## The Problem

When a customer files a chargeback, the merchant has 7–30 days to respond with a legally structured dispute package. That package must:

- Correctly identify the chargeback reason code and its burden of proof
- Pull together delivery records, device fingerprints, auth history, and cardholder communications
- Build a winning legal argument based on card network rules
- Draft a formal response document meeting network submission standards
- Pass internal quality review before submission

Most merchants lose by default — not because they have a bad case, but because they don't have the people or process to respond in time. AEGIS solves it.

---

## What AEGIS Does

A dispute is submitted via REST API. Five specialized agents process it in sequence:

```
Intake → Evidence Collector → Strategy → Writer → Reviewer
```

| Agent | Role |
|---|---|
| **Intake** | Classifies dispute category and urgency from Visa reason code + rules engine |
| **Evidence Collector** | Gathers order details, delivery proof, device fingerprint, auth history, cardholder comms |
| **Strategy** | Decides FIGHT / ACCEPT / ESCALATE with a 0–1 winability score and argument set |
| **Writer** | Drafts a formal, submission-ready dispute response document |
| **Reviewer** | Reviews the draft for completeness and triggers a revision loop if needed |

The Reviewer → Writer loop runs until the response passes review; after three rejected drafts the case is escalated to a human — the same way a paralegal would iterate on a draft. ACCEPT and ESCALATE verdicts skip the writer entirely.

---

## Evaluation Results

15 scenarios across all 8 supported reason codes, run against the **live API** (Render free tier, Groq `openai/gpt-oss-120b`) on 2026-11-14. Raw output: [`tests/evals/eval_results.json`](tests/evals/eval_results.json).

```
EVAL-001  13.1  $250   expected=FIGHT     got=FIGHT     win=0.92   7.8s
EVAL-002  13.1  $450   expected=FIGHT     got=FIGHT     win=0.92   6.7s
EVAL-003  13.3  $99    expected=ANY       got=ACCEPT    win=0.22   3.2s
EVAL-004  10.4  $175   expected=FIGHT     got=FIGHT     win=0.78   6.5s
EVAL-005  13.1  $320   expected=FIGHT     got=FIGHT     win=0.92  12.7s
EVAL-006  10.4  $540   expected=FIGHT     got=FIGHT     win=0.78  21.4s
EVAL-007  12.6  $89    expected=FIGHT     got=FIGHT     win=0.66  21.4s
EVAL-008  13.7  $1200  expected=ANY       got=FIGHT     win=0.71  13.4s
EVAL-009  13.2  $850   expected=ANY       got=ACCEPT    win=0.22   3.5s
EVAL-010  13.6  $2200  expected=ANY       got=ACCEPT    win=0.35   3.1s
EVAL-011  10.5  $5000  expected=ESCALATE  got=ESCALATE  win=0.45   4.2s
EVAL-012  10.4  $7500  expected=ANY       got=FIGHT     win=0.73   9.3s
EVAL-013  13.3  $130   expected=ANY       got=ACCEPT    win=0.27   4.6s
EVAL-014  13.1  $420   expected=FIGHT     got=FIGHT     win=0.86   7.1s
EVAL-015  10.4  $670   expected=FIGHT     got=FIGHT     win=0.78  10.2s

15/15 passed · median 7.1s · slowest 21.4s
```

**What this does and doesn't show:** 9 scenarios have an expected verdict (8 FIGHT, 1 ESCALATE) and all 9 matched. The other 6 are marked `ANY` and only check that the pipeline returns a valid verdict without errors. Because the evidence tools return fixed sample data (see [Limitations](#limitations)), the verdicts mostly reflect the reason code and amount, not real case evidence. Latency includes Groq free-tier rate limiting; run with `EVAL_PAUSE_S=20` to stay under it.

---

## Architecture

```text
┌──────────────────────────────────────────────────────────────┐
│                        CLIENT / API                          │
│              POST /dispute  {chargeback payload}             │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                   FastAPI (api/main.py)                      │
│              Pydantic schema validation                      │
│      Route runs the graph, then writes the .docx             │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│        LangGraph Orchestrator (agents/orchestrator.py)       │
│                                                              │
│  [START]                                                     │
│     → intake_agent                                           │
│     → evidence_collector_agent                               │
│     → strategy_agent                                         │
│     → writer_agent  ←───────────────────────────┐            │
│     → reviewer_agent                            │            │
│          │ review_passed?                       │            │
│          ├── YES → END                          │            │
│          ├── NO, < 3 drafts → (revision) ───────┘            │
│          └── NO, 3 drafts   → escalate → END                 │
│                                                              │
└──────────────────────────────┬───────────────────────────────┘
                               │
        ┌──────────────────────┴──────────────────────┐
        │                                             │
┌───────▼──────────────┐              ┌───────────────▼──────────┐
│  Reason Code         │              │        Groq LLM          │
│  Rules Engine        │              │  (openai/gpt-oss-120b)   │
│  data/               │              │    Agent reasoning       │
│  reason_codes.json   │              │    + JSON output         │
└──────────────────────┘              └──────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│              document_generator (tools/)                     │
│         Produces formatted .docx → generated_docs/           │
└──────────────────────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                       LangSmith                              │
│   Full trace of every agent run — LLM calls, tool results,   │
│   revision loops, token usage, latency per step              │
└──────────────────────────────────────────────────────────────┘
```

---

## API Reference

### `POST /dispute`

Submit a chargeback for autonomous defense analysis.

**Request:**
```json
{
  "chargeback_id": "CB-001",
  "merchant_id": "MERCH-001",
  "transaction_id": "TXN-456",
  "amount": 450.00,
  "reason_code": "13.1",
  "reason_description": "Item not received"
}
```

**Response:**
```json
{
  "chargeback_id": "CB-001",
  "verdict": "FIGHT",
  "winability_score": 0.85,
  "strategy_reasoning": "Strong delivery confirmation with carrier scan and customer signature. Evidence package supports a high-confidence defense.",
  "recommended_arguments": [
    "Delivery confirmation and customer signature prove merchandise was received.",
    "Order details provide a clear record of the transaction and fulfillment.",
    "Customer accepted terms and conditions at time of purchase."
  ],
  "review_passed": true,
  "dispute_category": "not_received",
  "urgency": "HIGH",
  "agent_trace": [
    "IntakeAgent: classified as not_received | urgency=HIGH",
    "EvidenceCollector: strength=0.85 | missing=[]",
    "StrategyAgent: verdict=DisputeVerdict.FIGHT | winability=0.85",
    "WriterAgent: drafted response (revision 0)",
    "ReviewerAgent: passed=True | feedback=''"
  ],
  "document_path": "generated_docs/CB-001.docx",
  "escalation_reason": null
}
```

### `GET /dispute/{chargeback_id}/download`

Download the generated `.docx` dispute response — ready for card network submission.

### `GET /health`

Health check.

---

## Supported Reason Codes

| Code | Description | Default Strategy |
|---|---|---|
| 13.1 | Merchandise Not Received | FIGHT with delivery proof |
| 13.3 | Not as Described | FIGHT with product evidence |
| 13.7 | Cancelled Merchandise | ACCEPT unless policy violation |
| 13.2 | Cancelled Recurring | ACCEPT unless prior notice given |
| 13.6 | Credit Not Processed | FIGHT with refund records |
| 10.4 | Fraudulent Transaction | FIGHT with auth + device data |
| 10.5 | Visa Fraud Monitoring | ESCALATE — legal review required |
| 12.6 | Duplicate Processing | FIGHT with transaction records |

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Agent framework | LangGraph | Explicit state machine — inspectable, debuggable, revision loops |
| LLM | Groq (`openai/gpt-oss-120b`, set via `GROQ_MODEL`) | Fast inference, reliable JSON output |
| Backend | FastAPI + Pydantic v2 | Fully typed, async, automatic OpenAPI docs |
| Document generation | python-docx | Submission-ready `.docx` output |
| Rules engine | JSON reason code rules | Deterministic guardrail on top of LLM reasoning |
| Observability | LangSmith (optional, off on the live demo) | Full agent trace per dispute |
| Containerization | Docker + docker-compose | One-command local setup |
| Deployment | Render (API, free web service via `render.yaml`) + Vercel (frontend) | Free hosting |
| CI/CD | GitHub Actions | Lint → test → build on every push; deploy on `main` |
| Code quality | ruff | Zero lint warnings enforced |

---

## Running Locally

```bash
# 1. Clone
git clone https://github.com/GowravSai26/Aegis
cd Aegis

# 2. Set environment variables
cp .env.example .env
# Add GROQ_API_KEY (LANGCHAIN_API_KEY is optional, for tracing)

# 3. Start the API
docker compose up --build

# 4. Test it
curl -X POST http://localhost:8000/dispute \
  -H "Content-Type: application/json" \
  -d '{
    "chargeback_id": "CB-001",
    "merchant_id": "MERCH-001",
    "transaction_id": "TXN-456",
    "amount": 450.00,
    "reason_code": "13.1",
    "reason_description": "Item not received"
  }'
```

---

## Running Tests

```bash
# Unit tests — LLM calls are mocked, no API key needed
pytest tests/unit/ -v

# Eval harness — needs a running API (localhost:8000 by default)
python tests/evals/eval_scenarios.py
AEGIS_API_URL=https://aegis-api-qs66.onrender.com EVAL_PAUSE_S=20 python tests/evals/eval_scenarios.py
```

---

## Project Structure

```
aegis/
├── agents/
│   ├── state.py                     # AegisState TypedDict + DisputeVerdict enum
│   ├── orchestrator.py              # LangGraph StateGraph — all 5 agents + edges
│   ├── intake_agent.py              # Dispute classification + urgency
│   ├── evidence_collector_agent.py  # Evidence gathering across 5 tools
│   ├── strategy_agent.py            # FIGHT / ACCEPT / ESCALATE + winability
│   ├── writer_agent.py              # Formal dispute response drafting
│   └── reviewer_agent.py            # Quality review + revision loop
├── api/
│   ├── main.py                      # FastAPI app + CORS
│   ├── schemas.py                   # Pydantic request/response models
│   └── routes/
│       ├── disputes.py              # POST /dispute + GET /dispute/{id}/download
│       └── health.py                # GET /health
├── tools/
│   ├── reason_code_rules.py         # Visa reason code rules engine
│   ├── document_generator.py        # .docx generation
│   └── evidence tools               # order_lookup, delivery_proof, device_fingerprint,
│                                    # auth_history, cardholder_comms
├── data/
│   └── reason_codes.json            # 8 Visa reason codes with evidence requirements
├── tests/
│   ├── unit/                        # Mocked unit tests: each agent + the full graph (8 tests)
│   └── evals/                       # 15-scenario end-to-end eval harness
├── frontend/index.html              # Single-page UI (deployed on Vercel)
├── generated_docs/                  # Output .docx files
├── Dockerfile
├── docker-compose.yml
├── render.yaml                      # Render Blueprint (free web service)
└── .github/workflows/ci.yml
```

---

## CI/CD

Every push to `main` triggers:

1. **Ruff** — lint + format check
2. **pytest** — 8 unit tests (all 5 agents + the revision loop)
3. **Docker build** — confirms image builds cleanly
4. **Deploy** — on `main`, calls Render's deploy hook (`RENDER_DEPLOY_HOOK` secret) to redeploy the API

Vercel redeploys the frontend on every push to `main`.

---

## Limitations

This is a portfolio project, not a production system. Known gaps:

- **Evidence is sample data.** The five evidence tools in `tools/` return fixed, strong-looking records (delivered, signed, 3-DS authenticated) for every transaction instead of querying a real order, carrier or payment system. The pipeline and prompts are real; the inputs are not.
- **No persistence.** Disputes aren't stored. Generated `.docx` files live on the server's disk, which Render wipes on every restart or redeploy, so download a document right after generating it.
- **No authentication or rate limiting** on the API; anyone with the URL can run disputes against the Groq quota.
- **LLM output isn't guaranteed.** Agents parse JSON from the model; on a parse error they fall back to safe defaults (e.g. strategy → ESCALATE) rather than failing.
- **Reason-code rules cover 8 Visa codes** only; other networks (Mastercard, RuPay) aren't modeled.
- **Free hosting:** cold starts take up to ~1 minute, and Groq's free tier rate-limits back-to-back requests.

---

## Environment Variables

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Groq API key for LLM inference |
| `GROQ_MODEL` | Groq model id (default `openai/gpt-oss-120b`) |
| `CORS_ORIGINS` | Comma-separated browser origins allowed to call the API (default: the Vercel frontend) |
| `LANGCHAIN_API_KEY` | LangSmith API key for tracing (optional) |
| `LANGCHAIN_TRACING_V2` | Enable LangSmith tracing (`true` / `false`) |
| `LANGCHAIN_PROJECT` | LangSmith project name |

---

## The Name — AEGIS

In Greek mythology, the **aegis** (αἰγίς) was the divine shield — carried by Zeus and Athena into battle. It was said to be so powerful that merely displaying it would strike fear into enemies and protect those behind it.

Merchants face $125 billion in annual chargeback losses — attacked by fraudulent claims, exploited by policy abuse, and lost by default due to lack of resources. AEGIS is that shield. Autonomous. Unbreakable. Always ready.

---

## Author

**Gowrav Sai Veeramallu**  
Agentic AI Engineer · Gen AI

[LinkedIn](https://www.linkedin.com/in/Gowrav-Sai-Veeramallu) · [GitHub](https://github.com/GowravSai26)
