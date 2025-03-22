from typing import Dict, Optional, Any, Type, List, Union
from crewai import Agent
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from ..tools.web_scraper import WebScraperTool

class ScrapeWebsiteInput(BaseModel):
    """Input schema for CustomScrapeWebsiteTool."""
    url: str = Field(..., description="The URL to scrape")

class CustomScrapeWebsiteTool(BaseTool):
    """Custom tool for web scraping using Playwright."""
    
    name: str = "scrape_website"
    description: str = "Scrapes a website and returns its HTML content and images"
    args_schema: Type[BaseModel] = ScrapeWebsiteInput
    
    def __init__(self) -> None:
        super().__init__()
        self._scraper = WebScraperTool()
    
    def _run(self, url: str) -> str:
        """Run the tool with the given URL.
        
        Args:
            url: The URL to scrape
            
        Returns:
            String containing the scraping results
        """
        try:
            with self._scraper as scraper:
                html, images = scraper.fetch_page_content(url)
                has_captcha = scraper.detect_captcha(html)
                
                result = {
                    "html": html,
                    "images": images,
                    "has_captcha": has_captcha
                }
                
                return str(result)
        except Exception as e:
            return f"Error scraping website: {str(e)}"
    
    async def _arun(self, url: str) -> str:
        """Async version of _run."""
        return self._run(url)

def create_agents(llm: Optional[ChatOllama] = None) -> Dict[str, Agent]:
    """Create and return the agent instances.
    
    Args:
        llm: Optional ChatOllama instance. If not provided, creates a new one.
        
    Returns:
        Dictionary of agent name to Agent instance
    """
    if llm is None:
        llm = ChatOllama(
            model="ollama/llava",
            base_url="http://localhost:11434",
            temperature=0.5
        )
    
    # Create tools
    scraper_tool = CustomScrapeWebsiteTool()
    
    # Scraper agent with custom tool
    scraper_agent = Agent(
        role="web_scraper",
        goal="Fetch HTML content and detect CAPTCHAs from target websites",
        backstory="You are an expert at web scraping and CAPTCHA detection",
        tools=[scraper_tool],
        allow_delegation=True,
        llm=llm,
        verbose=True
    )
    
    # Vision agent for CAPTCHA solving
    vision_agent = Agent(
        role="captcha_solver",
        goal="Solve CAPTCHAs and decode text from images",
        backstory="You are an expert at interpreting images and solving visual challenges",
        tools=[],  # Uses LLM's vision capabilities directly
        llm=llm,
        verbose=True
    )
    
    # Analysis agent for answering queries
    analysis_agent = Agent(
        role="content_analyzer",
        goal="Analyze web content and answer questions with reasoning",
        backstory="""You are an expert at understanding web content and providing 
        detailed answers with references to specific HTML elements""",
        tools=[],  # Uses LLM's reasoning capabilities directly
        llm=llm,
        verbose=True
    )
    
    return {
        "scraper": scraper_agent,
        "vision": vision_agent,
        "analyzer": analysis_agent
    } 