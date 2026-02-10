"""
Response parser - extracts structured content blocks from agent responses.
Separates markdown text from HTML components.
"""

import re
from typing import List

from nft_chatbot.models.chat import ContentBlock


# Special markers for structured tool responses
HTML_START = "<!--HTML_COMPONENT::"
HTML_END = "::END_HTML-->"


class ResponseParser:
    """
    Parse agent response into structured content blocks.
    
    Agent tools return content with special markers:
    <!--HTML_COMPONENT::grid-->
    <div>...</div>
    ::END_HTML-->
    
    This parser extracts HTML components and separates markdown text.
    """
    
    def parse(self, raw_response: str) -> List[ContentBlock]:
        """Parse raw response into content blocks."""
        blocks = []
        
        # Pattern to find HTML components with markers
        pattern = rf'{re.escape(HTML_START)}(\w+)-->(.*?){re.escape(HTML_END)}'
        
        last_end = 0
        for match in re.finditer(pattern, raw_response, re.DOTALL):
            # Add text before this HTML component
            text_before = raw_response[last_end:match.start()].strip()
            if text_before:
                blocks.append(ContentBlock(
                    type="text",
                    markdown=text_before
                ))
            
            # Add HTML component
            template_type = match.group(1)  # "grid", "table", "details"
            html_content = match.group(2).strip()
            blocks.append(ContentBlock(
                type="html_component",
                html=html_content,
                template=template_type
            ))
            
            last_end = match.end()
        
        # Add any remaining text after last HTML component
        remaining_text = raw_response[last_end:].strip()
        if remaining_text:
            blocks.append(ContentBlock(
                type="text",
                markdown=remaining_text
            ))
        
        # If no HTML components found, return single text block
        if not blocks:
            blocks.append(ContentBlock(
                type="text",
                markdown=raw_response
            ))
        
        return blocks
    
    @staticmethod
    def wrap_html(html: str, template_type: str) -> str:
        """Wrap HTML content with markers for parsing."""
        return f"{HTML_START}{template_type}-->\n{html}\n{HTML_END}"
