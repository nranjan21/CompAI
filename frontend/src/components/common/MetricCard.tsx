import React from 'react';
import { motion } from 'framer-motion';
import './MetricCard.css';

export interface MetricCardProps {
    label: string;
    value: string | number;
    icon?: string;
    trend?: string;
    trendDirection?: 'up' | 'down' | 'neutral';
    color?: 'purple' | 'green' | 'red' | 'blue' | 'orange';
    size?: 'sm' | 'md' | 'lg';
}

export const MetricCard: React.FC<MetricCardProps> = ({
    label,
    value,
    icon,
    trend,
    trendDirection = 'neutral',
    color = 'purple',
    size = 'md',
}) => {
    return (
        <motion.div
            className={`metric-card metric-card-${size} metric-card-${color}`}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            whileHover={{ y: -4, boxShadow: '0 8px 24px rgba(0,0,0,0.12)' }}
        >
            {icon && <div className="metric-icon">{icon}</div>}

            <div className="metric-content">
                <div className="metric-label">{label}</div>
                <div className="metric-value">{value}</div>

                {trend && (
                    <div className={`metric-trend metric-trend-${trendDirection}`}>
                        {trendDirection === 'up' && '↑'}
                        {trendDirection === 'down' && '↓'}
                        {trendDirection === 'neutral' && '→'}
                        <span>{trend}</span>
                    </div>
                )}
            </div>
        </motion.div>
    );
};

export default MetricCard;
