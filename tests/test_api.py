import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from src.api.main import app, QueryRequest

@pytest.fixture
def test_client():
    """Fixture providing a test client for the FastAPI app."""
    return TestClient(app)

@pytest.fixture
def mock_orchestrator():
    """Fixture providing a mocked WebScraperOrchestrator."""
    mock_orch = MagicMock()
    mock_orch.process_query.return_value = {
        "answer": "The price is $42.99",
        "reasoning": "Found in the product price element",
        "html_element": "<div class='price'>$42.99</div>"
    }
    return mock_orch

def test_health_endpoint(test_client):
    """Test the health check endpoint."""
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

@patch('src.agents.orchestrator.WebScraperOrchestrator.process_query')
def test_ask_endpoint_success(mock_process_query, test_client):
    """Test the /ask endpoint with a successful response."""
    # Setup mock to return a successful result
    mock_process_query.return_value = {
        "answer": "The price is $42.99",
        "reasoning": "Found in the product price element",
        "html_element": "<div class='price'>$42.99</div>"
    }
    
    # Make request
    response = test_client.post(
        "/ask",
        json={"url": "https://example.com", "query": "What is the price?"}
    )
    
    # Assertions
    assert response.status_code == 200
    result = response.json()
    assert "https://example.com" in result["url"]  # URL might have trailing slash
    assert result["query"] == "What is the price?"
    assert result["answer"] == "The price is $42.99"
    assert result["reasoning"] == "Found in the product price element"
    assert result["html_element"] == "<div class='price'>$42.99</div>"
    
    # Verify orchestrator called correctly
    mock_process_query.assert_called_once()
    args, kwargs = mock_process_query.call_args
    assert kwargs["url"].startswith("https://example.com")
    assert kwargs["query"] == "What is the price?"

def test_ask_endpoint_validation(test_client):
    """Test input validation for the /ask endpoint."""
    # Test with missing URL
    response = test_client.post(
        "/ask",
        json={"query": "What is the price?"}
    )
    assert response.status_code == 422
    
    # Test with invalid URL
    response = test_client.post(
        "/ask",
        json={"url": "not-a-url", "query": "What is the price?"}
    )
    assert response.status_code == 422
    
    # Test with missing query
    response = test_client.post(
        "/ask",
        json={"url": "https://example.com"}
    )
    assert response.status_code == 422

@patch('src.agents.orchestrator.WebScraperOrchestrator.process_query')
def test_ask_endpoint_error_handling(mock_process_query, test_client):
    """Test error handling in the /ask endpoint."""
    # Setup mock to raise an exception
    mock_process_query.side_effect = Exception("Connection error")
    
    # Make request
    response = test_client.post(
        "/ask",
        json={"url": "https://example.com", "query": "What is the price?"}
    )
    
    # Assertions
    assert response.status_code == 500
    result = response.json()
    assert "detail" in result
    assert "Connection error" in result["detail"] 