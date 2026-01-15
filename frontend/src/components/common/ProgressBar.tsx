import React from 'react';
import { motion } from 'framer-motion';
import './ProgressBar.css';

export interface ProgressBarProps {
    label: string;
    value: number;
    max?: number;
    color?: 'purple' | 'green' | 'red' | 'blue' | 'orange';
    showPercentage?: boolean;
    size?: 'sm' | 'md' | 'lg';
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
    label,
    value,
    max = 100,
    color = 'purple',
    showPercentage = true,
    size = 'md',
}) => {
    const percentage = Math.min((value / max) * 100, 100);

    return (
        <div className={`progress-bar-container progress-bar-${size}`}>
            <div className="progress-bar-header">
                <span className="progress-bar-label">{label}</span>
                {showPercentage && (
                    <span className="progress-bar-percentage">{Math.round(percentage)}%</span>
                )}
            </div>

            <div className="progress-bar-track">
                <motion.div
                    className={`progress-bar-fill progress-bar-fill-${color}`}
                    initial={{ width: 0 }}
                    animate={{ width: `${percentage}%` }}
                    transition={{ duration: 0.8, ease: 'easeOut' }}
                />
            </div>
        </div>
    );
};

export default ProgressBar;
