# FaultSense: Autonomous Fault Isolation and Root Cause Analysis Assistant

[![GitHub Repository](https://img.shields.io/badge/GitHub-FaultSense-blue?logo=github)](https://github.com/nithiofficial07-coder/FaultSense)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.40+-FF4B4B.svg?logo=Streamlit)](https://streamlit.io/)
[![FAISS CPU](https://img.shields.io/badge/FAISS-CPU-green.svg)](https://github.com/facebookresearch/faiss)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests Passing](https://img.shields.io/badge/tests-145%20passed-brightgreen.svg)]()

> **Elevator Technician Decision-Support Application**  
> **Repository:** [https://github.com/nithiofficial07-coder/FaultSense](https://github.com/nithiofficial07-coder/FaultSense)  
> *Safety Notice*: FaultSense is an offline-first advisory and diagnostic support tool designed for certified vertical transportation technicians. It does **NOT** interface directly with elevator safety circuits, controllers, or operational relays. All safety-related work must adhere to ASME A17.1 / EN 81 safety codes, Lockout/Tagout (LOTO) protocols, and physical multimeter verification.

---

## Quickstart & Repository Clone

```bash
# Clone the repository
git clone https://github.com/nithiofficial07-coder/FaultSense.git
cd FaultSense

# Create and activate virtual environment
python -m venv .venv
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup environment variables (default offline demo mode)
cp .env.example .env

# Launch technician dashboard
streamlit run app.py
```

---

## 1. Project Overview & System Architecture

FaultSense accelerates elevator troubleshooting by analyzing operational symptoms, diagnostic trouble codes (DTC), and sensor telemetry against historical maintenance logs and OEM technical advisories. It features a hybrid lexical (SQLite FTS5) and dense semantic vector retrieval pipeline (FAISS-CPU) coupled with an **agentic self-verification loop** that audits generated root-cause claims against retrieved evidence, re-retrieves when evidence is missing, and halts with an explicit inconclusive advisory on out-of-distribution faults.

### End-to-End System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Streamlit Technician UI                         │
│   Overview | New Investigation | Diagnostic Results | Diagnostic Report│
│   Conversational Assistant | Knowledge Base | History | Settings       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               Phase 5 & 6: Diagnostic Reasoning Engine                 │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Prompt Builder (Epistemic rules, untrusted data isolation)       │  │
│  │ LLM Adapters (OpenAI, Google Gemini, Anthropic Claude, Mock)     │  │
│  │ Deterministic Offline Fallback Engine (No API key / Demo Mode)   │  │
│  └──────────────────────────────────┬───────────────────────────────┘  │
│                                     │                                  │
│                                     ▼                                  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │           Phase 6: Agentic Self-Verification Loop                │  │
│  │  - Independent Claim Auditor (Supported, Partial, Contradicted) │  │
│  │  - Query Refinement & Adaptive Top-K Expansion                   │  │
│  │  - Bounded Retries (MAX_RETRIES=2) with Anti-Cycling Guard       │  │
│  │  - Strict Rejection: Unsupported claims NEVER silently approved  │  │
│  │  - Zero-Hallucination Citation Guard (Permitted Case ID Filter)  │  │
│  └──────────────────────────────────┬───────────────────────────────┘  │
└───────────────────────────────────┬─┘──────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│             Phase 3 & 4: Hybrid Retrieval & Indexing Layer             │
│  - Dense Vector Index: FAISS IndexFlatIP (Cosine Similarity via L2)    │
│  - Embedding Model: sentence-transformers/all-MiniLM-L6-v2 (384-D)     │
│  - Singleton Embedding Model Cache (30-60 ms warm inference)           │
│  - Lexical Full-Text Search: SQLite FTS5 (BM25 token matching)         │
│  - Multi-Factor Sufficiency Evaluator (Noise Floor, Exact DTC Match)   │
│  - Subsystem Topology Graph & Candidate Cross-System Propagation       │
│  - Safe JSON Vector-to-Case Mapping (Pickle Strictly Prohibited)       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               Phase 1 & 2: Data Ingestion & Storage Layer              │
│  - Multi-Format Parser: CSV and JSON format validation                 │
│  - Provenance Enforcement: Verified OEM vs Synthetic Illustrative      │
│  - Deduplication: In-batch and cross-repository SHA-256 fingerprinting │
│  - Signal Preprocessor: NumPy & Pandas telemetry normalization         │
│  - SQLite Repositories: fault_cases (relational + FTS5)                │
│  - SQLite Audit Trail: investigations (audit logs & verification steps)│
│  - Publication PDF Engine: ReportLab 14-section ASME A17.1 report      │
└────────────────────────────────────────────────────────────────────────┘
```

### 4-Step Professional Field Workflow
FaultSense implements a structured end-to-end decision-support lifecycle:
1. **Step 1: Submit Problem (`New Investigation`)** — Capture equipment metadata, building series, observed symptoms, diagnostic trouble code (DTC), subsystem, and optional CSV/JSON telemetry uploads or manual sensor inputs with pre-submission validation.
2. **Step 2: Analyze & Verify Evidence (`Diagnostic Results`)** — Hybrid retrieval queries FAISS dense vectors and SQLite FTS5 lexical indices. The Agentic Self-Verification Loop audits candidate hypotheses, cross-checks electrical sensor telemetry, filters citations, and presents a 12-factor diagnostic dossier.
3. **Step 3: Generate Technical PDF Report (`Diagnostic Report`)** — Compiles the comprehensive 14-section publication-grade report with repeated table headers, two-pass `Page X of Y` numbering, color-coded severity callouts, and safety disclaimers adhering to ASME A17.1 elevator safety codes.
4. **Step 4: Download & Technician Review (`Review Sign-Off`)** — Direct one-click PDF and structured JSON download buttons. Includes an interactive Field Technician Review and Sign-Off block where technicians record their name, license ID, physical findings, and review status (`approved`, `inconclusive`, `escalated`), persisted directly into the SQLite audit table.

### ASME A17.1 Compliant 14-Section PDF Structure
The ReportLab PDF engine compiles an exhaustive 14-section diagnostic deliverable:
1. **Header Block & Document Metadata** (Document control, ISO 8601 timestamps, investigation ID).
2. **Executive Summary & Verification Status** (High-level findings and confidence score).
3. **Equipment & Site Information** (Elevator series, building ID, machine room, controller).
4. **Problem Description & Observed Symptoms** (Reported fault narrative and observed indicators).
5. **Operational Telemetry & Sensor Readings** (Tabular electrical and mechanical metrics with safety ranges).
6. **Subsystem Analysis & DTC Interpretation** (Coupling analysis and OEM trouble code definitions).
7. **Identified Candidate Causes & Ranking** (Confidence breakdown, ranking rationale, and risk tier).
8. **Primary Root Cause Hypothesis** (Deep engineering analysis of the primary failure mode).
9. **Evidence Grounding & Retrieved Reference Cases** (Historical OEM case citations with similarity scores).
10. **Agentic Self-Verification Audit Trail** (Iteration count, claim status, and telemetry verification).
11. **Step-by-Step Troubleshooting & Safety Plan** (PPE requirements, LOTO procedures, actionable tasks).
12. **Preventive Maintenance Recommendations** (Long-term service life actions and component inspections).
13. **Technician Review & Field Sign-Off** (Interactive or printable signature block for certified technicians).
14. **Regulatory Disclaimers & Safety Standards** (ASME A17.1 / CSA B44 advisory decision-support notices).

---

## 2. Technology Stack

| Component | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Language** | Python | `>= 3.10` (Tested on 3.10 - 3.14) | Core application platform |
| **User Interface** | Streamlit | `>= 1.35.0` | Dark-navy industrial technician dashboard |
| **Vector Indexing** | FAISS CPU (`faiss-cpu`) | `>= 1.8.0` | Fast inner-product dense vector search |
| **Embeddings** | Sentence-Transformers | `>= 3.0.0` | `all-MiniLM-L6-v2` 384-dimensional dense vectors |
| **Relational & Search** | SQLite 3 | `Standard Library` | ACID storage, FTS5 lexical BM25 search, audit logs |
| **Data Processing** | Pandas & NumPy | `>= 2.2.0`, `>= 1.26.0` | Telemetry signal normalization & tabular parsing |
| **PDF Reporting** | ReportLab | `>= 4.0.0` (v5.1.0) | Publication-grade 14-section engineering report generator |
| **LLM Integration** | LangChain / HTTP Adapters | `>= 0.2.0` | Configurable OpenAI, Gemini, Anthropic interfaces |
| **Configuration** | python-dotenv | `>= 1.0.0` | Environment variables & secret isolation |
| **Testing & Evaluation**| Pytest & Unittest | `>= 8.0.0` | 145 automated unit, integration, and safety tests |

---

## 3. Project Directory Structure

```
FAULT_SENSE_PROJECT/
├── app.py                         # Streamlit application entry point & page router
├── demo_e2e.py                    # Complete Phase 8 CLI end-to-end interactive demo
├── demo_retrieval.py              # Phase 4 CLI standalone retrieval demonstration
├── run_evaluation.py              # Phase 8 comparative benchmark runner (Baseline vs Verified)
├── run_tests.py                   # Automated test runner (145 tests across 15 suites)
├── config/
│   ├── __init__.py
│   └── settings.py                # Environment configuration, validation & secret masking
├── src/
│   ├── ingestion/                 # Phase 1 & 2: Pipeline, CSV/JSON parser, telemetry normalizer
│   │   ├── pipeline.py
│   │   ├── preprocessor.py
│   │   ├── validators.py
│   │   └── exceptions.py
│   ├── knowledge_base/            # Case repository, validated models, provenance rules
│   │   ├── models.py
│   │   ├── repository.py
│   │   └── exceptions.py
│   ├── retrieval/                 # Phase 3 & 4: Dense & lexical search, topology, ranking
│   │   ├── document_builder.py    # Canonical semantic case chunking
│   │   ├── embeddings.py          # SentenceTransformer singleton cache & deterministic embedder
│   │   ├── evidence.py            # EvidencePackage, EvidenceSufficiency, MatchRationale
│   │   ├── index_manager.py       # Atomic FAISS index rebuild & repository sync
│   │   ├── ranking.py             # Configurable hybrid weights & soft re-ranking
│   │   ├── retrieval_service.py   # Multi-factor evidence retrieval service
│   │   ├── retriever.py           # HybridRetriever combining FAISS and FTS5
│   │   ├── topology.py            # Elevator subsystem electrical/mechanical coupling graph
│   │   └── vector_store.py        # FAISS IndexFlatIP + secure UTF-8 JSON metadata mapping
│   ├── diagnosis/                 # Phase 5, 6 & 7: Engine, verifier, assistant & adapters
│   │   ├── assistant.py           # Investigation-scoped conversational assistant service
│   │   ├── diagnostic_enricher.py # 12-factor enriched technical diagnostic dossier generator
│   │   ├── engine.py              # Diagnostic orchestrator (retrieval -> LLM -> loop -> DB)
│   │   ├── fallback.py            # Transparent offline deterministic diagnostic engine
│   │   ├── prompt_builder.py      # Untrusted data isolation & epistemic separation rules
│   │   ├── schema.py              # DiagnosticReport & CandidateCause Pydantic models
│   │   ├── session.py             # Investigation session state management
│   │   ├── validator.py           # Anti-hallucination citation guard & JSON schema checks
│   │   ├── llm/                   # Isolated LLM Provider Adapters
│   │   │   ├── base.py            # BaseLLMProvider, mask_credential, custom exceptions
│   │   │   └── providers.py       # OpenAI, Gemini, Anthropic, and Mock providers
│   │   └── verification/          # Phase 6: Agentic Self-Verification Loop
│   │       ├── deterministic.py   # Deterministic claim & telemetry contradiction verifier
│   │       ├── loop.py            # AgenticVerificationLoop iterative re-retrieval
│   │       ├── schema.py          # ClaimStatus, VerificationVerdict, VerificationRecord
│   │       └── service.py         # Independent DiagnosisVerificationService
│   ├── storage/                   # SQLite database manager & repositories
│   │   ├── database.py            # SQLite schema initialization (cases, FTS5, investigations)
│   │   └── repository.py          # Session and investigation persistence
│   ├── evaluation/                # RAGAS evaluation harness & metrics calculator
│   │   ├── evaluator.py
│   │   └── metrics.py
│   ├── ui/                        # Phase 7: Streamlit Technician-Facing Pages
│   │   ├── components/            # Header, sidebar, metric cards, status badges
│   │   └── pages/                 # Overview, Investigation, Results, Report, KB, History, Eval, Settings
│   │       └── diagnostic_report.py # Dedicated Step 4 publication report & sign-off page
│   └── utils/                     # Logging, exceptions, health checks & ReportLab PDF generator
│       └── report_generator.py    # ASME A17.1 compliant 14-section ReportLab PDF builder
├── data/
│   ├── sample_fault_cases.json    # Initial 12 benchmark cases (synthetic & verified field logs)
│   ├── sample_fault_cases.csv     # Tabular CSV representation for import validation
│   ├── evaluation_test_set.json   # Phase 8 labeled evaluation dataset (8 benchmark scenarios)
│   ├── evaluation_report.json     # Phase 8 automated benchmark metrics output
│   ├── evaluation_report.md       # Phase 8 generated comparative evaluation report
│   ├── schema.json                # JSON Schema draft 2020-12 specification
│   ├── fault_sense.db             # Persistent SQLite database (relational + FTS5 + audit)
│   └── vector_store/faiss/        # FAISS binary index, metadata.json, and manifest.json
├── tests/
│   ├── test_phase8_robustness.py  # Phase 8: Credential masking, synthetic labeling, timeouts
│   ├── test_verification_loop.py  # Phase 6: Agentic self-verification, retries & audit tests
│   ├── test_diagnosis_engine.py   # Phase 5: LLM adapters, prompt safety, validator & fallback
│   ├── test_retrieval_service.py  # Phase 4: Evidence packaging, ranking, sufficiency & topology
│   ├── test_vector_store.py       # Phase 3: Vector dimensions, mapping, rebuilds & corruption
│   ├── test_repository.py         # Phase 2: SQLite persistence & FTS5 full-text search
│   ├── test_ingestion.py          # Phase 1: CSV/JSON file ingestion & duplicate rejection
│   ├── test_preprocessor.py       # Phase 1: Pandas & NumPy signal normalization
│   ├── test_schema.py             # Phase 1: Schema validations & provenance enforcement
│   ├── test_indexing_interface.py # Vector embedding payload formatting
│   ├── test_health.py             # System health probe tests
│   ├── test_smoke.py              # End-to-end startup smoke tests
│   └── test_config.py             # Configuration & secret masking tests
├── requirements.txt               # Application dependencies
├── .env.example                   # Environment configuration template
├── .gitignore                     # Git exclusion rules (protects .env, *.db, *.log)
└── README.md                      # Comprehensive system documentation
```

---

## 4. Dataset Format & Provenance Separation

FaultSense enforces strict schema validation for every ingested fault case. Cases are stored in SQLite and indexed in FAISS with non-pickle JSON metadata.

### Validated Fault-Case Schema (12 Fields)

| Field | Type | Description |
| :--- | :--- | :--- |
| `case_id` | String | Unique case identifier (e.g., `CASE-SYNTH-ELEV-001`, `CASE-FIELD-ELEV-101`) |
| `subsystem` | String | Subsystem (`door_system`, `traction_drive`, `braking_system`, `safety_gear`, etc.) |
| `fault_code` | String | OEM Diagnostic Trouble Code (e.g., `E-DR-201`, `E-TRC-402`) |
| `symptoms` | List[String] | Natural language observations and technician symptom descriptions |
| `telemetry_summary` | Object | Normalized sensor telemetry (e.g., `dc_bus_voltage_v`, `optical_attenuation_db`) |
| `confirmed_root_cause` | String | Ground-truth root cause identified during physical maintenance |
| `corrective_action` | String | OEM-compliant corrective maintenance action taken |
| `source_title` | String | Document or advisory title |
| `source_reference` | String | OEM bulletin or work order reference number |
| `source_type` | String | Provenance classification: `oem_advisory`, `field_report`, or `synthetic_illustrative` |
| `verification_status` | String | Verification level: `verified`, `unverified`, or `rejected` |
| `metadata` | Object | Arbitrary metadata (e.g., `is_synthetic: true`, `model_series`, `building_type`) |

### Provenance Separation Rule
To maintain strict data integrity:
- **Field Cases** (`oem_advisory`, `field_report`): Real-world maintenance records from verified service events.
- **Illustrative Cases** (`synthetic_illustrative`): Clearly flagged with `is_synthetic: true`. They are displayed with distinct visual badges in the UI and are never passed off as verified field incidents.
- **Evaluation Cases** (`data/evaluation_test_set.json`): Kept in a dedicated evaluation dataset file to prevent test leakage into the primary vector store.

---

## 5. Installation & Environment Configuration

### Prerequisites
- Python 3.10+ (tested through Python 3.14)
- Git (optional)

### Step 1: Create and Activate Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Key configuration parameters in `.env`:
```ini
# Application Mode (set true for 100% offline operation without API keys)
DEMO_MODE=true

# LLM Provider Selection: mock, openai, gemini, anthropic
LLM_PROVIDER=mock
LLM_MODEL=gpt-4o-mini
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=2

# API Credentials (leave empty when using DEMO_MODE=true or LLM_PROVIDER=mock)
OPENAI_API_KEY=
GEMINI_API_KEY=
ANTHROPIC_API_KEY=

# Local Storage Paths
DATABASE_PATH=data/fault_sense.db
FAISS_INDEX_DIR=data/vector_store/faiss
```

### Secret Protection & Credential Masking
FaultSense enforces strict secret isolation:
- `.env` and `*.log` files are excluded in `.gitignore`.
- [`mask_credential()`](src/diagnosis/llm/base.py) sanitizes all API keys (e.g., `sk-p...7890`). Credentials **never** appear in application logs, UI displays, SQLite investigation tables, or exported diagnostic reports.

---

## 6. Startup Commands & Offline Demo Mode

### 1. Launch the Streamlit Technician Dashboard
```bash
streamlit run app.py
```
Open `http://localhost:8501` in your browser.

### 2. Run the End-to-End CLI Demo (`demo_e2e.py`)
To test the complete workflow without a web browser:
```bash
python demo_e2e.py
```
The script automatically demonstrates:
1. System boot and health check probes.
2. In-KB supported fault diagnosis (Optical curtain obstruction) verified on step 1.
3. Out-of-KB novel fault rejection (Overspeed governor trip) triggering bounded retries (2/2) and exiting with an explicit `VERIFICATION_LOOP_INCONCLUSIVE` advisory.
4. Conversational technician assistant with citation validation and out-of-domain query rejection.
5. SQLite audit trail persistence and session reloading.

### 3. Demo Mode (100% Offline, Zero Cost)
When `DEMO_MODE=true` or when no external API credentials are provided:
- The system uses the **Deterministic Fallback Engine** ([`src/diagnosis/fallback.py`](src/diagnosis/fallback.py)) and **Deterministic Verifier** ([`src/diagnosis/verification/deterministic.py`](src/diagnosis/verification/deterministic.py)).
- Semantic vectors are computed locally using `all-MiniLM-L6-v2` (~90 MB, cached in user directory).
- Diagnostic reports clearly state `is_fallback: true` with transparent reasoning provenance.
- Zero network traffic or paid API consumption is required.

---

## 7. LLM Provider Setup

FaultSense isolates LLM communication through provider adapters ([`src/diagnosis/llm/providers.py`](src/diagnosis/llm/providers.py)):

### OpenAI / Compatible (Local Ollama / vLLM / Groq)
```ini
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...
# For local Ollama or vLLM:
# OPENAI_BASE_URL=http://localhost:11434/v1
```

### Google Gemini
```ini
LLM_PROVIDER=gemini
LLM_MODEL=gemini-1.5-flash
GEMINI_API_KEY=AIzaSy...
```

### Anthropic Claude
```ini
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-...
```

---

## 8. Phase 8 Comparative Evaluation & Benchmark Methodology

To evaluate the self-verification approach rigorously, FaultSense was benchmarked against a **Baseline Single-Pass RAG** using the exact same retrieval parameters ($k=5$, identical cosine similarity metrics) across a labeled test set of 8 realistic elevator failure scenarios (`data/evaluation_test_set.json`).

### Benchmark Scenarios
- **In-Knowledge-Base Scenarios (6 cases)**: Standard documented failures across door systems, VVVF traction drives, motor encoders, brake shoe mechanical drag, hydraulic proportional down-valves, and landing door interlock contacts.
- **Out-of-Knowledge-Base / Contradictory Scenarios (2 cases)**:
  - `EVAL-TEST-007`: Novel overspeed governor flyweight mechanism trip (zero cases in KB).
  - `EVAL-TEST-008`: Contradictory technician claim (reported open-circuit brake coil, but telemetry sensor proves 4.2 A continuous coil current).

### Measured Comparative Results

```
================================================================================
COMPARATIVE EVALUATION SUMMARY (Actual Measured Benchmark Data)
================================================================================
Total Test Cases             : 8 (6 In-KB Groundable, 2 Out-of-KB / Contradictory)
Evaluation Runner            : run_evaluation.py -> data/evaluation_report.json
================================================================================
```

| Evaluation Metric | Baseline Single-Pass RAG | Self-Verifying RAG | Difference / Impact |
| :--- | :---: | :---: | :--- |
| **Retrieval Hit Rate (In-KB)** | `83%` | `83%` | Identical dense vector foundation |
| **Root-Cause Ranking Accuracy** | `67%` | `50%` | Verified engine cautiously defers borderline cases |
| **Evidence Grounding Score** | `35%` | `30%` | Reflects strict claim verification requirements |
| **Hallucination Rejection Rate** | **`0%`** (Leaked 100%) | **`100%`** (Caught 100%) | **Critical Safety Gain**: Zero ungrounded hypotheses leaked |
| **First-Pass Pass Rate** | N/A (Single-pass) | `50%` | Finalized on step 1 without needing retry |
| **Inconclusive Terminal Rate** | `0%` (Silently approves) | `50%` | Directs technicians to multimeter checks when evidence is missing |
| **Mean End-to-End Latency** | `1170.0 ms` | `54.3 ms` (warm cache) | Fast sub-100ms technician response |

### Honest Key Takeaways
1. **Safety Over Raw Guessing**: Baseline single-pass RAG achieved a superficially higher ranking accuracy on borderline in-KB cases (67% vs 50%) solely because it guessed a cause from weak evidence. However, **Baseline RAG completely failed on safety** (`0%` rejection rate), confidently inventing plausible-sounding explanations for the novel flyweight governor fault and accepting the contradictory open-circuit brake coil claim.
2. **100% Protection Against Hallucinated Root Causes**: The self-verification loop caught and rejected **100%** of the out-of-KB and contradictory failure modes. It exhausted its bounded retries (2/2) and returned an explicit `VERIFICATION_LOOP_INCONCLUSIVE` status with recommended physical multimeter checks.
3. **Singleton Embedding Optimization**: By implementing `_SHARED_MODEL_CACHE` in [`SentenceTransformerEmbeddingGenerator`](src/retrieval/embeddings.py), warm inference latency dropped from ~1,200 ms down to **54.3 ms**, easily meeting interactive field performance requirements.

To run the comparative benchmark at any time:
```bash
python run_evaluation.py
```

---

## 9. Automated Test Suite

FaultSense includes **145 automated unit and integration tests** across 15 test suites validating all implementation phases, UI navigation, telemetry uploads, technician review persistence, and 14-section ReportLab PDF generation.

### Execute Tests via Pytest:
```bash
pytest
```
*Output: `145 passed in 7.97s`*

### Execute Tests via Standalone Runner:
```bash
python run_tests.py
```

### Test Suite Coverage Breakdown

| Test Suite | File | Tests | Validated Capabilities |
| :--- | :--- | :---: | :--- |
| **UI Telemetry, PDF Reports & Review** | `test_ui_and_reports.py` | 18 | CSV/JSON telemetry uploads, malformed JSON recovery, 14-section ReportLab PDF generation, technician review SQLite persistence, live sign-off block |
| **Master Audit Scenarios (A–K)** | `test_audit_scenarios.py` | 11 | End-to-end audit: standard diagnosis, CSV/JSON telemetry, ungrounded rejections, retry bounding, provider fallback, persistence, KB updates, UI workflow |
| **Phase 8: Robustness & Security** | `test_phase8_robustness.py` | 5 | Credential sanitization, synthetic case flagging, LLM timeout fallback, malformed JSON recovery, bounded retries on novel faults |
| **Phase 6: Verification Loop** | `test_verification_loop.py` | 7 | Step 1 finalization, re-retrieval query expansion, anti-cycling guard, inconclusive exit, SQLite audit trail persistence |
| **Phase 5: Diagnostic Engine** | `test_diagnosis_engine.py` | 13 | LLM provider adapters, prompt injection defenses, JSON validation, anti-hallucination citation sanitization, fallback reasoning |
| **Phase 4: Evidence Retrieval** | `test_retrieval_service.py` | 13 | Top-K retrieval, hybrid ranking strategies, noise floor thresholds, subsystem topology propagation |
| **Phase 3: Vector Store** | `test_vector_store.py` | 11 | FAISS IndexFlatIP, L2 normalization, non-pickle metadata mapping, atomic re-indexing, corruption recovery |
| **Phase 2: Relational DB & FTS5**| `test_repository.py` | 9 | SQLite schema initialization, case CRUD, FTS5 full-text search, investigation history queries |
| **Phase 1: Ingestion & Schema** | `test_ingestion.py`, `test_schema.py`, `test_preprocessor.py` | 33 | CSV/JSON parsing, duplicate rejection, telemetry normalization, provenance enforcement |
| **Configuration & Health Probes**| `test_config.py`, `test_health.py`, `test_smoke.py`, `test_ui_and_assistant.py`, `test_indexing_interface.py` | 25 | Secret masking, system health diagnostics, end-to-end startup verification |
| **TOTAL** | **15 Suites** | **145** | **145 Passed, 0 Failed, 0 Skipped, 0 Errors** |

---

## 10. Local Storage Locations

| Artifact | Default Path | Format | Description |
| :--- | :--- | :--- | :--- |
| **FAISS Binary Index** | `data/vector_store/faiss/index.faiss` | Binary (FAISS) | Dense inner-product vector index (384 dimensions) |
| **Vector Metadata** | `data/vector_store/faiss/metadata.json` | JSON (UTF-8) | Row position $\rightarrow$ case metadata mapping (zero pickle) |
| **Index Manifest** | `data/vector_store/faiss/manifest.json` | JSON (UTF-8) | Embedding model info and SHA-256 integrity checksums |
| **SQLite Database** | `data/fault_sense.db` | SQLite 3 | `fault_cases`, `fault_cases_fts`, and `investigations` audit tables |
| **Evaluation Test Set** | `data/evaluation_test_set.json` | JSON (UTF-8) | 8 labeled benchmark scenarios |
| **Evaluation Reports** | `data/evaluation_report.md` | Markdown / JSON | Generated comparative evaluation metrics |
| **Application Logs** | `logs/fault_sense.log` | Text (Rotating) | Centralized application runtime logs |

---

## 11. Known Limitations & Operating Boundaries

1. **Advisory Decision Support Only**: FaultSense does not send signals to elevator controllers or safety circuits. It is strictly an informational assistant for certified technicians.
2. **Knowledge Base Size**: The initial knowledge base contains 12 core historical cases and 8 evaluation scenarios. While sufficient for architectural validation, real-world field deployment requires continuous ingestion of thousands of OEM bulletins and maintenance logs.
3. **Deterministic Verifier Heuristics**: In offline demo mode, the deterministic verification engine relies on keyword grounding ratios and sensor contradiction checks. While effective at catching obvious hallucinations, it does not match the deep contextual nuance of a frontier LLM verifier (e.g., GPT-4o or Gemini 1.5 Pro).
4. **Local Single-Node Deployment**: Storage is backed by local SQLite and FAISS files, designed for laptop or field-tablet deployment. Enterprise multi-technician synchronization would require migrating SQLite to PostgreSQL and FAISS to a managed vector store.

---

## 12. Troubleshooting

| Symptom | Probable Cause | Recommended Resolution |
| :--- | :--- | :--- |
| `HuggingFace download error` | Restricted network or firewall on first run | Verify internet connectivity during initial model download of `all-MiniLM-L6-v2` (~90 MB), or pre-populate `~/.cache/huggingface/hub/`. |
| `CorruptIndexError` on startup | Interrupted disk write or corrupted index files | FaultSense catches damaged files automatically. Navigate to **Knowledge Base** $\rightarrow$ **Vector Store** and click **Rebuild Vector Index**. |
| `UnicodeEncodeError: 'charmap'` | Windows console code page set to legacy cp1252 | Handled automatically in scripts via UTF-8 reconfigure. Alternatively run `chcp 65001` in PowerShell before running CLI scripts. |
| `No base Python found` in IDE | Virtual environment not selected | Select `.venv/Scripts/python.exe` as the default interpreter in VS Code / IDE settings. |
| `API Rate Limit (HTTP 429)` | External LLM provider quota exceeded | FaultSense automatically engages the **Deterministic Fallback Engine** (`is_fallback=True`), ensuring uninterrupted troubleshooting. |

---

*FaultSense Phase 8 Final Validation & Delivery Completed.*
