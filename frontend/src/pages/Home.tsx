import React from 'react';
import Hero from '../components/sections/Hero';
import './Home.css';

export const Home: React.FC = () => {
    return (
        <div className="home">
            <Hero />

            {/* How It Works Section */}
            <section className="section section-dark">
                <div className="container">
                    <h2 className="section-title text-center">
                        Before you invest, know the <span className="text-accent">why</span>
                    </h2>

                    <p className="section-subtitle text-center">
                        Every detail, laid bare by AI. Purpose, pros, and cons—delivered without bias.
                    </p>

                    <div className="grid-3 mt-3xl">
                        <div className="feature-card">
                            <div className="feature-icon">📊</div>
                            <h3>Multi-Source Research</h3>
                            <p>Analyzes SEC filings, news, social sentiment, and competitive landscape</p>
                        </div>

                        <div className="feature-card">
                            <div className="feature-icon">🧠</div>
                            <h3>AI-Powered Synthesis</h3>
                            <p>Connects insights across domains to surface non-obvious patterns</p>
                        </div>

                        <div className="feature-card">
                            <div className="feature-icon">📝</div>
                            <h3>Comprehensive Reports</h3>
                            <p>Structured markdown reports with executive summaries and key observations</p>
                        </div>
                    </div>
                </div>
            </section>

            {/* Features Section */}
            <section className="section">
                <div className="container">
                    <h2 className="section-title text-center">
                        <span className="text-accent">CompAI</span> in action
                    </h2>

                    <div className="grid-2 mt-3xl">
                        <div className="action-item">
                            <h3>🔍 Company Profile</h3>
                            <p>Discovers and validates company identity, extracts basic profile information</p>
                        </div>

                        <div className="action-item">
                            <h3>💰 Financial Analysis</h3>
                            <p>Analyzes SEC filings, revenue trends, and balance sheet strength</p>
                        </div>

                        <div className="action-item">
                            <h3>📰 News Intelligence</h3>
                            <p>Categorizes major events from news coverage and media mentions</p>
                        </div>

                        <div className="action-item">
                            <h3>💬 Sentiment Analysis</h3>
                            <p>Analyzes customer, employee, and investor sentiment from social media</p>
                        </div>

                        <div className="action-item">
                            <h3>🎯 Competitive Intelligence</h3>
                            <p>Maps competitive landscape and market positioning</p>
                        </div>

                        <div className="action-item">
                            <h3>✨ Insight Synthesis</h3>
                            <p>Generates cross-domain insights and identifies contradictions</p>
                        </div>
                    </div>
                </div>
            </section>
        </div>
    );
};

export default Home;
