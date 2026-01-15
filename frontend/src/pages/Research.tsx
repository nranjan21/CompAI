import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { apiService } from '../services/api';
import type { ResearchStatus } from '../types';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import './Research.css';

// Define research tasks with descriptions
const RESEARCH_TASKS = [
    {
        id: 'profile',
        title: 'Confirming company identity',
        subtitle: 'Validating ticker and basic information',
        threshold: 10,
    },
    {
        id: 'financial',
        title: 'Analyzing SEC filings and financials',
        subtitle: 'So you understand their performance',
        threshold: 30,
    },
    {
        id: 'news',
        title: 'Reading recent news and announcements',
        subtitle: 'Getting the real story from trusted sources',
        threshold: 50,
    },
    {
        id: 'sentiment',
        title: 'Analyzing market sentiment',
        subtitle: 'Beyond the official ratings',
        threshold: 70,
    },
    {
        id: 'competitive',
        title: 'Mapping competitive landscape',
        subtitle: 'That most investors miss',
        threshold: 85,
    },
    {
        id: 'synthesis',
        title: 'Creating your comprehensive report',
        subtitle: 'Everything you need to decide with confidence',
        threshold: 95,
    },
];

export const Research: React.FC = () => {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const [status, setStatus] = useState<ResearchStatus | null>(null);
    const [error, setError] = useState<string | null>(null);
    const hasInitiatedRef = React.useRef(false);

    const companyName = searchParams.get('company');
    const ticker = searchParams.get('ticker');

    useEffect(() => {
        if (!companyName) {
            navigate('/');
            return;
        }

        // Only start research once
        if (!hasInitiatedRef.current) {
            hasInitiatedRef.current = true;
            startResearch();
        }
    }, [companyName, ticker, navigate]);

    const startResearch = async () => {
        try {
            setError(null);

            const response = await apiService.createResearch({
                company_name: companyName!,
                ticker: ticker || undefined,
            });

            // Check if this is an existing or cached job
            if (response.existing) {
                if (response.cached) {
                    console.log('Using cached research result');
                } else {
                    console.log('Research already in progress for this company');
                }
            }

            pollStatus(response.job_id);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to start research');
        }
    };

    const pollStatus = async (id: string) => {
        try {
            const statusData = await apiService.getResearchStatus(id);
            setStatus(statusData);

            if (statusData.status === 'completed' && statusData.report_id) {
                setTimeout(() => {
                    navigate(`/report/${statusData.report_id}`);
                }, 1500);
            } else if (statusData.status === 'failed') {
                setError(statusData.error || 'Research failed');
            } else if (statusData.status === 'pending' || statusData.status === 'running') {
                setTimeout(() => pollStatus(id), 2000);
            }
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to get research status');
        }
    };

    const formatTimeRemaining = (status: ResearchStatus | null): string => {
        if (!status) return '0:00';

        // Use backend's estimate if available, otherwise fall back to client-side calculation
        const totalSeconds = status.estimated_time_remaining_seconds !== undefined
            ? status.estimated_time_remaining_seconds
            : Math.max(0, Math.ceil((100 - status.progress) * 1.5)); // Rough estimate

        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        return `${minutes}:${seconds.toString().padStart(2, '0')}`;
    };

    if (error) {
        return (
            <div className="research-page">
                <div className="research-container">
                    <Card className="error-card">
                        <div className="error-icon">❌</div>
                        <h2>Something went wrong</h2>
                        <p>{error}</p>
                        <Button onClick={() => navigate('/')}>
                            Go Back Home
                        </Button>
                    </Card>
                </div>
            </div>
        );
    }

    return (
        <div className="research-page">
            <div className="research-container">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                >
                    {/* Company Info Card */}
                    <Card className="company-info-card">
                        <p className="info-label">You're researching:</p>
                        <div className="company-display">
                            <div className="company-icon">🏢</div>
                            <h2 className="company-name">{companyName}</h2>
                        </div>
                    </Card>

                    {/* Progress Card */}
                    <Card className="progress-card">
                        <h3 className="progress-heading">Research Progress</h3>
                        <div className="progress-percentage">{status?.progress || 0}%</div>

                        <div className="progress-bar-container">
                            <div className="progress-bar-bg">
                                <motion.div
                                    className="progress-bar-fill"
                                    initial={{ width: 0 }}
                                    animate={{ width: `${status?.progress || 0}%` }}
                                    transition={{ duration: 0.5, ease: 'easeOut' }}
                                />
                            </div>
                        </div>

                        <p className="time-estimate">
                            Estimated time remaining: {formatTimeRemaining(status)}
                        </p>
                    </Card>

                    {/* Tasks List */}
                    <Card className="tasks-card">
                        <div className="tasks-list">
                            {RESEARCH_TASKS.map((task, index) => {
                                const isComplete = (status?.progress || 0) >= task.threshold;
                                const isActive =
                                    (status?.progress || 0) >= (index > 0 ? RESEARCH_TASKS[index - 1].threshold : 0) &&
                                    (status?.progress || 0) < task.threshold;

                                return (
                                    <motion.div
                                        key={task.id}
                                        className={`task-item ${isComplete ? 'complete' : ''} ${isActive ? 'active' : ''}`}
                                        initial={{ opacity: 0, x: -20 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        transition={{ duration: 0.3, delay: index * 0.1 }}
                                    >
                                        <div className="task-icon">
                                            {isComplete ? (
                                                <svg className="checkmark" viewBox="0 0 24 24" fill="none">
                                                    <circle cx="12" cy="12" r="10" fill="#10B981" />
                                                    <path
                                                        d="M8 12l2 2 4-4"
                                                        stroke="white"
                                                        strokeWidth="2"
                                                        strokeLinecap="round"
                                                        strokeLinejoin="round"
                                                    />
                                                </svg>
                                            ) : (
                                                <div className={`circle ${isActive ? 'pulse' : ''}`} />
                                            )}
                                        </div>
                                        <div className="task-content">
                                            <h4 className="task-title">{task.title}</h4>
                                            <p className="task-subtitle">{task.subtitle}</p>
                                        </div>
                                    </motion.div>
                                );
                            })}
                        </div>
                    </Card>
                </motion.div>
            </div>
        </div>
    );
};

export default Research;
