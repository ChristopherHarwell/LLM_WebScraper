import pytest
from src.tools.web_scraper import WebScraperTool

def test_web_scraper():
    """Test basic web scraping functionality."""
    url = "https://example.com"  # Simple static test site
    
    with WebScraperTool() as scraper:
        html, images = scraper.fetch_page_content(url)
        
        # Basic assertions
        assert html is not None
        assert "Example Domain" in html
        assert isinstance(images, dict)
        
        # Test CAPTCHA detection (should be False for example.com)
        assert not scraper.detect_captcha(html)

def test_captcha_detection():
    """Test CAPTCHA detection logic."""
    # HTML with CAPTCHA-like content
    test_html = """
    <html>
        <body>
            <form>
                <img src="captcha.png" alt="CAPTCHA">
                <input type="text" name="captcha" placeholder="Enter the text">
                <p>Please verify you are human</p>
            </form>
        </body>
    </html>
    """
    
    with WebScraperTool() as scraper:
        assert scraper.detect_captcha(test_html) 