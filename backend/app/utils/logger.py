"""
Logging utility for the Deep Research Agent.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from app.core.config import config

def setup_logger(name: str = "research_agent") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, config.system.log_level.upper() if hasattr(config.system, 'log_level') else "INFO"))
    
    if logger.handlers:
        return logger
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"research_agent_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logger()
