"""
Caprae Lead Prioritization Engine - Interactive API Demo
Demonstrates data validation, fuzzy deduplication, ICP scoring, and CRM export.
"""

import os
import sys
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.validation import validate_lead_data
from engine.deduplication import run_deduplication
from engine.scoring import score_lead
from engine.crm_export import export_hubspot_csv, export_salesforce_csv

def main():
    print("=" * 70)
    print("Caprae Lead Prioritization & Enrichment Engine - Engine Demo")
    print("=" * 70)

    # 1. Raw sample leads with scraper noise
    raw_leads = [
        {
            "first_name": "Sarah",
            "last_name": "Connor",
            "title": "VP of Sales",
            "company": "Cyberdyne Systems",
            "domain": "cyberdyne.io",
            "email": "sarah.connor@cyberdyne.io",
            "industry": "B2B SaaS",
            "company_size": 250
        },
        {
            "first_name": "Sarah",
            "last_name": "Connor",
            "title": "VP of Sales",
            "company": "Cyberdyne Systems Inc",
            "domain": "cyberdyne.io",
            "email": "sarah.connor@cyberdyne.io",
            "industry": "B2B SaaS",
            "company_size": 250
        },
        {
            "first_name": "Michael",
            "last_name": "Chang",
            "title": "Founder & CEO",
            "company": "CloudPulse AI",
            "domain": "cloudpulse.ai",
            "email": "info@cloudpulse.ai",
            "industry": "Artificial Intelligence",
            "company_size": 35
        },
        {
            "first_name": "Rachel",
            "last_name": "Green",
            "title": "Sales Intern",
            "company": "Central Perk Media",
            "domain": "centralperk.media",
            "email": "rachel@centralperk.media",
            "industry": "Digital Media",
            "company_size": 15
        }
    ]

    print(f"\n[1/4] Ingested {len(raw_leads)} raw scraped leads...")

    # 2. Validation
    print("\n[2/4] Running Data Hygiene Validation...")
    validated = []
    for lead in raw_leads:
        val = validate_lead_data(lead)
        combined = {**lead, **val}
        validated.append(combined)
        flag_str = ", ".join(val["quality_issues"]) if val["quality_issues"] else "Verified Clean"
        print(f"  - {lead['first_name']} {lead['last_name']} ({lead['email']}): Quality Score {val['data_quality_score']}% -> [{flag_str}]")

    # 3. Deduplication
    print("\n[3/4] Running Fuzzy Deduplication & Clustering...")
    deduped = run_deduplication(validated)
    for lead in deduped:
        status = "DUPLICATE" if lead["is_duplicate"] else "PRIMARY"
        print(f"  - [{status}] {lead['first_name']} {lead['last_name']} @ {lead['company']} (Cluster: {lead['dedup_cluster_id']})")
        if lead["is_duplicate"]:
            print(f"      Reason: {lead['duplicate_reason']}")

    # 4. ICP Fit Scoring
    print("\n[4/4] Calculating Configurable ICP Fit Scores...")
    icp_config = {
        "weight_seniority": 40,
        "weight_industry": 35,
        "weight_size": 25,
        "target_tier1_industries": ["B2B SaaS", "Artificial Intelligence"],
        "target_tier2_industries": ["Digital Media"],
        "min_company_size": 50,
        "max_company_size": 1000
    }

    scored_leads = []
    for lead in deduped:
        sc = score_lead(lead, icp_config)
        full = {**lead, **sc}
        scored_leads.append(full)
        print(f"  - {full['first_name']} {full['last_name']} ({full['title']}): ICP Score = {full['icp_score']}/100 [{full['icp_tier']}]")
        print(f"      Breakdown: {full['score_rationale']}")

    # 5. CRM Export Demo
    print("\n" + "=" * 70)
    print("Sample HubSpot CRM Export (Deduplicated Clean Leads Only):")
    print("=" * 70)
    hubspot_csv = export_hubspot_csv(scored_leads, only_unique=True)
    for line in hubspot_csv.strip().split("\n")[:4]:
        print(line)

    print("\n" + "=" * 70)
    print("Demo completed successfully!")
    print("=" * 70)

if __name__ == "__main__":
    main()
