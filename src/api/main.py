from typing import Dict, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from crewai import Crew, Process
from langchain_ollama.chat_models import ChatOllama

from ..agents.agents import create_agents

class QueryRequest(BaseModel):
    url: HttpUrl
    query: str

class QueryResponse(BaseModel):
    url: str
    query: str
    answer: str
    reasoning: str
    html_element: Optional[str] = None

app = FastAPI(
    title="LLM Web Scraper Chatbot",
    description="A multi-agent web scraper that answers questions about web content",
    version="0.1.0"
)

# Initialize LLM once for reuse
llm = ChatOllama(
    model="ollama/llava",
    base_url="http://localhost:11434",
    temperature=0.5
)

@app.post("/ask", response_model=QueryResponse)
async def ask_page(request: QueryRequest) -> Dict:
    """Process a query about a webpage.
    
    Args:
        request: QueryRequest with url and query
        
    Returns:
        Dict containing the answer, reasoning, and relevant HTML element
    """
    try:
        # Create agents with shared LLM
        agents = create_agents(llm)
        
        # Create tasks for the crew
        tasks = [
            {
                "description": f"Scrape the webpage at {request.url} and detect any CAPTCHAs",
                "agent": agents["scraper"],
                "expected_output": "HTML content and any detected CAPTCHAs"
            },
            {
                "description": f"Based on the scraped content, answer the question: {request.query}",
                "agent": agents["analyzer"],
                "expected_output": "Answer with reasoning and HTML element reference"
            }
        ]
        
        # Create crew with tasks
        crew = Crew(
            agents=list(agents.values()),
            tasks=tasks,
            process=Process.sequential,
            verbose=True
        )
        
        # Run the crew
        result = crew.kickoff()
        
        # Extract results
        if isinstance(result, list):
            scraping_result = result[0]
            analysis_result = result[1]
        else:
            scraping_result = result
            analysis_result = result
            
        # Parse the analysis result
        if isinstance(analysis_result, str):
            try:
                # Try to parse as JSON if it's a string representation of a dict
                import json
                analysis_result = json.loads(analysis_result)
            except:
                # If not JSON, use the string as the answer
                analysis_result = {"answer": analysis_result, "reasoning": "Direct response from agent"}
        elif hasattr(analysis_result, 'raw_output'):
            # Handle CrewOutput object
            analysis_result = {
                "answer": analysis_result.raw_output,
                "reasoning": "Response from agent",
                "html_element": None
            }
        
        # Ensure we have a dictionary with the required fields
        if not isinstance(analysis_result, dict):
            analysis_result = {
                "answer": str(analysis_result),
                "reasoning": "Direct response from agent",
                "html_element": None
            }
        
        return {
            "url": str(request.url),
            "query": request.query,
            "answer": analysis_result.get("answer", "Could not find an answer"),
            "reasoning": analysis_result.get("reasoning", "No reasoning provided"),
            "html_element": analysis_result.get("html_element")
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy"} 