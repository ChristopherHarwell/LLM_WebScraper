"""
Web Scraper Chatbot API

This module provides the FastAPI endpoints for the web scraper chatbot,
exposing a user-friendly interface to query websites and get AI-powered answers.
"""

from typing import Dict, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl, Field

from ..agents.orchestrator import WebScraperOrchestrator

class QueryRequest(BaseModel):
    """
    Request model for the /ask endpoint.
    
    Attributes:
        url: The URL of the webpage to analyze
        query: The user's natural language query about the webpage
    """
    url: HttpUrl = Field(..., description="URL of the webpage to analyze")
    query: str = Field(..., description="Question to ask about the webpage content")

class QueryResponse(BaseModel):
    """
    Response model for the /ask endpoint.
    
    Attributes:
        url: The URL that was analyzed
        query: The original query
        answer: The answer to the query
        reasoning: Explanation of how the answer was derived
        html_element: Optional HTML element containing the answer
    """
    url: str = Field(..., description="URL that was analyzed")
    query: str = Field(..., description="Original question asked")
    answer: str = Field(..., description="Answer to the question")
    reasoning: str = Field(..., description="Explanation of how the answer was found")
    html_element: Optional[str] = Field(None, description="HTML element containing the answer")

# Create the FastAPI application
app = FastAPI(
    title="Web Scraper Chatbot API",
    description="A multi-agent web scraper that answers questions about web content",
    version="0.1.0"
)

# Create a singleton orchestrator to be reused across requests
orchestrator = WebScraperOrchestrator()

@app.post("/ask", response_model=QueryResponse)
async def ask_page(request: QueryRequest) -> Dict:
    """
    Process a query about a webpage and return an answer.
    
    This endpoint takes a URL and a query, scrapes the webpage,
    and uses AI to answer the query based on the content.
    
    Args:
        request: QueryRequest with url and query
        
    Returns:
        QueryResponse containing the answer, reasoning, and relevant HTML element
        
    Raises:
        HTTPException: If scraping fails or processing encounters an error
    """
    try:
        # Process the query using our orchestrator
        result = orchestrator.process_query(
            url=str(request.url),
            query=request.query
        )
        
        # Return formatted response
        return {
            "url": str(request.url),
            "query": request.query,
            "answer": result.get("answer", "Could not find an answer"),
            "reasoning": result.get("reasoning", "No reasoning provided"),
            "html_element": result.get("html_element")
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {str(e)}"
        )

@app.get("/health")
async def health_check() -> Dict:
    """
    Simple health check endpoint.
    
    Returns:
        Dictionary with status indicator
    """
    return {"status": "healthy"} 