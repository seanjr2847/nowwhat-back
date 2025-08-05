"""Intent analysis Gemini prompts and response formats (English version)"""
import json
from typing import Dict, List, Optional
from pydantic import BaseModel

# Response schema definition
class IntentOption(BaseModel):
    title: str
    description: str
    icon: str

class IntentAnalysisResponse(BaseModel):
    intents: List[IntentOption]

def get_intent_analysis_prompt(goal: str, country_info: str = "", language_info: str = "") -> str:
    """Intent analysis prompt generation (English)"""
    # 국가 정보가 있으면 국가 맞춤 검색 프롬프트 추가
    country_search_prompt = ""
    if country_info:
        # country_info에서 국가명 추출 (예: "User country: US" -> "US")
        country_name = country_info.split(":")[-1].strip() if ":" in country_info else country_info.strip()
        country_search_prompt = f"\n\nPlease search primarily for country-specific information relevant to {country_name}."
    
    return f"""# 4-Option Intent Analysis Prompt

## Purpose
When users provide vague or abstract goals, generate 4 specific options to understand what they actually want. This helps quickly identify the user's true intent and provide personalized assistance.{country_search_prompt}

## Intent Classification Criteria
1. **"How to start?"** - Starting point/approach (first steps, methodology)
2. **"What do I need?"** - Preparation/conditions (resources, tools, environment)
3. **"What to choose?"** - Specific options (types, styles, variants)
4. **"What to watch out for?"** - Precautions/practical tips (obstacles, mistake prevention)

## Option Generation Rules
* Generate 1 option from each of the 4 categories
* Avoid bias toward same category (e.g., all "type" related X)
* Each option should help users from different perspectives
* Prohibit duplicate or similar options

## Selection Priority (by situation)
* Urgent feeling → Prioritize immediately actionable items
* Planning-oriented → Step-by-step from preparation stage
* Lots of concerns → Focus on options and pros/cons
* Experience sharing → Focus on precautions and tips

## User Level Reflection
* Implicitly include difficulty level in each option
* Arrange in order: Beginner → Intermediate → Advanced
* Example: "Getting started" → "Building foundation" → "Skill improvement" → "Becoming expert"

## Response Format Rules
* title: 2-3 core keywords (5-15 characters)
* description: Specific question including options (15-40 characters)
* Meaning delivery is priority, character count is guideline
* Avoid overly technical or specialized terms

## User Goal
"{goal}"

{country_info}
{language_info}

## Output Format
Generate exactly 4 options according to JSON schema:

```json
{{
  "intents": [
    {{
      "title": "Getting Started",
      "description": "How do I begin this journey?",
      "icon": "🚀"
    }},
    {{
      "title": "Preparation", 
      "description": "What do I need to prepare?",
      "icon": "📋"
    }},
    {{
      "title": "Selection",
      "description": "Which type suits me best?",
      "icon": "🎯"
    }},
    {{
      "title": "Precautions",
      "description": "What should I be careful about?",
      "icon": "⚠️"
    }}
  ]
}}
```

Only output the above JSON format. Do not include any other text or explanations."""