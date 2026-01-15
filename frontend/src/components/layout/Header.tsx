import React from 'react';
import { Link } from 'react-router-dom';
import './Header.css';

export const Header: React.FC = () => {
    return (
        <header className="header">
            <div className="container">
                <div className="header-content">
                    <Link to="/" className="header-logo">
                        <span className="logo-text">Comp</span>
                        <span className="logo-accent text-accent">AI</span>
                    </Link>

                    <nav className="header-nav hide-mobile">
                        <Link to="/" className="nav-link">Home</Link>
                        <Link to="/history" className="nav-link">History</Link>
                    </nav>
                </div>
            </div>
        </header>
    );
};

export default Header;
