import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { apiService } from '../services/api';
import type { ReportSummary } from '../types';
import Loading from '../components/common/Loading';
import Card from '../components/common/Card';
import './History.css';

export const History: React.FC = () => {
    const navigate = useNavigate();
    const [reports, setReports] = useState<ReportSummary[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchReports();
    }, []);

    const fetchReports = async () => {
        try {
            setLoading(true);
            setError(null);
            const data = await apiService.listReports();
            setReports(data);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load reports');
        } finally {
            setLoading(false);
        }
    };

    const handleViewReport = (reportId: string) => {
        navigate(`/report/${reportId}`);
    };

    if (loading) {
        return (
            <div className="history-page">
                <div className="container">
                    <Loading size="lg" text="Loading reports..." />
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="history-page">
                <div className="container">
                    <Card className="error-card">
                        <h2>❌ Error</h2>
                        <p>{error}</p>
                    </Card>
                </div>
            </div>
        );
    }

    return (
        <div className="history-page">
            <div className="container">
                <motion.div
                    className="history-content"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                >
                    <h1 className="history-title">Research History</h1>

                    {reports.length === 0 ? (
                        <Card className="empty-state">
                            <h2>📊 No Reports Yet</h2>
                            <p>Start your first company research to see reports here.</p>
                        </Card>
                    ) : (
                        <div className="reports-grid">
                            {reports.map((report, index) => (
                                <motion.div
                                    key={report.report_id}
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.3, delay: index * 0.1 }}
                                >
                                    <Card
                                        variant="default"
                                        hover
                                        onClick={() => handleViewReport(report.report_id)}
                                        className="report-card-item"
                                    >
                                        <h3 className="report-card-company">{report.company_name}</h3>
                                        {report.ticker && (
                                            <span className="report-card-ticker">{report.ticker}</span>
                                        )}
                                        <p className="report-card-date">
                                            {new Date(report.created_at).toLocaleDateString('en-US', {
                                                year: 'numeric',
                                                month: 'long',
                                                day: 'numeric',
                                            })}
                                        </p>
                                    </Card>
                                </motion.div>
                            ))}
                        </div>
                    )}
                </motion.div>
            </div>
        </div>
    );
};

export default History;
