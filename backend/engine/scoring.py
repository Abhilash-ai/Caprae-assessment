import re
from typing import Dict, Any, List

C_SUITE_PATTERNS = [r"\b(ceo|cro|cto|cmo|coo|cpo|cio|cso)\b", r"\bchief\b", r"\bfounder\b", r"\bco-founder\b", r"\bpresident\b", r"\bowner\b"]
VP_PATTERNS = [r"\bvp\b", r"\bvice president\b", r"\bhead of\b", r"\bevp\b", r"\bsvp\b"]
DIRECTOR_PATTERNS = [r"\bdirector\b", r"\bmanaging director\b"]
MANAGER_PATTERNS = [r"\bmanager\b", r"\blead\b", r"\bprincipal\b"]
SENIOR_PATTERNS = [r"\bsenior\b", r"\bsr\.?\b", r"\bconsultant\b", r"\bspecialist\b", r"\bstrategist\b", r"\barchitect\b"]
REP_PATTERNS = [r"\baccount executive\b", r"\bsdr\b", r"\bbdr\b", r"\brepresentative\b", r"\bassociate\b"]
INTERN_PATTERNS = [r"\bintern\b", r"\btrainee\b", r"\bassistant\b", r"\bstudent\b"]

def evaluate_seniority(title: str) -> tuple[int, str]:
    if not title:
        return 10, "No title provided"
    
    t = title.lower()
    for p in C_SUITE_PATTERNS:
        if re.search(p, t):
            return 100, "C-Suite / Founder level"
    for p in VP_PATTERNS:
        if re.search(p, t):
            return 85, "VP / Head of Department"
    for p in DIRECTOR_PATTERNS:
        if re.search(p, t):
            return 70, "Director level"
    for p in MANAGER_PATTERNS:
        if re.search(p, t):
            return 50, "Management / Team Lead"
    for p in SENIOR_PATTERNS:
        if re.search(p, t):
            return 35, "Senior IC / Specialist"
    for p in REP_PATTERNS:
        if re.search(p, t):
            return 20, "Sales Rep / Account Exec"
    for p in INTERN_PATTERNS:
        if re.search(p, t):
            return 5, "Intern / Entry level"
    
    return 25, "General role"

def evaluate_industry(industry: str, tier1: List[str], tier2: List[str]) -> tuple[int, str]:
    if not industry:
        return 15, "Unspecified industry"

    ind_lower = industry.lower().strip()

    for t1 in tier1:
        if t1.lower() in ind_lower or ind_lower in t1.lower():
            return 100, f"Tier 1 Target Industry ({t1})"

    for t2 in tier2:
        if t2.lower() in ind_lower or ind_lower in t2.lower():
            return 60, f"Tier 2 Target Industry ({t2})"

    return 20, f"Non-target industry ({industry})"

def evaluate_company_size(size: Any, min_size: int, max_size: int) -> tuple[int, str]:
    try:
        val = int(size)
    except (ValueError, TypeError):
        val = 0

    if val <= 0:
        return 10, "Unknown company size"

    if min_size <= val <= max_size:
        return 100, f"Ideal company size ({val} employees)"
    elif 20 <= val < min_size:
        return 65, f"Sub-scale organization ({val} employees)"
    elif max_size < val <= max_size * 3:
        return 60, f"Upper-mid market ({val} employees)"
    elif val > max_size * 3:
        return 35, f"Enterprise scale ({val} employees)"
    else:
        return 25, f"Micro business ({val} employees)"

def score_lead(lead: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    w_seniority = config.get("weight_seniority", 40)
    w_industry = config.get("weight_industry", 35)
    w_size = config.get("weight_size", 25)
    tier1 = config.get("target_tier1_industries", [])
    tier2 = config.get("target_tier2_industries", [])
    min_size = config.get("min_company_size", 50)
    max_size = config.get("max_company_size", 1000)

    sen_score, sen_desc = evaluate_seniority(lead.get("title", ""))
    ind_score, ind_desc = evaluate_industry(lead.get("industry", ""), tier1, tier2)
    size_score, size_desc = evaluate_company_size(lead.get("company_size", 0), min_size, max_size)

    total_weight = w_seniority + w_industry + w_size
    if total_weight == 0:
        total_weight = 100

    weighted_score = round(
        (sen_score * w_seniority + ind_score * w_industry + size_score * w_size) / total_weight
    )

    if weighted_score >= 75:
        tier = "Tier 1 (High Priority)"
    elif weighted_score >= 50:
        tier = "Tier 2 (Medium Priority)"
    else:
        tier = "Tier 3 (Low Priority)"

    rationale = f"{sen_desc} [{sen_score}pts]; {ind_desc} [{ind_score}pts]; {size_desc} [{size_score}pts]."

    return {
        "icp_score": weighted_score,
        "icp_tier": tier,
        "seniority_score": sen_score,
        "industry_score": ind_score,
        "size_score": size_score,
        "score_rationale": rationale
    }
