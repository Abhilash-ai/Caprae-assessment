# 1-to-2 Minute Video Walkthrough Script
**Project:** Caprae Lead Prioritization & Enrichment Engine (Path A)  
**Candidate:** Abhilash Maiske  
**Target Duration:** 90 – 110 Seconds  

---

### [0:00 – 0:25] Introduction & The SDR Problem (Tie Back to Workflow Value)
> *"Hi everyone, I'm Abhilash Maiske, and this is my submission for Caprae Capital's Full Stack Developer AI-Readiness Challenge.*  
> 
> *The reference product, SaaSQuatch Leads, solves raw web scraping—pulling thousands of rows from public directories. But for an SDR or sales team, a raw scraped CSV isn't 'done.' It's full of duplicate entries, missing domains, and generic catch-all emails like `info@` and `sales@` that destroy domain deliverability. Most critically, it has no ICP prioritization—so reps waste 30 to 40% of their day manually figuring out who to email first.*  
> 
> *To solve this, I chose **Path A: The Lead Prioritization & Enrichment Engine**—a post-scraping workflow engine that turns messy scraper dumps into clean, deduplicated, ICP-ranked, CRM-ready pipelines in seconds."*

---

### [0:25 – 1:15] Quick Live Demo (Screen Share)

#### 1. Ingestion & Preloaded Scraped Data
> *(Screen shows `http://localhost:8000`)*  
> *"Here is the application. SDRs can paste raw CSV text, upload files, or click **'Load Sample Scraped Leads'** to test our synthetic 51-lead scraper dataset. You can customize ICP scoring weights on the fly—adjusting title seniority, target industries, and company size bounds."*

#### 2. Pipeline Execution & Real-Time Intelligence
> *(Click **'⚡ Run Pipeline'**)*  
> *"In less than 50 milliseconds, our engine runs three core passes:*  
> 1. *First, **Data Hygiene & RFC Validation**: It flags broken domains and generic role accounts like `info@` and calculates a data health score.*  
> 2. *Second, **Fuzzy Deduplication**: It strips legal suffixes like 'Inc' and 'LLC' and runs sequence matching across names and domains, collapsing duplicate clusters and preserving only the highest-quality primary contact.*  
> 3. *Third, **Weighted ICP Scoring**: It scores every lead from 0 to 100 with full rationale—surfacing Tier 1 decision-makers at the very top.*  
> 
> *In our sample batch, 5 duplicates were automatically pruned, leaving 46 unique leads, 28 of which are high-fit Tier 1 targets with an 88% data health score."*

#### 3. CRM Export
> *(Click **'Export HubSpot CSV'** or show download)*  
> *"With one click, SDRs can export directly into HubSpot standard or Salesforce lead formats—with duplicates pre-filtered—ready for immediate outreach with zero manual column remapping."*

---

### [1:15 – 1:35] What I Would Build With More Time
> *"If I had more time, I would integrate real-time DNS/MX record verification with SMTP pinging to verify inbox deliverability live, and implement an LLM-powered personalized cold-outreach hook generator that extracts prospect news from company websites into a tailored first line."*

---

### [1:35 – 1:45] Conclusion
> *"Thank you for your time and consideration—I'm looking forward to the next steps with Caprae Capital!"*

---

## Recording Tips for Candidate
- **Screen:** Record your browser tab running at `http://localhost:8000`.
- **Flow:**
  1. Click *"🔄 Load Sample Scraped Leads"*.
  2. Click *"Configure ICP Criteria ▼"* to show sliders briefly.
  3. Click *"⚡ Run Pipeline"*.
  4. Point out the KPI cards (Total: 51, Unique: 46, Duplicates: 5, Tier 1: 28).
  5. Click on the *"Tier 1 High Fit"* and *"Duplicates Only"* filter tabs to show table reactivity.
  6. Click *"📥 Export HubSpot CSV"* to demonstrate instant CRM download.
- **Tools:** Loom, OBS Studio, or QuickTime.
