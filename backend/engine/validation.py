import re
from typing import Dict, Any, List

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
DOMAIN_REGEX = re.compile(r"^[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?$")

ROLE_PREFIXES = {
    "info", "sales", "support", "admin", "contact", "contactus", "inquiries",
    "helpdesk", "hello", "billing", "jobs", "careers", "marketing", "press",
    "media", "team", "office", "general", "reception", "operations", "service"
}

DISPOSABLE_OR_PLACEHOLDER_DOMAINS = {
    "example.com", "test.com", "sample.com", "localhost", "mailinator.com",
    "tempmail.com", "guerrillamail.com", "trashmail.com", "10minutemail.com"
}

def clean_domain(domain: str) -> str:
    if not domain:
        return ""
    d = domain.strip().lower()
    d = re.sub(r"^https?://", "", d)
    d = re.sub(r"^www\.", "", d)
    d = d.split("/")[0]
    return d

def validate_lead_data(lead_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates lead contact and company fields.
    Flags missing fields, malformed syntax, generic role emails, and calculates quality score.
    """
    email = str(lead_dict.get("email") or "").strip().lower()
    raw_domain = str(lead_dict.get("domain") or "").strip()
    domain = clean_domain(raw_domain)
    first_name = str(lead_dict.get("first_name") or "").strip()
    last_name = str(lead_dict.get("last_name") or "").strip()
    title = str(lead_dict.get("title") or "").strip()
    company = str(lead_dict.get("company") or "").strip()

    issues: List[str] = []
    quality_score = 100

    # 1. Email check
    is_valid_email = True
    is_role_based = False

    if not email:
        is_valid_email = False
        issues.append("Missing email address")
        quality_score -= 40
    elif not EMAIL_REGEX.match(email):
        is_valid_email = False
        issues.append("Malformed email syntax")
        quality_score -= 35
    else:
        # Check role-based
        local_part = email.split("@")[0].lower()
        if local_part in ROLE_PREFIXES or any(local_part.startswith(prefix + ".") for prefix in ROLE_PREFIXES):
            is_role_based = True
            issues.append(f"Generic role-based email ({local_part}@)")
            quality_score -= 20
        
        # Check if email domain matches domain (if domain exists)
        email_domain = email.split("@")[1]
        if domain and email_domain != domain:
            issues.append(f"Email domain ({email_domain}) differs from company domain ({domain})")
            quality_score -= 5

    # 2. Domain check
    is_valid_domain = True
    if not domain:
        is_valid_domain = False
        issues.append("Missing company domain")
        quality_score -= 20
    elif domain in DISPOSABLE_OR_PLACEHOLDER_DOMAINS:
        is_valid_domain = False
        issues.append(f"Placeholder or disposable domain ({domain})")
        quality_score -= 25
    elif not DOMAIN_REGEX.match(domain):
        is_valid_domain = False
        issues.append("Invalid domain format")
        quality_score -= 15

    # 3. Essential metadata checks
    if not first_name or not last_name:
        issues.append("Incomplete full name")
        quality_score -= 15

    if not title:
        issues.append("Missing job title")
        quality_score -= 15

    if not company:
        issues.append("Missing company name")
        quality_score -= 15

    # Clamp score between 0 and 100
    quality_score = max(0, min(100, quality_score))

    return {
        "cleaned_domain": domain,
        "is_valid_email": is_valid_email,
        "is_role_based_email": is_role_based,
        "is_valid_domain": is_valid_domain,
        "data_quality_score": quality_score,
        "quality_issues": issues
    }
