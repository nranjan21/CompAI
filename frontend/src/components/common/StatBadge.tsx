import React from 'react';
import './StatBadge.css';

export interface StatBadgeProps {
    label: string;
    value: string | number;
    color?: 'purple' | 'green' | 'red' | 'blue' | 'orange' | 'gray';
    icon?: string;
}

export const StatBadge: React.FC<StatBadgeProps> = ({
    label,
    value,
    color = 'purple',
    icon,
}) => {
    return (
        <div className={`stat-badge stat-badge-${color}`}>
            {icon && <span className="stat-badge-icon">{icon}</span>}
            <div className="stat-badge-content">
                <div className="stat-badge-value">{value}</div>
                <div className="stat-badge-label">{label}</div>
            </div>
        </div>
    );
};

export default StatBadge;
