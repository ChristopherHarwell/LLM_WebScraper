from typing import Dict, Tuple
import base64
import re
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

class WebScraperTool:
    """Custom web scraping tool using Playwright."""
    
    def __init__(self):
        self._playwright = None
        self._browser = None
    
    def __enter__(self):
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.firefox.launch(headless=True)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
    
    def fetch_page_content(self, url: str) -> Tuple[str, Dict[str, str]]:
        """Fetch page content and images using Playwright.
        
        Args:
            url: The target URL to scrape
            
        Returns:
            Tuple of (HTML content, dict of image URLs to base64 data)
        """
        page = self._browser.new_page()
        try:
            response = page.goto(url, timeout=60000)
            if not response:
                raise Exception(f"Failed to load {url}")
                
            html = page.content()
            
            # Extract and process images
            images = {}
            for img in page.query_selector_all("img"):
                src = img.get_attribute("src")
                if not src:
                    continue
                    
                # Keep data URIs as is
                if src.startswith("data:image"):
                    images[src] = src
                # Download and convert other images if they look like CAPTCHAs
                elif "captcha" in src.lower() or re.search(r'captcha', src, re.I):
                    try:
                        img_bytes = requests.get(
                            src,
                            headers={"Referer": url},
                            timeout=10
                        ).content
                        images[src] = "data:image/png;base64," + base64.b64encode(img_bytes).decode('utf-8')
                    except Exception as e:
                        print(f"Failed to download image {src}: {e}")
                        
            return html, images
            
        finally:
            page.close()
    
    def detect_captcha(self, html: str) -> bool:
        """Check if the page likely contains a CAPTCHA.
        
        Args:
            html: The page HTML content
            
        Returns:
            True if CAPTCHA is detected, False otherwise
        """
        soup = BeautifulSoup(html, "html.parser")
        
        # Common CAPTCHA indicators
        captcha_patterns = [
            r"captcha",
            r"verify.*human",
            r"prove.*human",
            r"are you a robot",
            r"not.*robot"
        ]
        
        # Check text content
        text = soup.get_text().lower()
        if any(re.search(pattern, text, re.I) for pattern in captcha_patterns):
            return True
            
        # Check for CAPTCHA-related elements
        for elem in soup.find_all(["img", "input", "form", "div"]):
            if any(re.search(pattern, str(elem), re.I) for pattern in captcha_patterns):
                return True
                
        return False 