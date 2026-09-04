import csv
import io
from typing import List, Dict, Any

def export_hubspot_csv(leads: List[Dict[str, Any]], only_unique: bool = True) -> str:
    """
    Generates a CSV string formatted for HubSpot standard CRM lead/contact import.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # HubSpot Standard Headers
    headers = [
        "First Name",
        "Last Name",
        "Email",
        "Job Title",
        "Company Name",
        "Website URL",
        "Phone Number",
        "LinkedIn Profile URL",
        "Industry",
        "Number of Employees",
        "City",
        "Country/Region",
        "Lead Status",
        "ICP Fit Score",
        "ICP Tier",
        "Deduplication Status",
        "Data Hygiene Flags"
    ]
    writer.writerow(headers)

    for lead in leads:
        if only_unique and lead.get("is_duplicate"):
            continue

        flags = ", ".join(lead.get("quality_issues", [])) if lead.get("quality_issues") else "Clean"
        status = "Duplicate" if lead.get("is_duplicate") else "NEW"
        domain = lead.get("domain", "")
        if domain and not domain.startswith("http"):
            domain = f"https://{domain}"

        writer.writerow([
            lead.get("first_name", ""),
            lead.get("last_name", ""),
            lead.get("email", ""),
            lead.get("title", ""),
            lead.get("company", ""),
            domain,
            lead.get("phone", ""),
            lead.get("linkedin_url", ""),
            lead.get("industry", ""),
            lead.get("company_size", 0),
            lead.get("city", ""),
            lead.get("country", ""),
            status,
            lead.get("icp_score", 0),
            lead.get("icp_tier", ""),
            "Duplicate" if lead.get("is_duplicate") else "Primary / Unique",
            flags
        ])

    return output.getvalue()

def export_salesforce_csv(leads: List[Dict[str, Any]], only_unique: bool = True) -> str:
    """
    Generates a CSV string formatted for Salesforce standard lead object import.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Salesforce Standard Headers
    headers = [
        "FirstName",
        "LastName",
        "Title",
        "Company",
        "Email",
        "Phone",
        "Website",
        "Industry",
        "NumberOfEmployees",
        "City",
        "Country",
        "LeadSource",
        "Status",
        "Rating",
        "ICP_Score__c",
        "Deduplication_Status__c",
        "Data_Quality_Notes__c"
    ]
    writer.writerow(headers)

    for lead in leads:
        if only_unique and lead.get("is_duplicate"):
            continue

        flags = "; ".join(lead.get("quality_issues", [])) if lead.get("quality_issues") else "Verified Clean"
        domain = lead.get("domain", "")
        if domain and not domain.startswith("http"):
            domain = f"https://{domain}"

        # Rating mapping in Salesforce
        icp_score = lead.get("icp_score", 0)
        if icp_score >= 75:
            rating = "Hot"
        elif icp_score >= 50:
            rating = "Warm"
        else:
            rating = "Cold"

        status = "Unqualified - Duplicate" if lead.get("is_duplicate") else "Open - Not Contacted"

        writer.writerow([
            lead.get("first_name", ""),
            lead.get("last_name", ""),
            lead.get("title", ""),
            lead.get("company", ""),
            lead.get("email", ""),
            lead.get("phone", ""),
            domain,
            lead.get("industry", ""),
            lead.get("company_size", 0),
            lead.get("city", ""),
            lead.get("country", ""),
            "SaaSQuatch Scraped",
            status,
            rating,
            icp_score,
            "Duplicate" if lead.get("is_duplicate") else "Primary",
            flags
        ])

    return output.getvalue()
