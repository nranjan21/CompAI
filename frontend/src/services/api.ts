/**
 * API Service
 * Centralized API client for backend communication
 */

import axios, { type AxiosInstance, AxiosError } from 'axios';
import type {
    ResearchRequest,
    ResearchResponse,
    ResearchStatus,
    ReportSummary,
    ReportDetail,
    ApiError,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiService {
    private client: AxiosInstance;

    constructor() {
        this.client = axios.create({
            baseURL: API_BASE_URL,
            headers: {
                'Content-Type': 'application/json',
            },
            timeout: 30000, // 30 seconds
        });

        // Request interceptor
        this.client.interceptors.request.use(
            (config) => {
                console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
                return config;
            },
            (error) => {
                return Promise.reject(error);
            }
        );

        // Response interceptor
        this.client.interceptors.response.use(
            (response) => {
                console.log(`[API] Response:`, response.status, response.data);
                return response;
            },
            (error: AxiosError<ApiError>) => {
                console.error('[API] Error:', error.response?.data || error.message);
                return Promise.reject(error);
            }
        );
    }

    /**
     * Health check
     */
    async healthCheck(): Promise<{ status: string; service: string; version: string }> {
        const response = await this.client.get('/');
        return response.data;
    }

    /**
     * Submit a new research request
     */
    async createResearch(data: ResearchRequest): Promise<ResearchResponse> {
        const response = await this.client.post<ResearchResponse>('/api/research', data);
        return response.data;
    }

    /**
     * Get research job status
     */
    async getResearchStatus(jobId: string): Promise<ResearchStatus> {
        const response = await this.client.get<ResearchStatus>(`/api/research/${jobId}`);
        return response.data;
    }

    /**
     * List all reports
     */
    async listReports(): Promise<ReportSummary[]> {
        const response = await this.client.get<ReportSummary[]>('/api/reports');
        return response.data;
    }

    /**
     * Get a specific report
     */
    async getReport(reportId: string): Promise<ReportDetail> {
        const response = await this.client.get<ReportDetail>(`/api/reports/${reportId}`);
        return response.data;
    }

    /**
     * Delete a report
     */
    async deleteReport(reportId: string): Promise<{ message: string }> {
        const response = await this.client.delete(`/api/reports/${reportId}`);
        return response.data;
    }

    /**
     * Get download URL for a report
     */
    getReportDownloadUrl(reportId: string): string {
        return `${API_BASE_URL}/api/reports/${reportId}/download`;
    }
}

// Export singleton instance
export const apiService = new ApiService();
export default apiService;
