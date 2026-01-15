/**
 * TypeScript Type Definitions
 */

export interface ResearchRequest {
    company_name: string;
    ticker?: string;
}

export interface ResearchResponse {
    job_id: string;
    status: string;
    message: string;
    existing?: boolean;  // True if returning existing job
    cached?: boolean;    // True if returning cached result
}

export interface ResearchStatus {
    job_id: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    progress: number; // 0-100
    current_agent?: string;
    company_name: string;
    ticker?: string;
    created_at: string;
    started_at?: string;
    completed_at?: string;
    estimated_time_remaining_seconds?: number;
    error?: string;
    report_id?: string;
}

export interface ReportSummary {
    report_id: string;
    company_name: string;
    ticker?: string;
    created_at: string;
    file_path: string;
}

export interface ReportDetail {
    report_id: string;
    company_name: string;
    ticker?: string;
    created_at: string;
    content: string; // Markdown content
    file_path: string;
}

export interface ApiError {
    detail: string;
}
