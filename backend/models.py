from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field
from database import Base

# SQLAlchemy ORM Models
class Batch(Base):
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), default="manual_input.csv")
    created_at = Column(DateTime, default=datetime.utcnow)
    total_leads = Column(Integer, default=0)
    unique_leads = Column(Integer, default=0)
    duplicate_leads = Column(Integer, default=0)
    high_fit_leads = Column(Integer, default=0)
    avg_quality_score = Column(Float, default=0.0)

    leads = relationship("LeadRecord", back_populates="batch", cascade="all, delete-orphan")


class LeadRecord(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id", ondelete="CASCADE"), nullable=False)
    
    # Raw Attributes
    first_name = Column(String(100), default="")
    last_name = Column(String(100), default="")
    title = Column(String(200), default="")
    company = Column(String(200), default="")
    domain = Column(String(200), default="")
    email = Column(String(255), default="")
    phone = Column(String(100), default="")
    linkedin_url = Column(String(300), default="")
    industry = Column(String(100), default="")
    company_size = Column(Integer, default=0)
    city = Column(String(100), default="")
    country = Column(String(100), default="")

    # Deduplication Fields
    is_duplicate = Column(Boolean, default=False)
    primary_lead_id = Column(Integer, nullable=True)
    duplicate_reason = Column(String(255), default="")
    dedup_cluster_id = Column(String(100), default="")

    # Data Hygiene & Validation
    is_valid_email = Column(Boolean, default=True)
    is_role_based_email = Column(Boolean, default=False)
    is_valid_domain = Column(Boolean, default=True)
    data_quality_score = Column(Integer, default=100)
    quality_issues = Column(JSON, default=list)

    # ICP Scoring
    icp_score = Column(Integer, default=0)
    icp_tier = Column(String(50), default="Tier 3 (Low)")
    seniority_score = Column(Integer, default=0)
    industry_score = Column(Integer, default=0)
    size_score = Column(Integer, default=0)
    score_rationale = Column(Text, default="")

    batch = relationship("Batch", back_populates="leads")


# Pydantic Schemas for API
class ICPConfigRequest(BaseModel):
    weight_seniority: int = Field(default=40, ge=0, le=100)
    weight_industry: int = Field(default=35, ge=0, le=100)
    weight_size: int = Field(default=25, ge=0, le=100)
    target_tier1_industries: List[str] = Field(
        default=[
            "B2B SaaS",
            "Enterprise Software",
            "Healthcare / HealthTech",
            "FinTech",
            "Cybersecurity",
            "Artificial Intelligence",
            "DeepTech / Hardware"
        ]
    )
    target_tier2_industries: List[str] = Field(
        default=[
            "Data & Analytics",
            "DevOps & Infrastructure",
            "Logistics & Supply Chain",
            "Advanced Manufacturing"
        ]
    )
    min_company_size: int = Field(default=50, ge=1)
    max_company_size: int = Field(default=1000, ge=1)


class LeadRawInput(BaseModel):
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""
    title: Optional[str] = ""
    company: Optional[str] = ""
    domain: Optional[str] = ""
    email: Optional[str] = ""
    phone: Optional[str] = ""
    linkedin_url: Optional[str] = ""
    industry: Optional[str] = ""
    company_size: Optional[Any] = 0
    city: Optional[str] = ""
    country: Optional[str] = ""


class ProcessRequest(BaseModel):
    filename: Optional[str] = "input_leads.csv"
    leads: List[LeadRawInput]
    icp_config: Optional[ICPConfigRequest] = ICPConfigRequest()


class LeadResponse(BaseModel):
    id: int
    batch_id: int
    first_name: str
    last_name: str
    title: str
    company: str
    domain: str
    email: str
    phone: str
    linkedin_url: str
    industry: str
    company_size: int
    city: str
    country: str
    is_duplicate: bool
    primary_lead_id: Optional[int]
    duplicate_reason: str
    dedup_cluster_id: str
    is_valid_email: bool
    is_role_based_email: bool
    is_valid_domain: bool
    data_quality_score: int
    quality_issues: List[str]
    icp_score: int
    icp_tier: str
    seniority_score: int
    industry_score: int
    size_score: int
    score_rationale: str

    model_config = {"from_attributes": True}


class BatchSummaryResponse(BaseModel):
    id: int
    filename: str
    created_at: datetime
    total_leads: int
    unique_leads: int
    duplicate_leads: int
    high_fit_leads: int
    avg_quality_score: float
    leads: List[LeadResponse] = []

    model_config = {"from_attributes": True}
