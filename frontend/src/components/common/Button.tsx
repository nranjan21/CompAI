import React from 'react';
import { motion } from 'framer-motion';
import './Button.css';

export interface ButtonProps {
    variant?: 'primary' | 'secondary' | 'icon' | 'ghost';
    size?: 'sm' | 'md' | 'lg';
    icon?: React.ReactNode;
    loading?: boolean;
    children?: React.ReactNode;
    onClick?: () => void;
    type?: 'button' | 'submit' | 'reset';
    disabled?: boolean;
    className?: string;
}

export const Button: React.FC<ButtonProps> = ({
    variant = 'primary',
    size = 'md',
    icon,
    loading = false,
    disabled,
    children,
    className = '',
    onClick,
    type = 'button',
}) => {
    const classes = [
        'btn',
        `btn-${variant}`,
        `btn-${size}`,
        loading && 'btn-loading',
        className,
    ]
        .filter(Boolean)
        .join(' ');

    return (
        <motion.button
            className={classes}
            disabled={disabled || loading}
            onClick={onClick}
            type={type}
            whileHover={{ scale: disabled || loading ? 1 : 1.02 }}
            whileTap={{ scale: disabled || loading ? 1 : 0.98 }}
            transition={{ duration: 0.2 }}
        >
            {loading ? (
                <span className="btn-spinner" />
            ) : (
                <>
                    {icon && <span className="btn-icon">{icon}</span>}
                    {children && <span className="btn-text">{children}</span>}
                </>
            )}
        </motion.button>
    );
};

export default Button;
