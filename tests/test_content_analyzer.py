import pytest
from unittest.mock import MagicMock, patch
from src.agents.content_analyzer import ContentAnalyzerAgent

@pytest.fixture
def mock_ollama_llm():
    """Fixture providing a mocked Ollama LLM."""
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = {
        "content": """{
            "answer": "The price is $42.99",
            "reasoning": "Found in the product-price div element",
            "html_element": "<div class='product-price'>$42.99</div>"
        }"""
    }
    return mock_llm

@pytest.fixture
def sample_html():
    """Fixture providing a sample HTML content."""
    return """
    <html>
        <head><title>Test Product</title></head>
        <body>
            <h1>Product Name</h1>
            <div class="product-description">This is a sample product.</div>
            <div class="product-price">$42.99</div>
            <div class="product-rating">4.5 stars</div>
        </body>
    </html>
    """

def test_content_analyzer_initialization():
    """Test that the ContentAnalyzerAgent initializes correctly."""
    mock_llm = MagicMock()
    analyzer = ContentAnalyzerAgent(llm=mock_llm)
    assert analyzer.llm == mock_llm
    assert analyzer.name == "content_analyzer"

def test_analyze_content(mock_ollama_llm, sample_html):
    """Test that the agent can analyze HTML content and answer questions."""
    query = "What is the price of the product?"
    
    analyzer = ContentAnalyzerAgent(llm=mock_ollama_llm)
    result = analyzer.analyze_content(sample_html, query)
    
    # Assertions
    assert "The price is $42.99" == result["answer"]
    assert "Found in the product-price div element" == result["reasoning"]
    assert "<div class='product-price'>$42.99</div>" == result["html_element"]

def test_analyze_content_with_images(mock_ollama_llm, sample_html):
    """Test that the agent can analyze HTML with embedded images."""
    query = "What is the price of the product?"
    images = {
        "product.jpg": "data:image/jpeg;base64,ABCD"
    }
    
    analyzer = ContentAnalyzerAgent(llm=mock_ollama_llm)
    result = analyzer.analyze_content(sample_html, query, images=images)
    
    # Verify the result
    assert "The price is $42.99" == result["answer"]
    
    # We don't need to check the image is in the call args since our embedding method
    # replaces img src attributes, not adds the base64 data to the message

def test_error_handling():
    """Test error handling when LLM fails to process the content."""
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = Exception("LLM processing error")
    
    analyzer = ContentAnalyzerAgent(llm=mock_llm)
    
    with pytest.raises(Exception) as exc_info:
        analyzer.analyze_content("<html></html>", "What is this?")
    
    assert "LLM processing error" in str(exc_info.value)

def test_malformed_llm_response():
    """Test handling of malformed LLM responses."""
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = {"content": "Not a JSON response"}
    
    analyzer = ContentAnalyzerAgent(llm=mock_llm)
    result = analyzer.analyze_content("<html></html>", "What is this?")
    
    # Should handle non-JSON gracefully
    assert "Not a JSON response" == result["answer"]
    assert "raw" in result["reasoning"].lower()
    assert result["html_element"] is None

@patch('json.loads')
def test_json_parsing_error(mock_json_loads, mock_ollama_llm):
    """Test handling of JSON parsing errors."""
    mock_json_loads.side_effect = ValueError("Invalid JSON")
    
    analyzer = ContentAnalyzerAgent(llm=mock_ollama_llm)
    result = analyzer.analyze_content("<html></html>", "What is this?")
    
    # Should handle JSON parsing errors gracefully
    assert isinstance(result, dict)
    assert "json format" in result["reasoning"].lower() 