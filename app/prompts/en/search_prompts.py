"""English search functionality for Gemini prompts and response formats"""
import json
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel

# Response schema definition
class ContactInfo(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None

class LinkInfo(BaseModel):
    title: str
    url: str

class SearchResponse(BaseModel):
    tips: List[str]
    contacts: List[ContactInfo]
    links: List[LinkInfo]
    price: Optional[str] = None
    location: Optional[str] = None

def get_search_prompt(checklist_item: str, user_country: str = None, user_language: str = None) -> str:
    """Generate English search prompt for checklist items (responseSchema compatible)"""
    current_year = datetime.now().year
    
    return f"""Search for "{checklist_item}" and provide EXACTLY 3-5 separate tips.

Requirements:
- tips: MUST be an array of 3-5 separate strings, each 15-50 words only
- contacts: array of contact objects with name/phone/email
- links: array of link objects with title/url
- price: single price string if found
- location: single location string if found

Each tip MUST be:
✓ ONE specific actionable step
✓ Maximum 50 words  
✓ No markdown, no bullet points
✓ Complete sentence

Context: {user_country or 'Korea'}, {current_year}, {user_language or 'English'}

CRITICAL: Return exactly 3-5 separate tips, not one long text."""