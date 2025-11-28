"""
Simple HTML to Markdown converter for fetching and converting web content.
"""
import requests
from typing import Optional
try:
    from markdownify import markdownify as md
    HAS_MARKDOWNIFY = True
except ImportError:
    HAS_MARKDOWNIFY = False

try:
    from bs4 import BeautifulSoup
    HAS_BEAUTIFULSOUP = True
except ImportError:
    HAS_BEAUTIFULSOUP = False


class HTMLToMarkdown:
    """Converts HTML content to Markdown format."""
    
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
    
    def convert_url(self, url: str) -> str:
        """
        Fetch a URL and convert its HTML content to Markdown.
        
        Args:
            url: The URL to fetch
            
        Returns:
            Markdown content or error message
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return self.convert_html(response.text)
        except requests.RequestException as e:
            return f"Error fetching URL: {str(e)}"
    
    def convert_html(self, html: str) -> str:
        """
        Convert HTML string to Markdown.
        
        Args:
            html: HTML content to convert
            
        Returns:
            Markdown content
        """
        if HAS_MARKDOWNIFY:
            # Use markdownify if available
            return md(html, heading_style="ATX", strip=['script', 'style'])
        elif HAS_BEAUTIFULSOUP:
            # Fallback to basic BeautifulSoup text extraction
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text
            text = soup.get_text()
            
            # Break into lines and remove leading/trailing space
            lines = (line.strip() for line in text.splitlines())
            
            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            
            # Drop blank lines
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text
        else:
            # Very basic fallback - just strip HTML tags
            import re
            text = re.sub('<[^<]+?>', '', html)
            return text

