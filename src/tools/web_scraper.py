"""
Web Scraper Tool Module

This module provides tools for fetching HTML content from websites and handling CAPTCHAs.
It uses Playwright for browser automation to handle JavaScript-heavy sites and detect CAPTCHA challenges.
"""

from typing import Dict, Tuple, Optional
import base64
import re
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Page

class WebScraperTool:
    """
    A web scraping tool that uses Playwright to fetch HTML content and detect CAPTCHAs.
    
    This class implements a context manager interface for better resource management,
    automatically handling browser initialization and cleanup.
    
    Attributes:
        _playwright: The Playwright instance
        _browser: The browser instance used for scraping
    """
    
    def __init__(self):
        """Initialize the web scraper tool with uninitialized Playwright."""
        self._playwright = None
        self._browser = None
    
    def __enter__(self):
        """Start the Playwright browser when entering the context."""
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.firefox.launch(headless=True)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure browser resources are cleaned up when exiting the context."""
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
    
    def fetch_page_content(self, url: str) -> Tuple[str, Dict[str, str]]:
        """
        Fetch page content and extract important images using Playwright.
        
        Args:
            url: The URL to scrape
            
        Returns:
            Tuple containing:
            - The HTML content as a string
            - A dictionary mapping image URLs to base64-encoded data URIs
            
        Raises:
            Exception: If the page fails to load or other errors occur
        """
        if not self._browser:
            raise ValueError("Browser not initialized. Use with WebScraperTool() as scraper: ...")
            
        page = self._browser.new_page()
        try:
            response = page.goto(url, timeout=60000)
            if not response:
                raise Exception(f"Failed to load {url}")
                
            html = page.content()
            
            # Extract and process images
            images = self._extract_images(page, url)
                        
            return html, images
            
        finally:
            page.close()
    
    def _extract_images(self, page: Page, url: str) -> Dict[str, str]:
        """
        Extract important images from the page, prioritizing CAPTCHA images.
        
        Args:
            page: The Playwright page object
            url: The source URL (used for referer header)
            
        Returns:
            Dictionary mapping image URLs to base64 data URIs
        """
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
                    
        return images
    
    def detect_captcha(self, html: str) -> bool:
        """
        Check if the page likely contains a CAPTCHA challenge.
        
        Args:
            html: The HTML content to analyze
            
        Returns:
            True if a CAPTCHA is detected, False otherwise
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
        
        # Check text content for CAPTCHA-related phrases
        text = soup.get_text().lower()
        if any(re.search(pattern, text, re.I) for pattern in captcha_patterns):
            return True
            
        # Check for CAPTCHA-related elements in HTML
        for elem in soup.find_all(["img", "input", "form", "div"]):
            if any(re.search(pattern, str(elem), re.I) for pattern in captcha_patterns):
                return True
        
        # Check image sources and alt text for CAPTCHA indicators
        for img in soup.find_all("img"):
            src = img.get("src", "")
            alt = img.get("alt", "")
            if "captcha" in src.lower() or "captcha" in alt.lower():
                return True
                
        return False 