import React from 'react';
import './Loading.css';

export interface LoadingProps {
    size?: 'sm' | 'md' | 'lg';
    text?: string;
}

export const Loading: React.FC<LoadingProps> = ({ size = 'md', text }) => {
    return (
        <div className="loading-container">
            <div className={`loading-spinner loading-spinner-${size}`} />
            {text && <p className="loading-text">{text}</p>}
        </div>
    );
};

export default Loading;
