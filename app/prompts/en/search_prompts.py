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

class StepInfo(BaseModel):
    order: int
    title: str
    description: str
    estimatedTime: Optional[str] = None
    difficulty: Optional[str] = None

class SearchResponse(BaseModel):
    steps: List[StepInfo]  # Structured step-by-step guide
    contacts: List[ContactInfo]
    links: List[LinkInfo]
    price: Optional[str] = None

def get_search_prompt(checklist_item: str, user_country: str = None, user_language: str = None) -> str:
    """Generate English search prompt for checklist items (responseSchema compatible)"""
    current_year = datetime.now().year
    
    return f"""Provide specific action steps to complete "{checklist_item}". Use Google web search actively to find real, current information.

## Important: Use Real Search Information
Actively utilize Google web search to provide actual information such as:
- **Business/Location related**: Real business names, addresses, phone numbers, hours, pricing
- **Service/Product related**: Currently available services, latest rates, booking methods
- **Location-based info**: Nearby businesses based on user location, regional characteristics
- **Current information**: Latest {current_year} information prioritized

Instructions:
1. Understand what "{checklist_item}" is and search for real information
2. Create 3-5 sequential action steps using actual search results
3. Each step should have: order, title, description, estimatedTime, difficulty
4. Include real contact information and links from search results

Example 1:
Item: "Get travel insurance"
Response: {{
  "steps": [
    {{
      "order": 1,
      "title": "Check travel details",
      "description": "Check your travel dates and destination to determine coverage needs (medical, luggage, etc.)",
      "estimatedTime": "15 minutes",
      "difficulty": "easy"
    }},
    {{
      "order": 2,
      "title": "Compare insurance options",
      "description": "Visit 2-3 insurance company websites to compare travel insurance products",
      "estimatedTime": "30 minutes",
      "difficulty": "easy"
    }},
    {{
      "order": 3,
      "title": "Select best option",
      "description": "Compare premiums and coverage limits to select the best product",
      "estimatedTime": "20 minutes",
      "difficulty": "medium"
    }},
    {{
      "order": 4,
      "title": "Apply and pay",
      "description": "Complete the online application form and make payment",
      "estimatedTime": "15 minutes",
      "difficulty": "easy"
    }},
    {{
      "order": 5,
      "title": "Download certificate",
      "description": "Download the insurance certificate and save it to your phone for the trip",
      "estimatedTime": "5 minutes",
      "difficulty": "easy"
    }}
  ],
  "contacts": [],
  "links": [{{"title": "Travel Insurance Comparison", "url": "https://example.com"}}],
  "price": "From $3 per day"
}}

Example 2:
Item: "Create workout routine"
Response: {{
  "steps": [
    {{
      "order": 1,
      "title": "Assess fitness level",
      "description": "Assess your current fitness level and available workout time slots",
      "estimatedTime": "30 minutes",
      "difficulty": "easy"
    }},
    {{
      "order": 2,
      "title": "Schedule workout days",
      "description": "Schedule 3-4 workout days per week and add them as recurring calendar events",
      "estimatedTime": "15 minutes",
      "difficulty": "easy"
    }},
    {{
      "order": 3,
      "title": "Plan exercise types",
      "description": "Plan specific exercise types for each day (Monday-upper body, Wednesday-lower body, Friday-full body)",
      "estimatedTime": "45 minutes",
      "difficulty": "medium"
    }},
    {{
      "order": 4,
      "title": "Start with light intensity",
      "description": "Start with light intensity and increase by 10% each week",
      "estimatedTime": "ongoing",
      "difficulty": "medium"
    }},
    {{
      "order": 5,
      "title": "Track progress",
      "description": "Download a workout tracking app and record your daily exercise and progress",
      "estimatedTime": "10 minutes",
      "difficulty": "easy"
    }}
  ],
  "contacts": [],
  "links": [],
  "price": null
}}

Example 3:
Item: "Write a resume"
Response: {{
  "steps": [
    {{
      "order": 1,
      "title": "Analyze job requirements",
      "description": "Read the job posting to understand requirements and preferred qualifications",
      "estimatedTime": "20 minutes",
      "difficulty": "easy"
    }},
    {{
      "order": 2,
      "title": "List experience",
      "description": "List your work experience and projects from the past 3 years in chronological order",
      "estimatedTime": "30 minutes",
      "difficulty": "easy"
    }},
    {{
      "order": 3,
      "title": "Add achievements",
      "description": "Add specific achievements and metrics for each role (sales increase %, projects completed, etc.)",
      "estimatedTime": "45 minutes",
      "difficulty": "medium"
    }},
    {{
      "order": 4,
      "title": "Create resume",
      "description": "Choose a resume template and input personal info, experience, education, and certifications",
      "estimatedTime": "1 hour",
      "difficulty": "medium"
    }},
    {{
      "order": 5,
      "title": "Save as PDF",
      "description": "Save the completed resume as PDF with filename 'YourName_Position_Resume'",
      "estimatedTime": "5 minutes",
      "difficulty": "easy"
    }}
  ],
  "contacts": [],
  "links": [{{"title": "Resume Templates", "url": "https://example.com"}}],
  "price": null
}}

Action steps for "{checklist_item}":
- Each step should be a structured object with order, title, description
- Use specific action verbs in descriptions (visit, create, download, etc.)
- Sequential steps that can be followed to completion
- Include estimatedTime (e.g., "15 minutes", "1 hour", "ongoing")
- Include difficulty level (easy, medium, hard)

Context: {user_country or 'Korea'}, {current_year}

Critical Rules:
- Include only actionable steps in the steps array
- Each step must be a complete structured object
- NEVER use JSON structure or special characters in output
- NEVER use markdown code blocks"""