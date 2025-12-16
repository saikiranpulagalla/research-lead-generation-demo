"""
Extractor Module
LangChain-based LLM extraction pipeline with retry logic.
"""

"""
Extractor Module
LangChain-based LLM extraction pipeline with retry logic.
"""

import json
from typing import Dict, Any, Optional
from pathlib import Path
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.language_models.chat_models import BaseChatModel
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from .model_selector import ModelSelector
from .schema import validate_json_structure, ValidationResult


class LLMExtractor:
    """Extracts structured data from text using LLM."""
    
    def __init__(
        self,
        model_selector: ModelSelector,
        prompt_path: Optional[str] = None,
        max_retries: int = 3,
    ):
        """
        Initialize extractor.
        
        Args:
            model_selector: ModelSelector instance for LLM management
            prompt_path: Path to extraction prompt file
            max_retries: Maximum retry attempts for extraction
        """
        self.model_selector = model_selector
        self.max_retries = max_retries
        
        # Load extraction prompt
        if prompt_path:
            self.prompt_template = self._load_prompt(prompt_path)
        else:
            # Use default prompt
            default_prompt_path = Path(__file__).parent.parent.parent / "prompts" / "extraction_prompt.txt"
            self.prompt_template = self._load_prompt(str(default_prompt_path))
        
        # Initialize model with fallback
        self.model, self.model_type = model_selector.get_model_with_fallback()
        
    def _load_prompt(self, prompt_path: str) -> PromptTemplate:
        """Load prompt template from file."""
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompt_text = f.read()
            
            return PromptTemplate(
                template=prompt_text,
                input_variables=["document_text"]
            )
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        except Exception as e:
            raise Exception(f"Failed to load prompt: {str(e)}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,))
    )
    def extract(self, text: str) -> Dict[str, Any]:
        """
        Extract structured data from text with retry logic.
        
        Args:
            text: Input text to extract from
            
        Returns:
            Extracted structured data as dictionary
            
        Raises:
            Exception: If extraction fails after all retries
        """
        # We treat failures (including empty/invalid JSON) as a signal to
        # optionally fall back to the other provider if available.
        try:
            # First attempt with the currently selected model
            return self._run_single_extraction_attempt(text, self.model, self.model_type)
        except Exception as e:
            print(f"Extraction attempt failed with {self.model_type}: {str(e)}")

            # Ask selector which keys are available so we can make a smart fallback choice
            try:
                key_status = self.model_selector.validate_api_keys()
            except Exception:
                key_status = {"openai": False, "gemini": False}

            # Decide fallback direction based on current model and available keys
            fallback_model_type: Optional[str] = None
            if self.model_type == "openai" and key_status.get("gemini"):
                fallback_model_type = "gemini"
            elif self.model_type == "gemini" and key_status.get("openai"):
                fallback_model_type = "openai"

            if not fallback_model_type:
                # No other provider to fall back to – surface the original cause
                raise Exception(f"Extraction failed with {self.model_type}: {str(e)}")

            try:
                print(f"Attempting fallback to {fallback_model_type.capitalize()}...")
                if fallback_model_type == "gemini":
                    self.model = self.model_selector.get_fallback_model()
                    self.model_type = "gemini"
                else:
                    self.model = self.model_selector.get_primary_model()
                    self.model_type = "openai"

                return self._run_single_extraction_attempt(text, self.model, self.model_type)
            except Exception as fallback_error:
                print(
                    f"Fallback to {fallback_model_type} also failed: "
                    f"{str(fallback_error)}"
                )
                # Include both primary and fallback failure reasons to aid debugging
                raise Exception(
                    "Extraction failed after trying all available models. "
                    f"Primary error ({self.model_type}): {str(e)} | "
                    f"Fallback error ({fallback_model_type}): {str(fallback_error)}"
                )

    def _run_single_extraction_attempt(
        self,
        text: str,
        model: BaseChatModel,
        model_type: str,
    ) -> Dict[str, Any]:
        """
        Run a single extraction attempt against the specified model.

        This isolates one model invocation + parsing/validation so we can easily
        call it for both primary and fallback models and keep tenacity retries
        focused on the overall operation.
        """
        # Format prompt
        formatted_prompt = self.prompt_template.format(document_text=text)

        # Invoke LLM
        response = model.invoke(formatted_prompt)

        # Extract content
        if hasattr(response, "content"):
            content = response.content
        else:
            content = str(response)

        # Diagnostic: show a short preview of the raw response to aid debugging
        try:
            preview = content.strip()[:1000]
            print(
                f"[{model_type}] LLM response preview (len={len(content)}): "
                f"{preview!r}"
            )
        except Exception:
            print(f"[{model_type}] LLM response preview unavailable")

        # Parse JSON
        parsed_data = self._parse_json(content)

        # Validate structure
        validation = validate_json_structure(parsed_data)

        if not validation.is_valid:
            raise Exception(f"Validation failed: {', '.join(validation.errors)}")

        return validation.data
    
    def _parse_json(self, content: str) -> Dict[str, Any]:
        """
        Parse JSON from LLM response with robust error handling.
        
        Args:
            content: LLM response content
            
        Returns:
            Parsed JSON dictionary
        """
        # Remove markdown code blocks if present
        content = content.strip()

        # Handle empty content explicitly to avoid confusing JSON errors
        if not content:
            raise Exception("Empty LLM response: content is empty or whitespace."
                            " Check model availability, API keys, or prompt formatting.")

        # Remove markdown code blocks (handle cases where closing ``` is missing)
        if content.startswith("```"):
            lines = content.split("\n")
            json_lines = []
            in_json = False
            
            for line in lines:
                stripped_line = line.strip()
                if stripped_line.startswith("```"):
                    if not in_json:
                        in_json = True
                        continue
                    else:
                        # Found closing ```
                        break
                if in_json:
                    json_lines.append(line)
            
            # If we never found closing ```, use all lines after the first ```
            if json_lines:
                content = "\n".join(json_lines).strip()
            else:
                # Fallback: remove first line if it's ```json or ```
                if lines and lines[0].strip().startswith("```"):
                    content = "\n".join(lines[1:]).strip()

        # Try to find JSON object boundaries
        start_idx = content.find('{')
        if start_idx == -1:
            raise Exception("No JSON object found in LLM response. Response starts with: "
                          f"{content[:200]!r}")
        
        # Find the matching closing brace, handling nested objects
        end_idx = start_idx
        brace_count = 0
        in_string = False
        escape_next = False
        
        for i in range(start_idx, len(content)):
            char = content[i]
            
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i
                        break
        
        # Extract JSON string
        if brace_count == 0 and end_idx > start_idx:
            json_str = content[start_idx:end_idx + 1]
        else:
            # JSON might be truncated - try to repair it
            json_str = content[start_idx:]
            # Try to close unclosed objects by adding closing braces
            if brace_count > 0:
                # Check if we're in the middle of a string - if so, close it first
                if in_string:
                    json_str += '"'
                # Add closing braces
                json_str += '\n' + '}' * brace_count

        # Parse JSON
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            # Try one more time with the original content after markdown removal
            try:
                # Try parsing from the first { to the last }
                start_idx = content.find('{')
                end_idx = content.rfind('}')
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    json_str = content[start_idx:end_idx + 1]
                    return json.loads(json_str)
            except json.JSONDecodeError:
                pass

            # Include a short snippet of the content to help debugging
            snippet = content[:1000].replace('\n', '\\n')
            raise Exception(f"Failed to parse JSON from LLM response: {str(e)}. "
                          f"Response length: {len(content)}, "
                          f"Response snippet: {snippet!r}")
    
    def extract_with_validation(self, text: str) -> tuple[Dict[str, Any], ValidationResult]:
        """
        Extract and return both data and validation result.
        
        Args:
            text: Input text
            
        Returns:
            Tuple of (extracted_data, validation_result)
        """
        try:
            data = self.extract(text)
            validation = validate_json_structure(data)
            return data, validation
        except Exception as e:
            return {}, ValidationResult(
                is_valid=False,
                errors=[str(e)]
            )
    
    def get_current_model_info(self) -> Dict[str, str]:
        """Get information about currently active model."""
        return {
            "model_type": self.model_type,
            "model_name": self.model_selector.primary_model if self.model_type == "openai" else self.model_selector.fallback_model,
        }