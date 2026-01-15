import uuid
from datetime import datetime
from pathlib import Path
from typing import List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from app.schemas.research import (
    ResearchRequest, 
    ResearchResponse, 
    ResearchStatus, 
    ReportSummary, 
    ReportDetail
)
from app.services.research_service import (
    research_jobs, 
    reports_storage, 
    run_research_job,
    find_existing_job
)

router = APIRouter()

@router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@router.post("/research", response_model=ResearchResponse)
async def create_research(request: ResearchRequest, background_tasks: BackgroundTasks):
    """Create a new research job or return existing one."""
    
    # Check for existing job for this company
    existing = find_existing_job(request.company_name)
    
    if existing:
        job_id = existing['job_id']
        status = existing['status']
        
        if status == 'running':
            # Return existing running job
            return ResearchResponse(
                job_id=job_id,
                status="running",
                message=f"Research already in progress for {request.company_name}",
                existing=True
            )
        elif existing.get('cached'):
            # Return cached completed job
            return ResearchResponse(
                job_id=job_id,
                status="completed",
                message=f"Using recent research for {request.company_name}",
                existing=True,
                cached=True
            )
    
    # No existing job found, create new one
    job_id = str(uuid.uuid4())
    
    research_jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "progress": 0,
        "current_agent": None,
        "company_name": request.company_name,
        "ticker": request.ticker,
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "error": None
    }
    
    background_tasks.add_task(run_research_job, job_id, request.company_name, request.ticker)
    
    return ResearchResponse(
        job_id=job_id,
        status="pending",
        message=f"Research job created for {request.company_name}"
    )

@router.get("/research/{job_id}", response_model=ResearchStatus)
async def get_research_status(job_id: str):
    if job_id not in research_jobs:
        raise HTTPException(status_code=404, detail="Research job not found")
    return ResearchStatus(**research_jobs[job_id])

@router.get("/reports", response_model=List[ReportSummary])
async def list_reports():
    summaries = [
        ReportSummary(
            report_id=report["report_id"],
            company_name=report["company_name"],
            ticker=report["ticker"],
            created_at=report["created_at"],
            file_path=report["file_path"]
        )
        for report in reports_storage.values()
    ]
    return sorted(summaries, key=lambda x: x.created_at, reverse=True)

@router.get("/reports/{report_id}", response_model=ReportDetail)
async def get_report(report_id: str):
    if report_id not in reports_storage:
        raise HTTPException(status_code=404, detail="Report not found")
    return ReportDetail(**reports_storage[report_id])

@router.delete("/reports/{report_id}")
async def delete_report(report_id: str):
    if report_id not in reports_storage:
        raise HTTPException(status_code=404, detail="Report not found")
    del reports_storage[report_id]
    return {"message": "Report deleted successfully"}

@router.get("/reports/{report_id}/download")
async def download_report(report_id: str):
    if report_id not in reports_storage:
        raise HTTPException(status_code=404, detail="Report not found")
    
    report = reports_storage[report_id]
    file_path = Path(report["file_path"])
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Report file not found")
    
    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type="text/markdown"
    )
