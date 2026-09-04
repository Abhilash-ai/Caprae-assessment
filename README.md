# Caprae Lead Prioritization & Enrichment Engine
> **Caprae Capital Full Stack Developer AI-Readiness Challenge — Path A Submission**  
> **Candidate:** Abhilash Maiske  
> **Reference Product:** [SaaSQuatch Leads](https://www.saasquatchleads.com)  

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![React 19](https://img.shields.io/badge/React-19-61dafb.svg)](https://react.dev/)
[![SQLite](https://img.shields.io/badge/SQLite-ACID-003B57.svg)](https://www.sqlite.org/)
[![Tests](https://img.shields.io/badge/Tests-15%20Passed-brightgreen.svg)](backend/tests/)

---

## Table of Contents
1. [Executive Summary & SDR Workflow Value](#1-executive-summary--sdr-workflow-value)
2. [Step 1: Reference Product Analysis (SaaSQuatch Leads)](#2-step-1-reference-product-analysis-saasquatch-leads)
3. [Feature Rationale (Why Path A: Lead Prioritization & Enrichment Engine)](#3-feature-rationale-why-path-a)
4. [Architecture & Technical Decisions (Step 3 Requirements)](#4-architecture--technical-decisions-step-3-requirements)
   - [Database Choice & Justification](#database-choice--justification)
   - [Performance & Caching Strategy](#performance--caching-strategy)
   - [Hosting Architecture](#hosting-architecture)
   - [Cloud Scaling Roadmap](#cloud-scaling-roadmap)
5. [Core Engine Modules](#5-core-engine-modules)
   - [1. Data Hygiene & Validation Engine](#1-data-hygiene--validation-engine)
   - [2. Fuzzy Deduplication & Clustering Engine](#2-fuzzy-deduplication--clustering-engine)
   - [3. Configurable ICP Fit Scoring Engine](#3-configurable-icp-fit-scoring-engine)
   - [4. Standard CRM Exporter (HubSpot & Salesforce)](#4-standard-crm-exporter-hubspot--salesforce)
6. [Quick Start & Setup Instructions](#6-quick-start--setup-instructions)
7. [Sample Dataset & Testing](#7-sample-dataset--testing)
8. [API Documentation & cURL Examples](#8-api-documentation--curl-examples)
9. [Automated Test Suite](#9-automated-test-suite)

---

## 1. Executive Summary & SDR Workflow Value

Sales Development Representatives (SDRs) and outbound revenue teams live and die by **speed to lead** and **pipeline conversion efficiency**. While web-scraping tools like SaaSQuatch Leads solve the top-of-funnel raw volume problem by extracting thousands of contact rows, **raw scraped data is inherently dirty, unranked, and CRM-incompatible**. 

An SDR presented with 1,000 raw scraped rows spends 30-40% of their workday manually cleaning spreadsheet columns, weeding out duplicates, looking up company sizes, and debating who to call first. Worse, emailing unvalidated or role-based addresses (`info@`, `sales@`) spikes domain bounce rates and destroys email deliverability.

This project delivers **Path A (Quality First): The Lead Prioritization & Enrichment Engine** — an automated, post-scraping workflow engine that takes raw scraper output and produces a clean, deduplicated, ICP-ranked, CRM-ready lead pipeline in milliseconds.

---

## 2. Step 1: Reference Product Analysis (SaaSQuatch Leads)

### Inputs, Outputs, and Core Workflow
- **What SaaSQuatch Leads Does:** SaaSQuatch Leads is an automated web/directory scraping tool that queries public internet directories, Google Maps, company websites, and social platforms to discover potential sales prospects.
- **Inputs:** Search parameters such as target keywords, company niches, geographic locations, and industry classifications.
- **Outputs:** Flat CSV or JSON tables containing raw scraped records (e.g., `first_name`, `last_name`, `title`, `company`, `domain`, `email`, `phone`, `city`).
- **Core Workflow:** User inputs criteria &rarr; Scraper crawls indexed sources &rarr; Raw records are aggregated &rarr; User downloads an unranked CSV dump.

### The SDR User Persona & Definition of "Done"
- **The User:** SDRs, Account Executives (AEs), Growth Marketers, and PE Origination Associates.
- **What "Done" Means to the User:** "Done" is **NOT** a massive spreadsheet of 2,000 unverified names. "Done" is **a clean, verified, prioritized, exportable list of high-intent decision-makers that can be imported directly into HubSpot or Salesforce with zero manual remapping, zero duplicate spam, and minimal bounce risk.**

### 3 Concrete Gaps in SaaSQuatch Leads That Cripple Sales Workflows
1. **Zero ICP Prioritization / Lead Scoring:**  
   Raw scrapers output flat lists without context. An SDR cannot tell whether row #14 is an intern at a 5-person agency or the Chief Revenue Officer at a $50M ARR SaaS business. Without automated ICP weighting (seniority, industry tier, company scale), sales reps waste hours cherry-picking leads manually.
2. **No Deduplication Across Scraped Sources & Variations:**  
   When scraping across multiple directories or searches, the same individual frequently appears multiple times under slight naming or entity variations (e.g., *"Sarah Connor"* at *"Cyberdyne Systems"* vs *"Cyberdyne Systems Inc"*). Contacting the same prospect multiple times creates an unprofessional brand impression and pollutes the CRM.
3. **Severe Data Hygiene & Deliverability Blindspots:**  
   Scrapers blindly capture generic role accounts (`info@`, `sales@`, `admin@`, `support@`) or malformed emails. Blasting cold outreach to these addresses triggers email spam filters, tanks sender domain reputation, and results in near-zero response rates.
4. **Lack of CRM-Ready Field Schemas:**  
   Scraper dumps use proprietary or arbitrary column headers. Revenue Ops teams must spend tedious hours remapping columns to match standard HubSpot and Salesforce lead object specifications.

---

## 3. Feature Rationale (Why Path A)

Rather than building multiple shallow tools, **Path A (Quality First)** addresses the core bottleneck between lead generation and revenue conversion.

| Core Problem in SDR Workflow | Solution in This Engine | Business Value Impact |
| :--- | :--- | :--- |
| **Duplicate Lead Chaos** | Canonical legal suffix stripping + fuzzy Levenshtein sequence matching on name, company, and domain. | Eliminates double-outreach, protects brand reputation, keeps CRM clean. |
| **Unranked Prospects** | Configurable, transparent ICP scoring engine (Title Seniority + Industry Fit + Company Headcount). | Focuses SDR outreach on Tier 1 high-probability buyers first, increasing conversion rates. |
| **High Bounce Rates** | Automated data hygiene checks (RFC syntax, generic role-based detection e.g. `info@`/`sales@`, domain health). | Safeguards outbound email domain reputation and inbox deliverability. |
| **Manual CRM Formatting** | One-click export into standard HubSpot and Salesforce Lead CSV schemas. | Eliminates 1-2 hours of manual CSV reformatting per campaign. |

---

## 4. Architecture & Technical Decisions (Step 3 Requirements)

### Database Choice & Justification
- **Selected Engine:** **SQLite (via SQLAlchemy ORM)**
- **Rationale:** 
  - **Zero-Latency Embedded Relational Engine:** For a 5-hour build and local SDR/campaign-level processing pipelines, SQLite provides zero-configuration ACID compliance with zero background daemon overhead.
  - **Full Relational Integrity:** We use relational tables (`batches` and `leads` with foreign key relationships, cascade deletion, and indexing) rather than unstructured JSON blobs.
  - **Seamless Migration Path:** Because the schema is built using SQLAlchemy ORM abstractions, switching to PostgreSQL for high-concurrency production requires only swapping the `DATABASE_URL` connection string to `postgresql://...` with zero application code changes.

### Performance & Caching Strategy
- **Current MVP Strategy:** 
  - Processing 1,000 leads takes **< 100 milliseconds** using in-memory vectorized parsing and fast Python `SequenceMatcher` comparison. At this scale, in-memory processing avoids network round-trips to external cache layers.
- **Production Scale Strategy (>100k leads/day):**
  - **Redis Cache Layer:** Cache normalized company name hashes and domain WHOIS/MX verification results to prevent re-evaluating recurring corporate entities across scrapers.
  - **Asynchronous Task Queue (Celery / ARQ):** Offload multi-thousand-row deduplication runs to background worker pools with WebSockets streaming progress back to the SDR's dashboard.

### Hosting Architecture
- **Selected Setup:** **Unified Single-Container Application**
- **Rationale:** 
  - The frontend is built using Vite into static optimized assets (`frontend/dist`) and mounted directly into the FastAPI application via `fastapi.staticfiles.StaticFiles`.
  - This provides the best of both worlds: a single port (`8000`), a single Docker image, no cross-origin CORS configuration headaches in production, and zero serverless cold-start latency.
  - Can also be decoupled at will: the Vite React frontend can be deployed statically to Cloudflare Pages/Vercel while FastAPI runs on a container service.

### Cloud Scaling Roadmap
- **MVP Deployment:** Render, Railway, or Fly.io (Single container deploy in 2 minutes via Dockerfile).
- **Enterprise / Production Deployment:** 
  - **Frontend:** AWS CloudFront CDN + S3 static bucket.
  - **Backend API:** AWS ECS Fargate or Google Cloud Run (auto-scaling container instances).
  - **Database:** AWS RDS PostgreSQL (Multi-AZ with read replicas).
  - **File Storage:** AWS S3 for raw CSV uploads and processed export downloads.

---

## 5. Core Engine Modules

### 1. Data Hygiene & Validation Engine (`backend/engine/validation.py`)
- RFC-compliant email regex validation.
- Detection of **20+ generic role-based prefixes** (`info@`, `sales@`, `support@`, `admin@`, `contact@`, `inquiries@`, `helpdesk@`, `billing@`, `jobs@`, etc.).
- Domain cleansing (stripping `https://`, `http://`, `www.`, path trailing characters) and placeholder domain filtering (`example.com`, `test.com`).
- Missing data detection (missing names, missing domains, missing job titles).
- Generates a **0-100 Data Quality Health Score** with explicit penalty breakdowns and human-readable issue tags.

### 2. Fuzzy Deduplication & Clustering Engine (`backend/engine/deduplication.py`)
- **Canonical Entity Normalization:** Strips common corporate legal suffixes (`Inc`, `LLC`, `Corp`, `Corporation`, `Ltd`, `Limited`, `Group`, `Technologies`, `Systems`, `Global`).
- **Multi-Pass Deduplication Matching:**
  - *Pass 1:* Exact email identity match.
  - *Pass 2:* Identical normalized domain + high fuzzy name similarity (&ge; 82%).
  - *Pass 3:* High fuzzy company match (&ge; 85%) + high fuzzy name match (&ge; 85%).
- **Cluster & Primary Lead Selection:** Disjoint-set graph clustering groups duplicates. The engine designates the highest-quality, most complete contact as the **Primary Lead** and flags duplicates with explicit reasons (e.g., *"Duplicate of primary contact #1: Matching domain (cyberdyne.io) with 90% name match"*).

### 3. Configurable ICP Fit Scoring Engine (`backend/engine/scoring.py`)
- Weighted dynamic scoring model:
  - **Title Seniority (Weight: 40%):** Evaluates regex role patterns across C-Suite/Founders (100 pts), VP/Heads (85 pts), Directors (70 pts), Managers/Leads (50 pts), Senior ICs (35 pts), Reps/Associates (20 pts), and Interns (5 pts).
  - **Industry Fit (Weight: 35%):** Configurable target lists (Tier 1: B2B SaaS, Enterprise Software, HealthTech, FinTech, Cybersecurity, AI = 100 pts; Tier 2: Logistics, Manufacturing = 60 pts; Unmatched = 20 pts).
  - **Company Headcount Fit (Weight: 25%):** Configurable sweet-spot bounds (e.g. 50–1,000 employees = 100 pts; upper mid-market = 60 pts; enterprise scale / micro = 25-35 pts).
- Categorizes prospects into actionable tiers:
  - **Tier 1 (High Priority):** Score &ge; 75 / 100
  - **Tier 2 (Medium Priority):** Score 50–74 / 100
  - **Tier 3 (Low Priority):** Score < 50 / 100
- Produces full human-readable score rationales stored with every record.

### 4. Standard CRM Exporter (`backend/engine/crm_export.py`)
- **HubSpot Export:** Formatted to HubSpot's standard contact import schema (`First Name`, `Last Name`, `Email`, `Job Title`, `Company Name`, `Website URL`, `Industry`, `ICP Fit Score`, `Data Hygiene Flags`, etc.).
- **Salesforce Export:** Formatted to Salesforce's standard Lead object import schema (`FirstName`, `LastName`, `Title`, `Company`, `Email`, `Website`, `Rating`, `Status`, `LeadSource`, `ICP_Score__c`, `Quality_Issues__c`).
- Built-in toggle to automatically exclude duplicate rows from export.

---

## 6. Quick Start & Setup Instructions

### Prerequisites
- **Python 3.10+**
- **Node.js v18+ & npm** (optional if using Docker or pre-built static bundle)

### Option A: 1-Click Startup (Windows)
Double-click `run.bat` or run:
```powershell
.\run.bat
```
Then navigate to `http://localhost:8000` in your web browser.

---

### Option B: Manual Setup

#### 1. Backend Setup
```bash
# Navigate to backend
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Start FastAPI server
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

#### 2. Frontend Setup (Development Mode)
```bash
# In a second terminal, navigate to frontend
cd frontend

# Install Node dependencies
npm install

# Start Vite dev server
npm run dev
```
Open `http://localhost:5173` (Vite dev server) or `http://localhost:8000` (FastAPI production build).

---

### Option C: Docker (Single Command)
```bash
docker build -t caprae-lead-engine .
docker run -p 8000:8000 caprae-lead-engine
```
Visit `http://localhost:8000`.

---

## 7. Sample Dataset & Testing

The repository includes a synthetic realistic dataset of 51 raw scraped leads (`data/sample_leads_raw.csv`).
- **Realistic Dirty Scraper Quirks Included:**
  - Exact and fuzzy duplicate contacts across slightly varying corporate entities (*"Cyberdyne Systems"* vs *"Cyberdyne Systems Inc"*, *"Apex Logix"* vs *"Apex Logix LLC"*).
  - Role-based catch-all accounts (*"info@cloudpulse.ai"*, *"sales@vanguardrobotics.com"*, *"admin@galaxybio.org"*, *"contact@sterlinglogistics.net"*).
  - Broken syntax and missing contact info (*"invalid-email@"*, missing domains).
  - Diverse seniority spectrum from Interns to Founders/C-Suite.
- **1-Click Testing:** Clicking **"🔄 Load Sample Scraped Leads"** in the web UI immediately populates the editor, runs the pipeline, and shows real deduplication and scoring metrics in real time.

---

## 8. API Documentation & cURL Examples

FastAPI provides an interactive OpenAPI / Swagger UI at:  
👉 **`http://localhost:8000/docs`**

### Key REST Endpoints

#### 1. Health Check
```bash
curl -X GET http://localhost:8000/api/health
```

#### 2. Fetch Sample Leads
```bash
curl -X GET http://localhost:8000/api/leads/sample
```

#### 3. Process Leads Pipeline
```bash
curl -X POST http://localhost:8000/api/leads/process \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "custom_leads.csv",
    "leads": [
      {
        "first_name": "Marcus",
        "last_name": "Vance",
        "title": "Chief Revenue Officer",
        "company": "Apex Logix",
        "domain": "apexlogix.com",
        "email": "marcus@apexlogix.com",
        "industry": "Enterprise Software",
        "company_size": 450
      },
      {
        "first_name": "Marcus",
        "last_name": "Vance",
        "title": "CRO",
        "company": "Apex Logix LLC",
        "domain": "apexlogix.com",
        "email": "marcus.v@apexlogix.com",
        "industry": "Enterprise Software",
        "company_size": 450
      }
    ],
    "icp_config": {
      "weight_seniority": 40,
      "weight_industry": 35,
      "weight_size": 25
    }
  }'
```

#### 4. Export Batch to HubSpot CSV
```bash
curl -X GET "http://localhost:8000/api/batches/1/export?crm=hubspot&only_unique=true" \
  -o hubspot_cleaned_leads.csv
```

#### 5. Export Batch to Salesforce CSV
```bash
curl -X GET "http://localhost:8000/api/batches/1/export?crm=salesforce&only_unique=true" \
  -o salesforce_cleaned_leads.csv
```

---

## 9. Automated Test Suite

The engine includes 15 automated pytest tests covering:
- RFC email syntax and role-based detection.
- Legal entity suffix normalization.
- Exact and fuzzy sequence matcher deduplication.
- Disjoint-set clustering and primary lead selection.
- Multi-factor ICP score calculation and tier assignment.
- HubSpot and Salesforce CSV header validation.
- End-to-end FastAPI integration testing.

To run the test suite:
```bash
python -m pytest backend/tests/test_engine.py -v
```
**Result: 15 passed in ~1.0s.**

---

## Project Structure
```
Caprae Assessment/
├── Dockerfile                  # Multi-stage Docker deployment definition
├── README.md                   # Comprehensive project documentation
├── BUSINESS_UNDERSTANDING.md   # Step 4 written business & candidate questionnaire
├── WALKTHROUGH_SCRIPT.md       # 1-2 minute video walkthrough script
├── run.bat                     # Windows 1-click startup script
├── data/
│   └── sample_leads_raw.csv    # 51 synthetic realistic dirty scraped leads
├── backend/
│   ├── database.py             # SQLite configuration and session manager
│   ├── main.py                 # FastAPI application and REST endpoints
│   ├── models.py               # SQLAlchemy ORM and Pydantic schemas
│   ├── requirements.txt        # Python dependencies
│   ├── engine/
│   │   ├── validation.py       # Data hygiene & RFC validation engine
│   │   ├── deduplication.py    # Fuzzy deduplication & clustering engine
│   │   ├── scoring.py          # Configurable weighted ICP scoring engine
│   │   └── crm_export.py       # HubSpot and Salesforce CSV exporters
│   └── tests/
│       └── test_engine.py      # Automated pytest suite (15 tests)
└── frontend/
    ├── package.json            # Vite React dependencies
    ├── vite.config.js          # Vite config with backend API proxy
    ├── index.html              # HTML entrypoint
    └── src/
        ├── App.jsx             # Interactive functional dashboard
        ├── App.css             # High-density functional CSS styling
        └── main.jsx            # React root mount
```
