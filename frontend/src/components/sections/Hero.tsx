import React from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import Input from '../common/Input';
import './Hero.css';

export const Hero: React.FC = () => {
    const navigate = useNavigate();

    const handleSearch = (companyName: string) => {
        navigate(`/research?company=${encodeURIComponent(companyName)}`);
    };

    return (
        <section className="hero section gradient-radial">
            <div className="container">
                <div className="hero-content">
                    <motion.h1
                        className="hero-title"
                        initial={{ opacity: 0, y: 30 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.6 }}
                    >
                        Ask <span className="text-accent">CompAI</span>
                    </motion.h1>

                    <motion.p
                        className="hero-subtitle"
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.6, delay: 0.2 }}
                    >
                        Deep company analysis in minutes
                    </motion.p>

                    <motion.div
                        className="hero-search"
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.6, delay: 0.4 }}
                    >
                        <Input
                            variant="hero"
                            size="hero"
                            placeholder="Enter a company name to analyze..."
                            showSubmitButton
                            onSearchSubmit={handleSearch}
                        />
                    </motion.div>

                    <motion.div
                        className="hero-examples"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ duration: 0.6, delay: 0.6 }}
                    >
                        <p className="examples-label">Try:</p>
                        <button
                            className="example-btn"
                            onClick={() => handleSearch('Apple Inc')}
                        >
                            Apple Inc
                        </button>
                        <button
                            className="example-btn"
                            onClick={() => handleSearch('Tesla')}
                        >
                            Tesla
                        </button>
                        <button
                            className="example-btn"
                            onClick={() => handleSearch('Microsoft')}
                        >
                            Microsoft
                        </button>
                    </motion.div>

                    <motion.div
                        className="hero-scroll-indicator"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ duration: 0.6, delay: 0.8 }}
                    >
                        <svg
                            width="24"
                            height="24"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                        >
                            <path d="M12 5v14M19 12l-7 7-7-7" />
                        </svg>
                    </motion.div>
                </div>
            </div>
        </section>
    );
};

export default Hero;
