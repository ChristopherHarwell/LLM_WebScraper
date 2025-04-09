"""
Web Scraper API Package

This package contains the FastAPI implementation for the web scraper chatbot:

- main: FastAPI application and endpoints
"""

from .main import app, QueryRequest, QueryResponse

__all__ = ['app', 'QueryRequest', 'QueryResponse']
