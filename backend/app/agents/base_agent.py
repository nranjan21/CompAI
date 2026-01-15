"""
Base Agent class that all research agents inherit from.
Provides common functionality for workflow orchestration, caching, and error handling.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from datetime import datetime
from app.core.llm_manager import get_llm_manager
from app.utils.logger import logger
from app.utils.cache_manager import get_cache_manager


class BaseAgent(ABC):
    """
    Abstract base class for all research agents.
    
    Provides:
    - LLM integration
    - Caching
    - Logging
    - Error handling
    - Progress tracking
    """
    
    def __init__(self, name: str, use_cache: bool = True):
        """
        Initialize base agent.
        
        Args:
            name: Agent name (for logging and caching)
            use_cache: Whether to use caching
        """
        self.name = name
        self.use_cache = use_cache
        self.llm_manager = get_llm_manager()
        self.cache_manager = get_cache_manager() if use_cache else None
        self.current_step = 0
        self.total_steps = 0
        self.errors: List[str] = []
        
        logger.info(f"🤖 Initialized {self.name}")
    
    def _log_step(self, step_name: str):
        """Log the current step of execution."""
        self.current_step += 1
        logger.info(f"[{self.name}] Step {self.current_step}/{self.total_steps}: {step_name}")
    
    def _add_error(self, error: str):
        """Add an error to the error list."""
        self.errors.append(error)
        logger.error(f"[{self.name}] ❌ {error}")
    
    def _generate_cache_key(self, *args, **kwargs) -> str:
        """
        Generate a cache key for the agent's execution.
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Cache key string
        """
        import hashlib
        import json
        
        key_data = {
            "agent": self.name,
            "args": args,
            "kwargs": kwargs
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _llm_generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2048) -> Optional[str]:
        """
        Generate text using LLM with error handling.
        
        Args:
            prompt: Prompt for the LLM
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text or None if failed
        """
        try:
            result = self.llm_manager.generate(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            if result.get("success"):
                return result.get("text")
            else:
                error_msg = result.get("error", "Unknown LLM error")
                self._add_error(f"LLM generation failed: {error_msg}")
                return None
        except Exception as e:
            self._add_error(f"LLM exception: {str(e)}")
            return None
    
    def _execute_with_cache(self, cache_key: str, execute_fn, ttl_hours: Optional[int] = 24) -> Any:
        """
        Execute a function with caching support.
        
        Args:
            cache_key: Cache key
            execute_fn: Function to execute if cache miss
            ttl_hours: Cache TTL in hours
            
        Returns:
            Result from cache or execution
        """
        if not self.use_cache or self.cache_manager is None:
            return execute_fn()
        
        # Try to get from cache
        cached_result = self.cache_manager.get(cache_key, ttl_hours)
        
        if cached_result is not None:
            logger.info(f"[{self.name}] 📦 Using cached result")
            return cached_result
        
        # Execute and cache
        result = execute_fn()
        
        if result is not None:
            self.cache_manager.set(cache_key, result)
        
        return result
    
    @abstractmethod
    def execute(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Execute the agent's workflow.
        
        This method must be implemented by all subclasses.
        
        Returns:
            Dictionary containing agent results
        """
        pass
    
    def run(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Run the agent with error handling and metadata.
        
        Args:
            *args: Positional arguments for execute()
            **kwargs: Keyword arguments for execute()
            
        Returns:
            Dictionary with results and metadata
        """
        start_time = datetime.now()
        self.errors = []
        
        logger.info(f"🚀 Starting {self.name}")
        
        try:
            result = self.execute(*args, **kwargs)
            
            # Add metadata
            result["_metadata"] = {
                "agent": self.name,
                "timestamp": start_time.isoformat(),
                "duration_seconds": (datetime.now() - start_time).total_seconds(),
                "errors": self.errors,
                "success": len(self.errors) == 0
            }
            
            logger.info(f"✅ {self.name} completed successfully")
            return result
            
        except Exception as e:
            self._add_error(f"Fatal error: {str(e)}")
            logger.exception(f"💥 {self.name} failed with exception")
            
            return {
                "_metadata": {
                    "agent": self.name,
                    "timestamp": start_time.isoformat(),
                    "duration_seconds": (datetime.now() - start_time).total_seconds(),
                    "errors": self.errors,
                    "success": False
                }
            }
