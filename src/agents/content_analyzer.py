"""
Content Analyzer Agent Module

This module provides an agent that analyzes web content using a vision-capable LLM
to answer user queries based on HTML content and embedded images.
"""

from typing import Dict, Optional, Any, List, Union
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from bs4 import BeautifulSoup
import json

class ContentAnalyzerAgent:
    """
    Agent responsible for analyzing web content and answering user queries.
    
    This agent uses a vision-capable LLM to analyze HTML content and any embedded
    images to provide accurate answers to user questions about the content.
    
    Attributes:
        name: Identifier for the agent
        llm: Vision-capable language model (e.g., DeepSeek-Vision via Ollama)
    """
    
    def __init__(self, llm: BaseChatModel):
        """
        Initialize the content analyzer agent.
        
        Args:
            llm: Vision-capable language model instance
        """
        self.name = "content_analyzer"
        self.llm = llm
    
    def analyze_content(self, 
                      html: str, 
                      query: str,
                      images: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Analyze web content and answer the user's query.
        
        Args:
            html: The HTML content of the webpage
            query: The user's natural language query
            images: Optional dictionary mapping image URLs to base64 data URIs
            
        Returns:
            Dictionary containing:
            - answer: The answer to the user's query
            - reasoning: Explanation of how the answer was derived
            - html_element: The HTML element containing the answer (if applicable)
            
        Raises:
            Exception: If the LLM fails to process the content
        """
        # Embed images in HTML if provided
        if images:
            html = self._embed_images_in_html(html, images)
        
        # Prepare system and human messages for the LLM
        system_message = SystemMessage(
            content="""You are a web content analysis expert. 
            Given HTML content and a question, your task is to find the answer in the content.
            Analyze the HTML structure, text, and any embedded images to provide an accurate answer.
            Always include the specific HTML element that contains your answer.
            Format your response as a JSON object with three fields:
            - answer: The direct answer to the question
            - reasoning: A brief explanation of how you found the answer
            - html_element: The HTML element (tag and content) containing the answer
            """
        )
        
        human_message = HumanMessage(
            content=f"""HTML Content:
            {html}
            
            Question: {query}
            
            Respond with a JSON object containing the answer, reasoning, and HTML element.
            """
        )
        
        # Call the model to analyze the content
        response = self.llm.invoke([system_message, human_message])
        
        # Extract response content based on the format
        if hasattr(response, 'content'):
            response_content = response.content
        elif isinstance(response, dict) and 'content' in response:
            response_content = response['content']
        else:
            response_content = str(response)
        
        # Extract and parse the JSON response
        try:
            # Try to parse as JSON
            result = json.loads(response_content)
            
            # Ensure all required fields are present
            return {
                "answer": result.get("answer", response_content),
                "reasoning": result.get("reasoning", "Direct response from model"),
                "html_element": result.get("html_element")
            }
        except (json.JSONDecodeError, ValueError):
            # If not valid JSON, return the raw response
            return {
                "answer": response_content,
                "reasoning": "Raw response from model (not in expected JSON format)",
                "html_element": None
            }
    
    def _embed_images_in_html(self, html: str, images: Dict[str, str]) -> str:
        """
        Embed base64-encoded images directly in the HTML.
        
        Args:
            html: The HTML content
            images: Dictionary mapping image URLs to base64 data URIs
            
        Returns:
            HTML with embedded images
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Replace image sources with data URIs
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if src in images:
                img['src'] = images[src]
        
        return str(soup) 