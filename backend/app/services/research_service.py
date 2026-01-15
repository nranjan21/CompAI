import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
from app.agents.orchestrator import OrchestratorAgent
from app.synthesis.insight_synthesizer import InsightSynthesizer
from app.reporting.report_generator import ReportGenerator
from app.utils.logger import logger

# In-memory storage (replace with database for production)
research_jobs: Dict[str, Dict[str, Any]] = {}
reports_storage: Dict[str, Dict[str, Any]] = {}

def find_existing_job(company_name: str) -> Optional[Dict[str, Any]]:
    """
    Check if there's an existing job for this company.
    
    Returns:
        Existing job dict if found, None otherwise
    """
    company_name_lower = company_name.lower().strip()
    
    for job_id, job in research_jobs.items():
        job_company = job.get('company_name', '').lower().strip()
        
        if job_company == company_name_lower:
            status = job.get('status')
            
            # If job is running, return it
            if status == 'running':
                logger.info(f"Found running job for {company_name}: {job_id}")
                return {'job_id': job_id, 'status': 'running', 'existing': True}
            
            # If job completed recently (within 1 hour), return it
            if status == 'completed':
                completed_at_str = job.get('completed_at')
                if completed_at_str:
                    completed_at = datetime.fromisoformat(completed_at_str)
                    age_minutes = (datetime.now() - completed_at).total_seconds() / 60
                    
                    if age_minutes < 60:  # Within 1 hour
                        logger.info(f"Found recent completed job for {company_name}: {job_id} ({age_minutes:.1f} min ago)")
                        return {'job_id': job_id, 'status': 'completed', 'existing': True, 'cached': True}
    
    return None


def run_research_job(job_id: str, company_name: str, ticker: Optional[str]):
    """Execute research job and update status"""
    try:
        start_time = datetime.now()
        research_jobs[job_id]["status"] = "running"
        research_jobs[job_id]["progress"] = 0
        research_jobs[job_id]["started_at"] = start_time.isoformat()
        
        # Define progress callback to update job status
        def progress_callback(agent_name: str, progress: int):
            """Update job progress and calculate time estimate."""
            research_jobs[job_id]["current_agent"] = agent_name
            research_jobs[job_id]["progress"] = progress
            
            # Calculate estimated time remaining
            if progress > 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                estimated_total = (elapsed / progress) * 100
                remaining = max(0, estimated_total - elapsed)
                research_jobs[job_id]["estimated_time_remaining_seconds"] = int(remaining)
            
            logger.info(f"Job {job_id}: {progress}% - {agent_name}")
        
        # Initialize components
        orchestrator = OrchestratorAgent()
        synthesizer = InsightSynthesizer()
        report_generator = ReportGenerator()
        
        # Step 1: Conduct research with progress callback
        research_results = orchestrator.conduct_research(
            company_name=company_name,
            ticker=ticker,
            parallel=True,
            progress_callback=progress_callback
        )
        
        # Step 2: Synthesize insights
        research_jobs[job_id]["current_agent"] = "Synthesis Engine"
        research_jobs[job_id]["progress"] = 95
        synthesis = synthesizer.synthesize(research_results)
        
        # Step 3: Generate report
        research_jobs[job_id]["current_agent"] = "Report Generator"
        research_jobs[job_id]["progress"] = 98
        report_path = report_generator.generate_report(research_results, synthesis)
        
        # Read report content
        with open(report_path, 'r', encoding='utf-8') as f:
            report_content = f.read()
        
        # Store report
        report_id = str(uuid.uuid4())
        reports_storage[report_id] = {
            "report_id": report_id,
            "company_name": company_name,
            "ticker": ticker,
            "created_at": datetime.now().isoformat(),
            "file_path": str(report_path),
            "content": report_content
        }
        
        # Update job status
        research_jobs[job_id]["status"] = "completed"
        research_jobs[job_id]["progress"] = 100
        research_jobs[job_id]["completed_at"] = datetime.now().isoformat()
        research_jobs[job_id]["report_id"] = report_id
        
        logger.info(f"Research job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Research job {job_id} failed: {e}", exc_info=True)
        research_jobs[job_id]["status"] = "failed"
        research_jobs[job_id]["error"] = str(e)
        research_jobs[job_id]["completed_at"] = datetime.now().isoformat()
