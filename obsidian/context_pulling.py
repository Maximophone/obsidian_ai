from integrations.html_to_markdown import HTMLToMarkdown
from obsidian.file_utils import resolve_file_path, get_file_contents, remove_frontmatter
import os

# Initialize HTML to Markdown converter
html_to_md = HTMLToMarkdown()


def insert_file_ref(fname: str = "", subfolder: str = "", typ: str = "document") -> str:
    """
    Insert a reference to a file in the AI context.
    
    Args:
        fname (str): Filename
        subfolder (str): Subfolder to search within each search path
        typ (str): Type of document
    
    Returns:
        str: Formatted file reference
    """
    resolved_path = resolve_file_path(fname, subfolder)
    
    if not resolved_path:
        return f"Error: Cannot find file {fname}"
    
    file_name = os.path.basename(resolved_path)
    contents = get_file_contents(resolved_path)

    if typ=="prompt":
        # we remove the frontmatter, and insert the prompt as is
        try:
            contents = remove_frontmatter(contents)
        except IndexError:
            contents = contents
        return contents
    
    return f"<{typ}><filename>{file_name}</filename>\n<contents>{contents}</contents></{typ}>"


def fetch_url_content(url: str) -> str:
    """
    Fetch and convert URL content to markdown.
    
    Args:
        url (str): URL to fetch
        
    Returns:
        str: Markdown content
    """
    try:
        return html_to_md.convert_url(url)
    except Exception as e:
        return f"Error fetching URL: {str(e)}"
