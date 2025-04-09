"""
Web Scraper Orchestrator Module

This module provides the orchestrator that coordinates the various agents
for the web scraping process, handling the workflow from URL fetching to
CAPTCHA solving and content analysis.
"""

from typing import Dict, Any, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama.chat_models import ChatOllama

from ..tools.web_scraper import WebScraperTool
from .captcha_solver import CaptchaSolverAgent
from .content_analyzer import ContentAnalyzerAgent

class WebScraperOrchestrator:
    """
    Orchestrator that coordinates the different specialized agents for web scraping.
    
    This class creates and manages the workflow between the scraper, CAPTCHA solver,
    and content analyzer agents, implementing the overall pipeline from URL fetching
    to answering user queries.
    
    Attributes:
        llm: The language model shared by the agents
        agents: Dictionary of agent instances
        max_captcha_attempts: Maximum number of CAPTCHA solving attempts
    """
    
    def __init__(self, llm: Optional[BaseChatModel] = None, max_captcha_attempts: int = 3):
        """
        Initialize the web scraper orchestrator.
        
        Args:
            llm: Optional language model instance. If None, a default is created.
            max_captcha_attempts: Maximum number of attempts to solve a CAPTCHA
        """
        self.llm = llm or ChatOllama(
            model="ollama/llava",
            base_url="http://localhost:11434",
            temperature=0.5
        )
        self.max_captcha_attempts = max_captcha_attempts
        self.agents = self.create_agents()
    
    def create_agents(self) -> Dict[str, Any]:
        """
        Create and initialize all required agent instances.
        
        Returns:
            Dictionary mapping agent names to their instances
        """
        # Create the CAPTCHA solver agent
        captcha_solver = CaptchaSolverAgent(llm=self.llm)
        
        # Create the content analyzer agent
        content_analyzer = ContentAnalyzerAgent(llm=self.llm)
        
        # The WebScraperTool is not a full agent, but we include it in the same dict
        scraper = WebScraperTool()
        
        return {
            "scraper": scraper,
            "captcha_solver": captcha_solver,
            "content_analyzer": content_analyzer
        }
    
    def process_query(self, url: str, query: str) -> Dict[str, Any]:
        """
        Process a user query about a webpage.
        
        This method orchestrates the full pipeline:
        1. Fetch the webpage content
        2. Detect and solve CAPTCHAs if present
        3. Analyze the content to answer the query
        
        Args:
            url: The URL to scrape
            query: The user's natural language query
            
        Returns:
            Dictionary containing the answer, reasoning, and HTML element
            
        Raises:
            Exception: If scraping fails or CAPTCHA cannot be solved after max attempts
        """
        # Access our agents
        scraper = self.agents["scraper"]
        captcha_solver = self.agents["captcha_solver"]
        content_analyzer = self.agents["content_analyzer"]
        
        # Initialize CAPTCHA solving counter
        captcha_attempts = 0
        
        with scraper as scraper_instance:
            # First attempt to fetch the page
            html, images = scraper_instance.fetch_page_content(url)
            
            # Handle CAPTCHA if detected
            while scraper_instance.detect_captcha(html) and captcha_attempts < self.max_captcha_attempts:
                captcha_attempts += 1
                
                # Find the first CAPTCHA image
                captcha_image = None
                for src, data_uri in images.items():
                    if "captcha" in src.lower():
                        captcha_image = data_uri
                        break
                
                if not captcha_image:
                    # No image found but we detected a CAPTCHA, might be text-based
                    # For now, we'll just break and try to analyze the content anyway
                    break
                
                # Solve the CAPTCHA
                solution = captcha_solver.solve_captcha(captcha_image, context=html)
                
                # Here we would normally submit the CAPTCHA solution back to the page
                # But for this implementation, we'll just refetch the page
                # In a real implementation, this would involve form submission
                html, images = scraper_instance.fetch_page_content(url)
            
            # Check if we exceeded CAPTCHA attempts
            if captcha_attempts >= self.max_captcha_attempts and scraper_instance.detect_captcha(html):
                raise Exception(f"Maximum CAPTCHA attempts ({self.max_captcha_attempts}) exceeded")
            
            # Analyze the content
            result = content_analyzer.analyze_content(html, query, images)
            
            return result 