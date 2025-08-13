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
    
    return f"""Follow these steps to provide information about "{checklist_item}":

Step 1: First understand what "{checklist_item}" means
Step 2: Think of 3-5 specific actions the user can actually take
Step 3: Write each action as an independent complete sentence
Step 4: Format as JSON following the examples below

Example 1:
Search: "Get travel insurance"
Thinking process: Travel insurance covers risks during trips. User needs to select product, check coverage, and complete purchase.
Response: {{
  "tips": [
    "Compare coverage limits based on your travel duration and destination",
    "Ensure medical expenses and lost luggage coverage are included",
    "Check if your credit card already provides travel insurance benefits",
    "Disclose any pre-existing medical conditions before purchasing"
  ],
  "contacts": [],
  "links": [{{"title": "Travel Insurance Comparison", "url": "https://example.com"}}],
  "price": "From $3 per day",
  "location": null
}}

Example 2:
Search: "Create workout routine"
Thinking process: Workout routine is a regular exercise plan. User needs to set schedule, choose exercises, adjust intensity, and track progress.
Response: {{
  "tips": [
    "Schedule 3-4 regular workout sessions per week and mark them in your calendar",
    "Balance strength training and cardio exercises in your routine",
    "Start with appropriate intensity for your fitness level and gradually increase",
    "Include proper stretching before and after workouts to prevent injuries",
    "Track your progress weekly to monitor improvements"
  ],
  "contacts": [],
  "links": [],
  "price": null,
  "location": null
}}

Example 3:
Search: "Write a resume"
Thinking process: Resume is essential document for job applications. User needs structure, content emphasis, and proper formatting.
Response: {{
  "tips": [
    "List work experience in reverse chronological order for better readability",
    "Include specific achievements and quantifiable results for credibility",
    "Highlight key skills relevant to the position you're applying for",
    "Keep it concise and clear within two pages maximum"
  ],
  "contacts": [],
  "links": [{{"title": "Resume Templates", "url": "https://example.com"}}],
  "price": null,
  "location": null
}}

Now for "{checklist_item}":
1. First understand what this is
2. Think of specific actionable steps
3. Respond in the exact JSON format as the examples above

Context: {user_country or 'Korea'}, {current_year}

Important: Do not include the thinking process, only provide the final JSON response."""