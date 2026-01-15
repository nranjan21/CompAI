import React from 'react';
import './MiniBarChart.css';

export interface MiniBarChartProps {
    data: number[];
    labels?: string[];
    height?: number;
    color?: 'purple' | 'green' | 'blue';
    showValues?: boolean;
}

export const MiniBarChart: React.FC<MiniBarChartProps> = ({
    data,
    labels,
    height = 120,
    color = 'purple',
    showValues = false,
}) => {
    const max = Math.max(...data);

    return (
        <div className="mini-bar-chart" style={{ height: `${height}px` }}>
            <div className="chart-bars">
                {data.map((value, index) => {
                    const barHeight = (value / max) * 100;

                    return (
                        <div key={index} className="chart-bar-wrapper">
                            {showValues && <div className="chart-value">{value}</div>}
                            <div className="chart-bar-container">
                                <div
                                    className={`chart-bar chart-bar-${color}`}
                                    style={{ height: `${barHeight}%` }}
                                    title={`${labels?.[index] || index}: ${value}`}
                                />
                            </div>
                            {labels?.[index] && (
                                <div className="chart-label">{labels[index]}</div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default MiniBarChart;
