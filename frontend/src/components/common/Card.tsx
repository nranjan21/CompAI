import React from 'react';
import { motion } from 'framer-motion';
import './Card.css';

export interface CardProps {
    variant?: 'default' | 'glass' | 'dark';
    hover?: boolean;
    children: React.ReactNode;
    className?: string;
    onClick?: () => void;
}

export const Card: React.FC<CardProps> = ({
    variant = 'default',
    hover = false,
    children,
    className = '',
    onClick,
}) => {
    const classes = [
        'card',
        `card-${variant}`,
        hover && 'card-hover',
        onClick && 'card-clickable',
        className,
    ]
        .filter(Boolean)
        .join(' ');

    const MotionCard = motion.div;

    return (
        <MotionCard
            className={classes}
            onClick={onClick}
            whileHover={hover ? { y: -4, scale: 1.02 } : {}}
            transition={{ duration: 0.3 }}
        >
            {children}
        </MotionCard>
    );
};

export default Card;
