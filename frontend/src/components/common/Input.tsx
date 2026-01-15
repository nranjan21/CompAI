import React, { useState } from 'react';
import { motion } from 'framer-motion';
import Button from './Button';
import './Input.css';

export interface InputProps {
    variant?: 'default' | 'glass' | 'hero';
    size?: 'sm' | 'md' | 'lg' | 'hero';
    icon?: React.ReactNode;
    onSearchSubmit?: (value: string) => void;
    showSubmitButton?: boolean;
    submitIcon?: React.ReactNode;
    placeholder?: string;
    value?: string;
    onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
    className?: string;
}

export const Input: React.FC<InputProps> = ({
    variant = 'default',
    size = 'md',
    icon,
    onSearchSubmit,
    showSubmitButton = false,
    submitIcon,
    className = '',
    placeholder,
    value: propValue,
    onChange,
}) => {
    const [value, setValue] = useState(propValue || '');

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (onSearchSubmit && value) {
            onSearchSubmit(value.toString());
        }
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setValue(e.target.value);
        onChange?.(e);
    };

    const containerClasses = [
        'input-container',
        `input-container-${variant}`,
        `input-container-${size}`,
        className,
    ]
        .filter(Boolean)
        .join(' ');

    const inputClasses = [
        'input',
        `input-${variant}`,
        `input-${size}`,
    ]
        .filter(Boolean)
        .join(' ');

    return (
        <motion.form
            className={containerClasses}
            onSubmit={handleSubmit}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
        >
            {icon && <span className="input-icon-left">{icon}</span>}

            <input
                value={value}
                onChange={handleChange}
                className={inputClasses}
                placeholder={placeholder}
            />

            {showSubmitButton && (
                <Button
                    type="submit"
                    variant="icon"
                    size={size === 'hero' ? 'lg' : size === 'lg' ? 'md' : 'sm'}
                    className="input-submit-btn"
                >
                    {submitIcon || (
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
                            <path d="M5 12h14M12 5l7 7-7 7" />
                        </svg>
                    )}
                </Button>
            )}
        </motion.form>
    );
};

export default Input;
