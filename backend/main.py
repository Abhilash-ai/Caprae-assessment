import csv
import io
import os
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from database import engine, Base, get_db
import models
from engine.validation import validate_lead_data
from engine.deduplication import run_deduplication
from engine.scoring import score_lead
from engine.crm_export import export_hubspot_csv, export_salesforce_csv

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Caprae Lead Prioritization & Enrichment Engine",
    description="Quality-first lead deduplication, data hygiene validation, ICP fit scoring, and CRM export engine.",
    version="1.0.0"
)

# Enable CORS for local Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SAMPLE_CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "sample_leads_raw.csv")

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Caprae Lead Prioritization Engine",
        "reference_product": "SaaSQuatch Leads",
        "version": "1.0.0"
    }

@app.get("/api/leads/sample")
def get_sample_leads():
    """Returns the pre-loaded synthetic scraped lead dataset."""
    if not os.path.exists(SAMPLE_CSV_PATH):
        raise HTTPException(status_code=404, detail="Sample leads file not found.")
    
    leads = []
    with open(SAMPLE_CSV_PATH, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            leads.append(row)
    
    return {
        "filename": "sample_leads_raw.csv",
        "count": len(leads),
        "leads": leads
    }

def process_leads_pipeline(raw_leads: List[dict], icp_cfg: dict) -> dict:
    """Core orchestration pipeline: Validation -> Deduplication -> ICP Scoring."""
    # Step 1: Hygiene & Validation
    validated_leads = []
    for lead in raw_leads:
        val_res = validate_lead_data(lead)
        combined = {**lead, **val_res}
        if "cleaned_domain" in val_res and val_res["cleaned_domain"]:
            combined["domain"] = val_res["cleaned_domain"]
        validated_leads.append(combined)

    # Step 2: Deduplication
    deduped_leads = run_deduplication(validated_leads)

    # Step 3: ICP Fit Scoring
    processed_leads = []
    high_fit_count = 0
    total_quality = 0

    for lead in deduped_leads:
        score_res = score_lead(lead, icp_cfg)
        final_lead = {**lead, **score_res}
        if final_lead["icp_score"] >= 75:
            high_fit_count += 1
        total_quality += final_lead.get("data_quality_score", 0)
        processed_leads.append(final_lead)

    total_leads = len(processed_leads)
    dup_count = sum(1 for x in processed_leads if x.get("is_duplicate"))
    unique_count = total_leads - dup_count
    avg_quality = round(total_quality / total_leads, 1) if total_leads > 0 else 0.0

    return {
        "total_leads": total_leads,
        "unique_leads": unique_count,
        "duplicate_leads": dup_count,
        "high_fit_leads": high_fit_count,
        "avg_quality_score": avg_quality,
        "leads": processed_leads
    }

@app.post("/api/leads/process", response_model=models.BatchSummaryResponse)
def process_leads(payload: models.ProcessRequest, db: Session = Depends(get_db)):
    """Processes raw lead objects sent as JSON."""
    raw_dicts = [ld.model_dump() for ld in payload.leads]
    cfg_dict = payload.icp_config.model_dump() if payload.icp_config else models.ICPConfigRequest().model_dump()

    pipeline_res = process_leads_pipeline(raw_dicts, cfg_dict)

    # Persist Batch in SQLite
    batch = models.Batch(
        filename=payload.filename or "json_batch.csv",
        total_leads=pipeline_res["total_leads"],
        unique_leads=pipeline_res["unique_leads"],
        duplicate_leads=pipeline_res["duplicate_leads"],
        high_fit_leads=pipeline_res["high_fit_leads"],
        avg_quality_score=pipeline_res["avg_quality_score"]
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    lead_records = []
    for ld in pipeline_res["leads"]:
        rec = models.LeadRecord(
            batch_id=batch.id,
            first_name=ld.get("first_name", "") or "",
            last_name=ld.get("last_name", "") or "",
            title=ld.get("title", "") or "",
            company=ld.get("company", "") or "",
            domain=ld.get("domain", "") or "",
            email=ld.get("email", "") or "",
            phone=ld.get("phone", "") or "",
            linkedin_url=ld.get("linkedin_url", "") or "",
            industry=ld.get("industry", "") or "",
            company_size=int(ld.get("company_size") or 0),
            city=ld.get("city", "") or "",
            country=ld.get("country", "") or "",
            is_duplicate=ld.get("is_duplicate", False),
            primary_lead_id=ld.get("primary_lead_id"),
            duplicate_reason=ld.get("duplicate_reason", ""),
            dedup_cluster_id=ld.get("dedup_cluster_id", ""),
            is_valid_email=ld.get("is_valid_email", True),
            is_role_based_email=ld.get("is_role_based_email", False),
            is_valid_domain=ld.get("is_valid_domain", True),
            data_quality_score=ld.get("data_quality_score", 100),
            quality_issues=ld.get("quality_issues", []),
            icp_score=ld.get("icp_score", 0),
            icp_tier=ld.get("icp_tier", ""),
            seniority_score=ld.get("seniority_score", 0),
            industry_score=ld.get("industry_score", 0),
            size_score=ld.get("size_score", 0),
            score_rationale=ld.get("score_rationale", "")
        )
        lead_records.append(rec)

    db.add_all(lead_records)
    db.commit()
    db.refresh(batch)

    return batch

@app.post("/api/leads/upload-csv", response_model=models.BatchSummaryResponse)
async def upload_csv(
    file: UploadFile = File(...),
    weight_seniority: int = Form(40),
    weight_industry: int = Form(35),
    weight_size: int = Form(25),
    min_company_size: int = Form(50),
    max_company_size: int = Form(1000),
    db: Session = Depends(get_db)
):
    """Processes a CSV file uploaded by the user."""
    contents = await file.read()
    try:
        decoded = contents.decode("utf-8")
    except UnicodeDecodeError:
        decoded = contents.decode("latin-1")

    reader = csv.DictReader(io.StringIO(decoded))
    raw_leads = []
    for row in reader:
        raw_leads.append(row)

    if not raw_leads:
        raise HTTPException(status_code=400, detail="Uploaded CSV contains no valid rows.")

    cfg_dict = models.ICPConfigRequest(
        weight_seniority=weight_seniority,
        weight_industry=weight_industry,
        weight_size=weight_size,
        min_company_size=min_company_size,
        max_company_size=max_company_size
    ).model_dump()

    pipeline_res = process_leads_pipeline(raw_leads, cfg_dict)

    batch = models.Batch(
        filename=file.filename or "uploaded_leads.csv",
        total_leads=pipeline_res["total_leads"],
        unique_leads=pipeline_res["unique_leads"],
        duplicate_leads=pipeline_res["duplicate_leads"],
        high_fit_leads=pipeline_res["high_fit_leads"],
        avg_quality_score=pipeline_res["avg_quality_score"]
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    lead_records = []
    for ld in pipeline_res["leads"]:
        rec = models.LeadRecord(
            batch_id=batch.id,
            first_name=ld.get("first_name", "") or "",
            last_name=ld.get("last_name", "") or "",
            title=ld.get("title", "") or "",
            company=ld.get("company", "") or "",
            domain=ld.get("domain", "") or "",
            email=ld.get("email", "") or "",
            phone=ld.get("phone", "") or "",
            linkedin_url=ld.get("linkedin_url", "") or "",
            industry=ld.get("industry", "") or "",
            company_size=int(ld.get("company_size") or 0) if str(ld.get("company_size") or "").isdigit() else 0,
            city=ld.get("city", "") or "",
            country=ld.get("country", "") or "",
            is_duplicate=ld.get("is_duplicate", False),
            primary_lead_id=ld.get("primary_lead_id"),
            duplicate_reason=ld.get("duplicate_reason", ""),
            dedup_cluster_id=ld.get("dedup_cluster_id", ""),
            is_valid_email=ld.get("is_valid_email", True),
            is_role_based_email=ld.get("is_role_based_email", False),
            is_valid_domain=ld.get("is_valid_domain", True),
            data_quality_score=ld.get("data_quality_score", 100),
            quality_issues=ld.get("quality_issues", []),
            icp_score=ld.get("icp_score", 0),
            icp_tier=ld.get("icp_tier", ""),
            seniority_score=ld.get("seniority_score", 0),
            industry_score=ld.get("industry_score", 0),
            size_score=ld.get("size_score", 0),
            score_rationale=ld.get("score_rationale", "")
        )
        lead_records.append(rec)

    db.add_all(lead_records)
    db.commit()
    db.refresh(batch)

    return batch

@app.get("/api/batches", response_model=List[models.BatchSummaryResponse])
def list_batches(limit: int = 10, db: Session = Depends(get_db)):
    """List recent lead processing batches."""
    batches = db.query(models.Batch).order_by(models.Batch.id.desc()).limit(limit).all()
    return batches

@app.get("/api/batches/{batch_id}", response_model=models.BatchSummaryResponse)
def get_batch(batch_id: int, db: Session = Depends(get_db)):
    """Retrieve a specific batch with all processed leads."""
    batch = db.query(models.Batch).filter(models.Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return batch

@app.get("/api/batches/{batch_id}/export")
def export_batch_csv(
    batch_id: int,
    crm: str = Query("hubspot", pattern="^(hubspot|salesforce)$"),
    only_unique: bool = Query(True),
    db: Session = Depends(get_db)
):
    """Export processed leads formatted for HubSpot or Salesforce CRM import."""
    batch = db.query(models.Batch).filter(models.Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    leads_dicts = []
    for l in batch.leads:
        leads_dicts.append({
            "first_name": l.first_name,
            "last_name": l.last_name,
            "title": l.title,
            "company": l.company,
            "domain": l.domain,
            "email": l.email,
            "phone": l.phone,
            "linkedin_url": l.linkedin_url,
            "industry": l.industry,
            "company_size": l.company_size,
            "city": l.city,
            "country": l.country,
            "is_duplicate": l.is_duplicate,
            "data_quality_score": l.data_quality_score,
            "quality_issues": l.quality_issues or [],
            "icp_score": l.icp_score,
            "icp_tier": l.icp_tier
        })

    if crm == "hubspot":
        csv_data = export_hubspot_csv(leads_dicts, only_unique=only_unique)
        filename = f"hubspot_leads_batch_{batch_id}.csv"
    else:
        csv_data = export_salesforce_csv(leads_dicts, only_unique=only_unique)
        filename = f"salesforce_leads_batch_{batch_id}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# Static files mount for single-port / container hosting
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")
if os.path.exists(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="static")

