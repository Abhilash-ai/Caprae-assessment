import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from engine.validation import validate_lead_data
from engine.deduplication import normalize_company_name, are_leads_duplicate, run_deduplication
from engine.scoring import evaluate_seniority, evaluate_industry, evaluate_company_size, score_lead
from engine.crm_export import export_hubspot_csv, export_salesforce_csv

client = TestClient(app)

# ----------------- 1. VALIDATION TESTS -----------------
def test_validation_clean_lead():
    clean_lead = {
        "first_name": "Sarah",
        "last_name": "Connor",
        "title": "VP of Sales",
        "company": "Cyberdyne Systems",
        "domain": "cyberdyne.io",
        "email": "sarah.connor@cyberdyne.io"
    }
    res = validate_lead_data(clean_lead)
    assert res["is_valid_email"] is True
    assert res["is_role_based_email"] is False
    assert res["is_valid_domain"] is True
    assert res["data_quality_score"] == 100
    assert len(res["quality_issues"]) == 0

def test_validation_role_based_email():
    role_lead = {
        "first_name": "Michael",
        "last_name": "Chang",
        "title": "Founder",
        "company": "CloudPulse",
        "domain": "cloudpulse.ai",
        "email": "info@cloudpulse.ai"
    }
    res = validate_lead_data(role_lead)
    assert res["is_valid_email"] is True
    assert res["is_role_based_email"] is True
    assert any("role-based" in issue.lower() for issue in res["quality_issues"])
    assert res["data_quality_score"] < 100

def test_validation_malformed_and_missing_data():
    bad_lead = {
        "first_name": "Ghost",
        "last_name": "",
        "title": "",
        "company": "",
        "domain": "",
        "email": "broken-email@"
    }
    res = validate_lead_data(bad_lead)
    assert res["is_valid_email"] is False
    assert res["is_valid_domain"] is False
    assert res["data_quality_score"] <= 30
    assert len(res["quality_issues"]) >= 3


# ----------------- 2. DEDUPLICATION TESTS -----------------
def test_company_name_normalization():
    assert normalize_company_name("Cyberdyne Systems Inc") == "cyberdyne"
    assert normalize_company_name("Cyberdyne Systems, LLC") == "cyberdyne"
    assert normalize_company_name("Apex Logix Corporation") == "apex logix"
    assert normalize_company_name("Apex Logix") == "apex logix"

def test_are_leads_duplicate_exact_email():
    l1 = {"email": "sarah@cyberdyne.io", "first_name": "Sarah", "last_name": "Connor"}
    l2 = {"email": "SARAH@cyberdyne.io", "first_name": "S.", "last_name": "Connor"}
    is_dup, reason = are_leads_duplicate(l1, l2)
    assert is_dup is True
    assert "identical email" in reason.lower()

def test_are_leads_duplicate_fuzzy_company_and_name():
    l1 = {
        "first_name": "Sarah",
        "last_name": "Connor",
        "company": "Cyberdyne Systems",
        "domain": "cyberdyne.io",
        "email": "sarah.c@cyberdyne.io"
    }
    l2 = {
        "first_name": "Sarah",
        "last_name": "Connor",
        "company": "Cyberdyne Systems Inc",
        "domain": "cyberdyne.io",
        "email": "sconnor@cyberdyne.io"
    }
    is_dup, reason = are_leads_duplicate(l1, l2)
    assert is_dup is True

def test_run_deduplication_cluster_and_primary():
    leads = [
        {
            "first_name": "Sarah",
            "last_name": "Connor",
            "company": "Cyberdyne Systems",
            "domain": "cyberdyne.io",
            "email": "sarah@cyberdyne.io",
            "phone": "+15550101",
            "data_quality_score": 100
        },
        {
            "first_name": "Sarah",
            "last_name": "Connor",
            "company": "Cyberdyne Systems Inc",
            "domain": "cyberdyne.io",
            "email": "",
            "phone": "",
            "data_quality_score": 50
        }
    ]
    results = run_deduplication(leads)
    assert results[0]["is_duplicate"] is False
    assert results[1]["is_duplicate"] is True
    assert results[1]["primary_lead_id"] == results[0]["temp_id"]


# ----------------- 3. ICP SCORING TESTS -----------------
def test_seniority_scoring():
    score, _ = evaluate_seniority("Chief Revenue Officer")
    assert score == 100
    score, _ = evaluate_seniority("VP of Sales")
    assert score == 85
    score, _ = evaluate_seniority("Director of Marketing")
    assert score == 70
    score, _ = evaluate_seniority("Sales Intern")
    assert score == 5

def test_industry_scoring():
    tier1 = ["B2B SaaS", "FinTech"]
    tier2 = ["Logistics"]
    score, _ = evaluate_industry("B2B SaaS", tier1, tier2)
    assert score == 100
    score, _ = evaluate_industry("Logistics & Supply Chain", tier1, tier2)
    assert score == 60
    score, _ = evaluate_industry("Retail & Apparel", tier1, tier2)
    assert score == 20

def test_company_size_scoring():
    score, _ = evaluate_company_size(250, min_size=50, max_size=1000)
    assert score == 100
    score, _ = evaluate_company_size(5, min_size=50, max_size=1000)
    assert score == 25

def test_full_lead_scoring():
    lead = {
        "title": "VP of Sales",
        "industry": "B2B SaaS",
        "company_size": 250
    }
    cfg = {
        "weight_seniority": 40,
        "weight_industry": 35,
        "weight_size": 25,
        "target_tier1_industries": ["B2B SaaS"],
        "target_tier2_industries": [],
        "min_company_size": 50,
        "max_company_size": 1000
    }
    res = score_lead(lead, cfg)
    assert res["icp_score"] >= 85
    assert "Tier 1" in res["icp_tier"]
    assert len(res["score_rationale"]) > 10


# ----------------- 4. CRM EXPORT TESTS -----------------
def test_crm_export_formats():
    leads = [
        {
            "first_name": "Elena",
            "last_name": "Rostova",
            "title": "Director of Demand Gen",
            "company": "FinScale Tech",
            "domain": "finscale.co",
            "email": "elena.r@finscale.co",
            "phone": "+15550103",
            "linkedin_url": "https://linkedin.com/in/elena-rostova",
            "industry": "FinTech",
            "company_size": 120,
            "city": "New York",
            "country": "USA",
            "is_duplicate": False,
            "data_quality_score": 100,
            "quality_issues": [],
            "icp_score": 85,
            "icp_tier": "Tier 1 (High Priority)"
        },
        {
            "first_name": "Elena",
            "last_name": "Rostova",
            "title": "Director",
            "company": "FinScale Tech Inc",
            "domain": "finscale.co",
            "email": "elena@finscale.co",
            "is_duplicate": True,
            "icp_score": 80
        }
    ]

    hubspot_csv = export_hubspot_csv(leads, only_unique=True)
    assert "First Name,Last Name,Email,Job Title" in hubspot_csv
    assert "Elena,Rostova,elena.r@finscale.co" in hubspot_csv
    # Duplicate was filtered out
    assert "elena@finscale.co" not in hubspot_csv

    salesforce_csv = export_salesforce_csv(leads, only_unique=False)
    assert "FirstName,LastName,Title,Company" in salesforce_csv
    assert "Hot" in salesforce_csv
    assert "SaaSQuatch Scraped" in salesforce_csv


# ----------------- 5. API INTEGRATION TESTS -----------------
def test_api_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_api_sample_leads():
    response = client.get("/api/leads/sample")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] > 20
    assert len(data["leads"]) > 0

def test_api_process_pipeline():
    payload = {
        "filename": "test_batch.csv",
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
        ]
    }
    response = client.post("/api/leads/process", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_leads"] == 2
    assert data["unique_leads"] == 1
    assert data["duplicate_leads"] == 1
    assert data["high_fit_leads"] >= 1
