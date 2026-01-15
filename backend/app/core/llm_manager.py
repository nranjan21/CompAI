"""
LLM Manager with fallback chain logic.
Manages multiple free LLM providers and automatically falls back on failure.
"""

import time
from typing import Optional, Dict, Any, List
from enum import Enum
import google.generativeai as genai
from groq import Groq
from huggingface_hub import InferenceClient
from together import Together
import cohere

from app.core.config import config
from app.utils.logger import logger


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    GEMINI = "gemini"
    GROQ = "groq"
    HUGGINGFACE = "huggingface"
    TOGETHER = "together"
    COHERE = "cohere"


class LLMManager:
    """
    Manages multiple LLM providers with automatic fallback chain.
    """
    
    def __init__(self):
        """Initialize all available LLM providers."""
        self.providers = {}
        self.usage_stats = {provider: {"calls": 0, "failures": 0} for provider in LLMProvider}
        self.last_used = None
        
        # Initialize Gemini
        if config.llm.google_api_key:
            try:
                genai.configure(api_key=config.llm.google_api_key)
                self.providers[LLMProvider.GEMINI] = genai.GenerativeModel('gemini-2.0-flash')
                logger.info("✅ Gemini initialized")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize Gemini: {e}")
        
        # Initialize Groq
        if config.llm.groq_api_key:
            try:
                self.providers[LLMProvider.GROQ] = Groq(api_key=config.llm.groq_api_key)
                logger.info("✅ Groq initialized")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize Groq: {e}")
        
        # Initialize HuggingFace
        if config.llm.huggingface_api_key:
            try:
                self.providers[LLMProvider.HUGGINGFACE] = InferenceClient(
                    token=config.llm.huggingface_api_key
                )
                logger.info("✅ HuggingFace initialized")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize HuggingFace: {e}")
        
        # Initialize Together AI
        if config.llm.together_api_key:
            try:
                self.providers[LLMProvider.TOGETHER] = Together(api_key=config.llm.together_api_key)
                logger.info("✅ Together AI initialized")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize Together AI: {e}")
        
        # Initialize Cohere
        if config.llm.cohere_api_key:
            try:
                self.providers[LLMProvider.COHERE] = cohere.Client(api_key=config.llm.cohere_api_key)
                logger.info("✅ Cohere initialized")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize Cohere: {e}")
        
        if not self.providers:
            logger.error("❌ No LLM providers initialized!")
            raise ValueError("No LLM providers available")
    
    def _call_gemini(self, prompt: str, **kwargs) -> str:
        """Call Gemini with retry logic for transient failures."""
        model_name = 'gemini-2.0-flash'
        max_retries = 2
        delay = 1.0
        
        for attempt in range(1, max_retries + 1):
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                return response.text
            except Exception as e:
                if attempt < max_retries:
                    # Try fallback model on first retry
                    if attempt == 1:
                        try:
                            model = genai.GenerativeModel('gemini-1.5-flash')
                            response = model.generate_content(prompt)
                            return response.text
                        except:
                            pass
                    logger.warning(f"Gemini attempt {attempt}/{max_retries} failed: {e}")
                    time.sleep(delay * attempt)
                else:
                    logger.error(f"Gemini failed after {max_retries} attempts: {e}")
                    raise

    
    def _call_groq(self, prompt: str, **kwargs) -> str:
        """Call Groq with retry logic for transient failures."""
        client = self.providers[LLMProvider.GROQ]
        max_retries = 2
        delay = 1.0
        
        for attempt in range(1, max_retries + 1):
            try:
                chat_completion = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama-3.3-70b-versatile",
                    temperature=kwargs.get("temperature", 0.7),
                    max_tokens=kwargs.get("max_tokens", 2048),
                )
                return chat_completion.choices[0].message.content
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"Groq attempt {attempt}/{max_retries} failed: {e}")
                    time.sleep(delay * attempt)
                else:
                    raise

    
    def _call_huggingface(self, prompt: str, **kwargs) -> str:
        client = self.providers[LLMProvider.HUGGINGFACE]
        response = client.text_generation(
            prompt,
            model="mistralai/Mixtral-8x7B-Instruct-v0.1",
            max_new_tokens=kwargs.get("max_tokens", 2048),
            temperature=kwargs.get("temperature", 0.7),
        )
        return response
    
    def _call_together(self, prompt: str, **kwargs) -> str:
        client = self.providers[LLMProvider.TOGETHER]
        response = client.chat.completions.create(
            model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 2048),
        )
        return response.choices[0].message.content
    
    def _call_cohere(self, prompt: str, **kwargs) -> str:
        """Call Cohere with retry logic for transient failures."""
        client = self.providers[LLMProvider.COHERE]
        max_retries = 2
        delay = 1.0
        
        for attempt in range(1, max_retries + 1):
            try:
                response = client.chat(
                    message=prompt,
                    model="command-r-08-2024",
                    temperature=kwargs.get("temperature", 0.7),
                )
                return response.text
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"Cohere attempt {attempt}/{max_retries} failed: {e}")
                    time.sleep(delay * attempt)
                else:
                    raise

    
    def generate(
        self, 
        prompt: str, 
        temperature: float = 0.7,
        max_tokens: int = 2048,
        retry_on_failure: bool = True
    ) -> Dict[str, Any]:
        provider_order = []
        for provider_name in config.llm.providers:
            try:
                provider = LLMProvider(provider_name)
                if provider in self.providers:
                    provider_order.append(provider)
            except ValueError:
                continue
        
        if not provider_order:
            provider_order = list(self.providers.keys())
        
        last_error = None
        for provider in provider_order:
            try:
                start_time = time.time()
                if provider == LLMProvider.GEMINI:
                    text = self._call_gemini(prompt, temperature=temperature, max_tokens=max_tokens)
                elif provider == LLMProvider.GROQ:
                    text = self._call_groq(prompt, temperature=temperature, max_tokens=max_tokens)
                elif provider == LLMProvider.HUGGINGFACE:
                    text = self._call_huggingface(prompt, temperature=temperature, max_tokens=max_tokens)
                elif provider == LLMProvider.TOGETHER:
                    text = self._call_together(prompt, temperature=temperature, max_tokens=max_tokens)
                elif provider == LLMProvider.COHERE:
                    text = self._call_cohere(prompt, temperature=temperature, max_tokens=max_tokens)
                else:
                    continue
                
                elapsed = time.time() - start_time
                self.usage_stats[provider]["calls"] += 1
                self.last_used = provider
                return {
                    "text": text,
                    "provider": provider.value,
                    "elapsed_time": elapsed,
                    "success": True
                }
            except Exception as e:
                last_error = e
                self.usage_stats[provider]["failures"] += 1
                logger.warning(f"Provider {provider.value} failed: {str(e)[:100]}")
                
                if not retry_on_failure or provider == provider_order[-1]:
                    logger.error(f"All LLM providers exhausted. Last error: {e}")
                    break
                
                # Wait before trying next provider
                logger.info(f"Trying next provider in fallback chain...")
                time.sleep(0.5)
                continue
        
        return {
            "text": None,
            "provider": None,
            "error": str(last_error),
            "success": False
        }
    
    def get_usage_stats(self) -> Dict[str, Dict[str, int]]:
        return self.usage_stats
    
    def get_available_providers(self) -> List[str]:
        return [p.value for p in self.providers.keys()]


llm_manager = None

def get_llm_manager() -> LLMManager:
    global llm_manager
    if llm_manager is None:
        llm_manager = LLMManager()
    return llm_manager
