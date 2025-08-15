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
    steps: List[str]  # Changed from tips to steps - actionable guide
    contacts: List[ContactInfo]
    links: List[LinkInfo]
    price: Optional[str] = None
    location: Optional[str] = None

def get_search_prompt(checklist_item: str, user_country: str = None, user_language: str = None) -> str:
    """Generate English search prompt for checklist items (responseSchema compatible)"""
    current_year = datetime.now().year
    
    return f"""Provide specific action steps to complete "{checklist_item}".

Instructions:
1. Understand what "{checklist_item}" is
2. Write 3-5 sequential action steps needed to complete it
3. Each step should start with "Step 1:", "Step 2:", etc.
4. Make each step specific and actionable

Example 1:
Item: "Get travel insurance"
Response: {{
  "steps": [
    "Step 1: Check your travel dates and destination to determine coverage needs (medical, luggage, etc.)",
    "Step 2: Visit 2-3 insurance company websites to compare travel insurance products",
    "Step 3: Compare premiums and coverage limits to select the best product",
    "Step 4: Complete the online application form and make payment",
    "Step 5: Download the insurance certificate and save it to your phone for the trip"
  ],
  "contacts": [],
  "links": [{{"title": "Travel Insurance Comparison", "url": "https://example.com"}}],
  "price": "From $3 per day",
  "location": null
}}

Example 2:
Item: "Create workout routine"
Response: {{
  "steps": [
    "Step 1: Assess your current fitness level and available workout time slots",
    "Step 2: Schedule 3-4 workout days per week and add them as recurring calendar events",
    "Step 3: Plan specific exercise types for each day (Monday-upper body, Wednesday-lower body, Friday-full body)",
    "Step 4: Start with light intensity and increase by 10% each week",
    "Step 5: Download a workout tracking app and record your daily exercise and progress"
  ],
  "contacts": [],
  "links": [],
  "price": null,
  "location": null
}}

Example 3:
Item: "Write a resume"
Response: {{
  "steps": [
    "Step 1: Read the job posting to understand requirements and preferred qualifications",
    "Step 2: List your work experience and projects from the past 3 years in chronological order",
    "Step 3: Add specific achievements and metrics for each role (sales increase %, projects completed, etc.)",
    "Step 4: Choose a resume template and input personal info, experience, education, and certifications",
    "Step 5: Save the completed resume as PDF with filename 'YourName_Position_Resume'"
  ],
  "contacts": [],
  "links": [{{"title": "Resume Templates", "url": "https://example.com"}}],
  "price": null,
  "location": null
}}

Action steps for "{checklist_item}":
- Each step starts with "Step N:"
- Use specific action verbs (visit, create, download, etc.)
- Sequential steps that can be followed to completion

Context: {user_country or 'Korea'}, {current_year}

Critical Rules:
- Include only actionable steps in the steps array
- Each step must start with "Step N:" as a complete sentence
- NEVER use JSON structure or special characters
- NEVER use markdown code blocks"""