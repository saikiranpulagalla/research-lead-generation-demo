"""
Model Selector Module
Handles LLM selection with OpenAI (primary) and Google Gemini (fallback).
"""

"""
Model Selector Module
Handles LLM selection with OpenAI (primary) and Google Gemini (fallback).
"""

import os
from typing import Optional, Literal
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models.chat_models import BaseChatModel


class ModelSelector:
    """Selects and initializes LLM models with fallback logic."""
    
    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        google_api_key: Optional[str] = None,
        primary_model: str = "gpt-4o",
        fallback_model: str = "gemini-2.5-flash",
        temperature: float = 0.1,
    ):
        """
        Initialize model selector.
        
        Args:
            openai_api_key: OpenAI API key (or from env)
            google_api_key: Google API key (or from env)
            primary_model: OpenAI model name
            fallback_model: Gemini model name
            temperature: Model temperature (0-1)
        """
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.google_api_key = google_api_key or os.getenv("GOOGLE_API_KEY")
        self.primary_model = primary_model
        self.fallback_model = fallback_model
        self.temperature = temperature
        
        # Track which model is currently active
        self.current_model: Literal["openai", "gemini"] = "openai"
    
    def get_primary_model(self) -> BaseChatModel:
        """
        Get OpenAI model (primary).
        
        Returns:
            Initialized ChatOpenAI model
            
        Raises:
            ValueError: If OpenAI API key is not set
        """
        if not self.openai_api_key:
            raise ValueError(
                "OpenAI API key not found. "
                "Set OPENAI_API_KEY environment variable or pass it to constructor."
            )
        
        try:
            model = ChatOpenAI(
                model=self.primary_model,
                api_key=self.openai_api_key,
                temperature=self.temperature,
                max_tokens=4096,
                timeout=60,
                max_retries=2,
            )
            self.current_model = "openai"
            return model
        except Exception as e:
            raise Exception(f"Failed to initialize OpenAI model: {str(e)}")
    
    def get_fallback_model(self) -> BaseChatModel:
        """
        Get Google Gemini model (fallback).
        
        Returns:
            Initialized ChatGoogleGenerativeAI model
            
        Raises:
            ValueError: If Google API key is not set
        """
        if not self.google_api_key:
            raise ValueError(
                "Google API key not found. "
                "Set GOOGLE_API_KEY environment variable or pass it to constructor."
            )
        
        try:
            model = ChatGoogleGenerativeAI(
                model=self.fallback_model,
                google_api_key=self.google_api_key,
                temperature=self.temperature,
                max_output_tokens=8192,  # Increased to handle longer JSON responses
                timeout=60,
            )
            self.current_model = "gemini"
            return model
        except Exception as e:
            raise Exception(f"Failed to initialize Gemini model: {str(e)}")
    
    def get_model_with_fallback(self) -> tuple[BaseChatModel, Literal["openai", "gemini"]]:
        """
        Get model with automatic fallback logic.
        Tries OpenAI first, falls back to Gemini if OpenAI fails.
        
        Returns:
            Tuple of (model, model_type)
        """
        # Try OpenAI first
        try:
            if self.openai_api_key:
                model = self.get_primary_model()
                return model, "openai"
        except Exception as e:
            print(f"OpenAI initialization failed: {str(e)}. Falling back to Gemini...")
        
        # Fall back to Gemini
        try:
            if self.google_api_key:
                model = self.get_fallback_model()
                return model, "gemini"
        except Exception as e:
            raise Exception(
                f"Both OpenAI and Gemini initialization failed. "
                f"Last error: {str(e)}"
            )
        
        raise Exception(
            "No API keys available. Set either OPENAI_API_KEY or GOOGLE_API_KEY."
        )
    
    def validate_api_keys(self) -> dict[str, bool]:
        """
        Validate which API keys are available.
        
        Returns:
            Dictionary with availability status for each provider
        """
        return {
            "openai": bool(self.openai_api_key),
            "gemini": bool(self.google_api_key),
        }
    
    def get_available_models(self) -> list[str]:
        """
        Get list of available models based on API keys.
        
        Returns:
            List of available model names
        """
        available = []
        keys = self.validate_api_keys()
        
        if keys["openai"]:
            available.append(f"OpenAI: {self.primary_model}")
        if keys["gemini"]:
            available.append(f"Gemini: {self.fallback_model}")
        
        return available