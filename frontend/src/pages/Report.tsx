import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { apiService } from '../services/api';
import type { ReportDetail } from '../types';
import Loading from '../components/common/Loading';
import Button from '../components/common/Button';
import Card from '../components/common/Card';
import './Report.css';

// Improved markdown to HTML converter
const parseMarkdown = (text: string): string => {
    let html = text;

    // Base URL for images served from backend
    const API_BASE = 'http://localhost:8000';

    // Headers
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

    // Images (![alt](url)) - handle local paths by prefixing API_BASE
    html = html.replace(/!\[(.*?)\]\((.*?)\)/g, (match, alt, url) => {
        let finalUrl = url;
        if (url.startsWith('reports/') || url.startsWith('reports\\')) {
            finalUrl = `${API_BASE}/${url.replace(/\\/g, '/')}`;
        }
        return `<div class="report-image-container">
            <img src="${finalUrl}" alt="${alt}" class="report-image" />
            <p class="image-caption">${alt}</p>
        </div>`;
    });

    // Links ([text](url)) - truncate long URLs in text or messy titles
    html = html.replace(/\[(.*?)\]\((.*?)\)/g, (match, text, url) => {
        let displayedText = text;
        if (text.length > 80) {
            displayedText = text.substring(0, 77) + '...';
        }
        return `<a href="${url}" target="_blank" rel="noopener noreferrer">${displayedText}</a>`;
    });

    // Bold and italic
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

    // Lists
    const lines = html.split('\n');
    let inList = false;
    const processed: string[] = [];

    for (const line of lines) {
        const trimmed = line.trim();

        if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
            if (!inList) {
                processed.push('<ul>');
                inList = true;
            }
            // Inner links/bold might still need processing if not caught by global regexes
            processed.push(`<li>${trimmed.substring(2)}</li>`);
        } else {
            if (inList) {
                processed.push('</ul>');
                inList = false;
            }
            if (trimmed) {
                // If the line is already a tag (like image div), don't wrap in p
                if (trimmed.startsWith('<div') || trimmed.startsWith('<h')) {
                    processed.push(line);
                } else {
                    processed.push(`<p>${line}</p>`);
                }
            }
        }
    }

    if (inList) processed.push('</ul>');

    return processed.join('\n');
};

// Parse sections from markdown
interface Section {
    id: string;
    title: string;
    body: string;
}

const parseSections = (content: string): Section[] => {
    // Split by any header level to find the first real section
    const headerMatches = content.match(/^#+ .+/gm);
    if (!headerMatches) return [];

    // Split content by H2 headers primarily for tabs
    const sections = content.split(/(?=^## )/gm);

    return sections.map((section, index) => {
        const lines = section.trim().split('\n');
        const titleLine = lines.find(line => line.startsWith('##')) || lines.find(line => line.startsWith('#'));

        let title = titleLine
            ? titleLine.replace(/^#+\s*/, '').replace(/\*\*/g, '').trim()
            : '';

        const body = lines.filter(line => !line.startsWith('#')).join('\n').trim();

        // Fallback title if empty
        if (!title && body) title = `Section ${index + 1}`;

        return {
            id: title.toLowerCase().replace(/[^a-z0-9]+/g, '-') || `section-${index}`,
            title,
            body
        };
    }).filter(section => section.body.length > 10 && section.title); // Filter out very short or untitled sections
};


export const Report: React.FC = () => {
    const { reportId } = useParams<{ reportId: string }>();
    const navigate = useNavigate();
    const [report, setReport] = useState<ReportDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<string>('overview');

    useEffect(() => {
        if (reportId) {
            fetchReport();
        }
    }, [reportId]);

    const fetchReport = async () => {
        try {
            setLoading(true);
            setError(null);
            const data = await apiService.getReport(reportId!);
            setReport(data);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load report');
        } finally {
            setLoading(false);
        }
    };

    const handleDownload = () => {
        if (reportId) {
            const url = apiService.getReportDownloadUrl(reportId);
            window.open(url, '_blank');
        }
    };

    if (loading) {
        return (
            <div className="report-page">
                <div className="report-container-wide">
                    <Loading size="lg" text="Loading report..." />
                </div>
            </div>
        );
    }

    if (error || !report) {
        return (
            <div className="report-page">
                <div className="report-container-wide">
                    <Card className="error-card">
                        <div className="error-icon">📄</div>
                        <h2>Report not found</h2>
                        <p>{error || 'The report you\'re looking for doesn\'t exist.'}</p>
                        <Button onClick={() => navigate('/')}>Go Back Home</Button>
                    </Card>
                </div>
            </div>
        );
    }

    const sections = parseSections(report.content);
    const executiveSummary = sections.find(s =>
        s.title.toLowerCase().includes('executive') ||
        s.title.toLowerCase().includes('summary')
    );

    const filteredSections = sections.filter(s => s.id !== executiveSummary?.id);

    return (
        <div className="report-page">
            <div className="report-container-wide">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                >
                    {/* Header */}
                    <div className="report-header-section">
                        <div className="header-content">
                            <h1 className="company-title">{report.company_name}</h1>
                            {report.ticker && <span className="ticker-badge">{report.ticker}</span>}
                        </div>
                        <p className="report-date">
                            Generated {new Date(report.created_at).toLocaleDateString('en-US', {
                                year: 'numeric',
                                month: 'long',
                                day: 'numeric',
                            })}
                        </p>
                    </div>

                    {/* Action Bar */}
                    <div className="action-bar">
                        <Button variant="secondary" onClick={() => navigate('/history')}>
                            View History
                        </Button>
                        <Button onClick={handleDownload}>
                            Download Report
                        </Button>
                    </div>

                    <div className="report-main-layout">
                        {/* Tab Navigation - Sidebar */}
                        <div className="tab-navigation-sidebar">
                            <div className="tab-navigation-vertical">
                                <button
                                    className={`tab-button ${activeTab === 'overview' ? 'active' : ''}`}
                                    onClick={() => setActiveTab('overview')}
                                >
                                    Overview
                                </button>

                                {filteredSections.map((section) => (
                                    <button
                                        key={section.id}
                                        className={`tab-button ${activeTab === section.id ? 'active' : ''}`}
                                        onClick={() => setActiveTab(section.id)}
                                    >
                                        {section.title}
                                    </button>
                                ))}

                                <button
                                    className={`tab-button ${activeTab === 'full' ? 'active' : ''}`}
                                    onClick={() => setActiveTab('full')}
                                >
                                    Full Report
                                </button>
                            </div>
                        </div>

                        {/* Content Area */}
                        <div className="report-content-area">
                            {/* Overview Tab */}
                            {activeTab === 'overview' && (
                                <motion.div
                                    key="overview"
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    transition={{ duration: 0.3 }}
                                    className="tab-content"
                                >
                                    {/* Executive Summary Card */}
                                    {executiveSummary && (
                                        <Card className="summary-card">
                                            <div className="summary-header">
                                                <h2>
                                                    <span className="ai-badge">AI</span>
                                                    Executive Summary
                                                </h2>
                                            </div>
                                            <div
                                                className="summary-content"
                                                dangerouslySetInnerHTML={{ __html: parseMarkdown(executiveSummary.body) }}
                                            />
                                        </Card>
                                    )}
                                </motion.div>
                            )}

                            {/* Section Tabs */}
                            {filteredSections.map((section) =>
                                activeTab === section.id && (
                                    <motion.div
                                        key={section.id}
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        transition={{ duration: 0.3 }}
                                        className="tab-content"
                                    >
                                        <Card className="section-detail-card">
                                            <h2 className="section-detail-title">{section.title}</h2>
                                            <div
                                                className="section-detail-content"
                                                dangerouslySetInnerHTML={{ __html: parseMarkdown(section.body) }}
                                            />
                                        </Card>
                                    </motion.div>
                                )
                            )}

                            {/* Full Report Tab */}
                            {activeTab === 'full' && (
                                <motion.div
                                    key="full"
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    transition={{ duration: 0.3 }}
                                    className="tab-content"
                                >
                                    <Card className="full-report-card">
                                        <div
                                            className="markdown-content"
                                            dangerouslySetInnerHTML={{ __html: parseMarkdown(report.content) }}
                                        />
                                    </Card>
                                </motion.div>
                            )}
                        </div>
                    </div>
                </motion.div>
            </div>
        </div>
    );
};

export default Report;
