"""
CAPTCHA Solver Agent Module

This module provides an agent that uses a vision-capable LLM to solve image-based CAPTCHAs
and other visual challenges found during web scraping.
"""

from typing import Optional, Dict, Any, Union
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
import re
import json

class CaptchaSolverAgent:
    """
    Agent responsible for solving image-based CAPTCHAs using a vision-capable LLM.
    
    This agent accepts base64-encoded image data and uses the LLM's vision capabilities
    to interpret the text or solve the visual challenge.
    
    Attributes:
        name: Identifier for the agent
        llm: Vision-capable language model (e.g., LLaVA via Ollama)
    """
    
    def __init__(self, llm: BaseChatModel):
        """
        Initialize the CAPTCHA solver agent.
        
        Args:
            llm: Vision-capable language model instance
        """
        self.name = "captcha_solver"
        self.llm = llm
    
    def solve_captcha(self, image_data_uri: str, context: Optional[str] = None) -> str:
        """
        Solve an image-based CAPTCHA using the vision-capable LLM.
        
        Args:
            image_data_uri: Base64 data URI of the CAPTCHA image
            context: Optional HTML context or instructions about the CAPTCHA
            
        Returns:
            String containing the solved CAPTCHA text
            
        Raises:
            Exception: If the LLM fails to interpret the image
        """
        # Prepare system and human messages for the LLM
        system_message = SystemMessage(
            content="You are a CAPTCHA solving assistant. Your task is to accurately read " 
                    "and interpret text from images, especially CAPTCHAs. Respond with ONLY "
                    "the text you see in the image, nothing else."
        )
        
        human_content = "What text do you see in this CAPTCHA image?"
        if context:
            human_content += f"\n\nContext: {context}"
        
        human_message = HumanMessage(
            content=[
                {"type": "text", "text": human_content},
                {"type": "image_url", "image_url": {"url": image_data_uri}}
            ]
        )
        
        # Call the vision model to interpret the image
        response = self.llm.invoke([system_message, human_message])
        
        # Extract the solution text
        # Check if the response is an object with a content attribute or a dict with a 'content' key
        if hasattr(response, 'content'):
            solution = response.content
        elif isinstance(response, dict) and 'content' in response:
            solution = response['content']
        else:
            solution = str(response)
        
        # Clean up the solution (remove quotes, extra spaces, etc.)
        solution = solution.strip().strip('"\'')
        
        return solution
    
    def solve_text_captcha(self, challenge: str) -> str:
        """
        Solve a text-based CAPTCHA challenge (e.g., math problems, logic puzzles).
        
        Args:
            challenge: The text of the CAPTCHA challenge
            
        Returns:
            The solution to the challenge
        """
        system_message = SystemMessage(
            content="You are a CAPTCHA solving assistant specialized in solving text-based "
                    "challenges like math problems and logic puzzles. Provide ONLY the answer, "
                    "no explanations."
        )
        
        human_message = HumanMessage(
            content=f"Solve this CAPTCHA challenge: {challenge}"
        )
        
        response = self.llm.invoke([system_message, human_message])
        
        # Handle response format flexibly
        if hasattr(response, 'content'):
            solution = response.content
        elif isinstance(response, dict) and 'content' in response:
            solution = response['content']
        else:
            solution = str(response)
            
        solution = solution.strip().strip('"\'')
        
        return solution 