import pytest
from unittest.mock import MagicMock, patch
from bs4 import BeautifulSoup
from src.tools.web_scraper import WebScraperTool

def test_web_scraper_initialization():
    """Test that the WebScraperTool initializes correctly."""
    with WebScraperTool() as scraper:
        assert scraper._playwright is not None
        assert scraper._browser is not None
    
    # Test the context manager closes resources
    scraper = WebScraperTool()
    assert scraper._playwright is None
    assert scraper._browser is None

@pytest.mark.integration
def test_fetch_page_content_integration():
    """Integration test for fetching content from a real site."""
    url = "https://example.com"  # Simple static test site
    
    with WebScraperTool() as scraper:
        html, images = scraper.fetch_page_content(url)
        
        # Basic assertions
        assert html is not None
        assert "Example Domain" in html
        assert isinstance(images, dict)
        
        # Test CAPTCHA detection (should be False for example.com)
        assert not scraper.detect_captcha(html)

@patch('src.tools.web_scraper.sync_playwright')
def test_fetch_page_content_mock(mock_playwright):
    """Test fetching page content with mocked Playwright."""
    # Setup mocks
    mock_page = MagicMock()
    mock_page.content.return_value = "<html><body>Test Content</body></html>"
    mock_page.query_selector_all.return_value = []
    
    mock_browser = MagicMock()
    mock_browser.new_page.return_value = mock_page
    
    mock_playwright_context = MagicMock()
    mock_playwright_context.firefox.launch.return_value = mock_browser
    mock_playwright.return_value.start.return_value = mock_playwright_context
    
    # Execute test
    url = "https://test.com"
    scraper = WebScraperTool()
    with scraper:
        html, images = scraper.fetch_page_content(url)
    
    # Assertions
    assert html == "<html><body>Test Content</body></html>"
    assert images == {}
    mock_page.goto.assert_called_once_with(url, timeout=60000)
    mock_page.close.assert_called_once()

def test_detect_captcha():
    """Test CAPTCHA detection logic with various HTML patterns."""
    captcha_html_samples = [
        """<html><body><form><img src="captcha.png" alt="CAPTCHA"></form></body></html>""",
        """<html><body><p>Please verify you are human</p></body></html>""",
        """<html><body><div class="captcha-container">Enter code</div></body></html>""",
        """<html><body><p>Prove you're not a robot</p></body></html>"""
    ]
    
    non_captcha_html = [
        """<html><body><p>Welcome to our website</p></body></html>""",
        """<html><body><img src="logo.png" alt="Logo"></body></html>""",
        """<html><body><form><input type="text" name="search"></form></body></html>"""
    ]
    
    with WebScraperTool() as scraper:
        # Test positive cases (should detect CAPTCHA)
        for html in captcha_html_samples:
            assert scraper.detect_captcha(html), f"Failed to detect CAPTCHA in: {html}"
        
        # Test negative cases (should not detect CAPTCHA)
        for html in non_captcha_html:
            assert not scraper.detect_captcha(html), f"False positive CAPTCHA detection in: {html}"

@patch('requests.get')
@patch('src.tools.web_scraper.sync_playwright')
def test_image_processing(mock_playwright, mock_requests_get):
    """Test that images are properly processed, especially CAPTCHAs."""
    # Setup mocks
    mock_img = MagicMock()
    mock_img.get_attribute.side_effect = lambda attr: {
        "src": "https://example.com/captcha.png"
    }.get(attr)
    
    mock_page = MagicMock()
    mock_page.content.return_value = "<html><body>Test Content</body></html>"
    mock_page.query_selector_all.return_value = [mock_img]
    
    mock_browser = MagicMock()
    mock_browser.new_page.return_value = mock_page
    
    mock_playwright_context = MagicMock()
    mock_playwright_context.firefox.launch.return_value = mock_browser
    mock_playwright.return_value.start.return_value = mock_playwright_context
    
    # Mock the image download
    mock_response = MagicMock()
    mock_response.content = b"fake image data"
    mock_requests_get.return_value = mock_response
    
    # Execute test
    url = "https://test.com"
    scraper = WebScraperTool()
    with scraper:
        html, images = scraper.fetch_page_content(url)
    
    # Assertions
    assert "https://example.com/captcha.png" in images
    assert images["https://example.com/captcha.png"].startswith("data:image/png;base64,")
    mock_requests_get.assert_called_once_with(
        "https://example.com/captcha.png",
        headers={"Referer": url},
        timeout=10
    )

def test_error_handling():
    """Test error handling during page fetching."""
    with patch('src.tools.web_scraper.sync_playwright') as mock_playwright:
        # Setup mocks to raise an exception
        mock_page = MagicMock()
        mock_page.goto.side_effect = Exception("Connection timeout")
        
        mock_browser = MagicMock()
        mock_browser.new_page.return_value = mock_page
        
        mock_playwright_context = MagicMock()
        mock_playwright_context.firefox.launch.return_value = mock_browser
        mock_playwright.return_value.start.return_value = mock_playwright_context
        
        # Execute test
        scraper = WebScraperTool()
        with scraper:
            with pytest.raises(Exception) as exc_info:
                html, images = scraper.fetch_page_content("https://test.com")
            
            assert "Connection timeout" in str(exc_info.value)
        
        # Ensure page is closed even when an exception occurs
        mock_page.close.assert_called_once() 