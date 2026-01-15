from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class ResearchRequest(BaseModel):
    company_name: str
    ticker: Optional[str] = None

class ResearchResponse(BaseModel):
    job_id: str
    status: str
    message: str
    existing: Optional[bool] = False  # True if returning existing job
    cached: Optional[bool] = False    # True if returning cached result

class ResearchStatus(BaseModel):
    job_id: str
    status: str  # "pending", "running", "completed", "failed"
    progress: int  # 0-100
    current_agent: Optional[str] = None
    company_name: str
    ticker: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    estimated_time_remaining_seconds: Optional[int] = None
    error: Optional[str] = None
    report_id: Optional[str] = None

class ReportSummary(BaseModel):
    report_id: str
    company_name: str
    ticker: Optional[str] = None
    created_at: str
    file_path: str

class ReportDetail(BaseModel):
    report_id: str
    company_name: str
    ticker: Optional[str] = None
    created_at: str
    content: str  # Markdown content
    file_path: str
