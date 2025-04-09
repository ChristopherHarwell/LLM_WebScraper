import pytest
from unittest.mock import MagicMock, patch
from src.agents.orchestrator import WebScraperOrchestrator

@pytest.fixture
def mock_agents():
    """Fixture providing mocked agents."""
    # Setup scraper mock to work as context manager
    mock_scraper = MagicMock()
    mock_scraper.__enter__ = MagicMock(return_value=mock_scraper)
    mock_scraper.__exit__ = MagicMock(return_value=None)
    mock_scraper.fetch_page_content.return_value = ("<html></html>", {})
    
    mock_captcha_solver = MagicMock()
    mock_captcha_solver.solve_captcha.return_value = "CAPTCHA123"
    
    mock_content_analyzer = MagicMock()
    mock_content_analyzer.analyze_content.return_value = {
        "answer": "The answer is 42",
        "reasoning": "Found in the page",
        "html_element": "<div>42</div>"
    }
    
    return {
        "scraper": mock_scraper,
        "captcha_solver": mock_captcha_solver,
        "content_analyzer": mock_content_analyzer
    }

def test_orchestrator_initialization():
    """Test that the WebScraperOrchestrator initializes correctly."""
    mock_llm = MagicMock()
    with patch('src.agents.orchestrator.WebScraperTool'):
        with patch('src.agents.orchestrator.CaptchaSolverAgent'):
            with patch('src.agents.orchestrator.ContentAnalyzerAgent'):
                orchestrator = WebScraperOrchestrator(llm=mock_llm)
                assert orchestrator.llm == mock_llm
                assert hasattr(orchestrator, "create_agents")

@patch('src.agents.orchestrator.WebScraperTool')
@patch('src.agents.orchestrator.CaptchaSolverAgent')
@patch('src.agents.orchestrator.ContentAnalyzerAgent')
def test_create_agents(mock_analyzer_cls, mock_solver_cls, mock_scraper_cls):
    """Test that the orchestrator creates all required agents."""
    # Setup mocks
    mock_scraper = MagicMock()
    mock_scraper_cls.return_value = mock_scraper
    
    mock_solver = MagicMock()
    mock_solver_cls.return_value = mock_solver
    
    mock_analyzer = MagicMock()
    mock_analyzer_cls.return_value = mock_analyzer
    
    # Create orchestrator and call create_agents directly without auto-init
    mock_llm = MagicMock()
    orchestrator = WebScraperOrchestrator.__new__(WebScraperOrchestrator)
    orchestrator.llm = mock_llm
    orchestrator.max_captcha_attempts = 3
    agents = orchestrator.create_agents()
    
    # Assertions
    assert "scraper" in agents
    assert "captcha_solver" in agents
    assert "content_analyzer" in agents
    
    mock_solver_cls.assert_called_once_with(llm=mock_llm)
    mock_analyzer_cls.assert_called_once_with(llm=mock_llm)

def test_process_query_no_captcha(mock_agents):
    """Test the query processing flow without CAPTCHA."""
    url = "https://example.com"
    query = "What is the meaning of life?"
    
    # Setup the mock scraper to not detect CAPTCHA
    mock_agents["scraper"].detect_captcha.return_value = False
    
    # Create orchestrator and process query
    orchestrator = WebScraperOrchestrator.__new__(WebScraperOrchestrator)
    orchestrator.agents = mock_agents
    orchestrator.max_captcha_attempts = 3
    result = orchestrator.process_query(url, query)
    
    # Assertions
    mock_agents["scraper"].fetch_page_content.assert_called_once_with(url)
    mock_agents["captcha_solver"].solve_captcha.assert_not_called()
    mock_agents["content_analyzer"].analyze_content.assert_called_once()
    
    assert result["answer"] == "The answer is 42"
    assert result["reasoning"] == "Found in the page"
    assert result["html_element"] == "<div>42</div>"

def test_process_query_with_captcha(mock_agents):
    """Test the query processing flow with CAPTCHA detection and solving."""
    url = "https://example.com"
    query = "What is the meaning of life?"
    
    # Setup the mock scraper to detect CAPTCHA first time, then not after solving
    mock_agents["scraper"].detect_captcha.side_effect = [True, False]
    
    # First fetch finds CAPTCHA, second one succeeds
    captcha_html = "<html><img src='captcha.png'></html>"
    captcha_images = {"captcha.png": "data:image/png;base64,ABCDEF"}
    success_html = "<html><div>42</div></html>"
    mock_agents["scraper"].fetch_page_content.side_effect = [
        (captcha_html, captcha_images),
        (success_html, {})
    ]
    
    # Create orchestrator and process query
    orchestrator = WebScraperOrchestrator.__new__(WebScraperOrchestrator)
    orchestrator.agents = mock_agents
    orchestrator.max_captcha_attempts = 3
    result = orchestrator.process_query(url, query)
    
    # Assertions
    assert mock_agents["scraper"].fetch_page_content.call_count == 2
    mock_agents["captcha_solver"].solve_captcha.assert_called_once_with(
        "data:image/png;base64,ABCDEF", 
        context=captcha_html
    )
    mock_agents["content_analyzer"].analyze_content.assert_called_once()
    
    assert result["answer"] == "The answer is 42"

def test_process_query_error_handling(mock_agents):
    """Test error handling in the orchestration process."""
    url = "https://example.com"
    query = "What is this?"
    
    # Override the fetch_page_content method to raise an exception
    mock_agents["scraper"].fetch_page_content.side_effect = Exception("Connection error")
    
    # Create orchestrator and process query
    orchestrator = WebScraperOrchestrator.__new__(WebScraperOrchestrator)
    orchestrator.agents = mock_agents
    orchestrator.max_captcha_attempts = 3
    
    with pytest.raises(Exception) as exc_info:
        orchestrator.process_query(url, query)
    
    assert "Connection error" in str(exc_info.value)
    mock_agents["content_analyzer"].analyze_content.assert_not_called()

def test_max_captcha_attempts(mock_agents):
    """Test that the orchestrator limits CAPTCHA solving attempts."""
    url = "https://example.com"
    query = "What is this?"
    
    # Always detect CAPTCHA
    mock_agents["scraper"].detect_captcha.return_value = True
    
    # Always return the same CAPTCHA image
    mock_agents["scraper"].fetch_page_content.return_value = (
        "<html></html>", 
        {"captcha.png": "data:image/png;base64,ABCDEF"}
    )
    
    # Create orchestrator with limited attempts
    orchestrator = WebScraperOrchestrator.__new__(WebScraperOrchestrator)
    orchestrator.agents = mock_agents
    orchestrator.max_captcha_attempts = 3
    
    with pytest.raises(Exception) as exc_info:
        orchestrator.process_query(url, query)
    
    assert "Maximum CAPTCHA attempts" in str(exc_info.value)
    assert mock_agents["scraper"].fetch_page_content.call_count == 4  # Initial + 3 attempts 