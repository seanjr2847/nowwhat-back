"""Question generation Gemini prompts and response formats (English version)"""
from typing import List
from pydantic import BaseModel


class QuestionOption(BaseModel):
    id: str
    text: str
    value: str

class QuestionResponse(BaseModel):
    id: str
    text: str
    type: str
    options: List[QuestionOption]
    required: bool

class QuestionsListResponse(BaseModel):
    questions: List[QuestionResponse]


def get_questions_generation_prompt(
    goal: str, intent_title: str, user_country: str, user_language: str, 
    country_context: str, language_context: str
) -> str:
    """Question generation prompt (English)"""
    return f"""# Universal Checklist Question Generation Prompt

## Role
You are a personalized checklist generation expert for achieving user goals. You design questions that adapt to various domains and goals to collect essential information.

## Input Information
```
User Information:
- Goal: "{goal}"
- Selected Intent: "{intent_title}"
- Country: "{user_country}"
- Language: "{user_language}"
- Country Context: "{country_context}"
- Language Context: "{language_context}"
```

## Task
Analyze the user's goal and selected intent to generate key questions needed to create an actionable checklist.

## Goal Complexity Analysis & Question Count Decision
First evaluate the goal's complexity and determine the number of questions accordingly:

### Complexity Evaluation Criteria
- **Low (Simple)**: Single activity, clear goal, short timeframe
  - Examples: "drink more water", "go to bed early"
  - Question count: 3

- **Medium (Moderate)**: Multiple steps, choices exist, medium timeframe
  - Examples: "start exercising", "learn a new hobby"
  - Question count: 4

- **High (Complex)**: Multi-stage process, many variables, long timeframe
  - Examples: "start a business", "master a new language"
  - Question count: 5

## Question Design Principles

### 1. Essential Information Categories (Common to all complexity levels)
1. **Time Frame**: When, how often
2. **Resources/Budget**: Investable time, money, effort
3. **Priority**: What matters most

### 2. Additional Categories by Complexity
**Medium (4 questions)**: Above 3 + Method/Style
**High (5 questions)**: Above 4 + Experience Level/Constraints

### 3. Question Type Guidelines
- **Multiple Choice**: When options are clear (time, budget, method, etc.)
- **Text Input**: Personal situations or details (specific goals, special constraints, etc.)

### 4. Option Design Principles
- Mutually Exclusive: Clear, non-overlapping distinctions
- Comprehensive: Cover most user situations
- Realistic: Actually selectable options
- 4 options recommended (minimum 3, maximum 5)

## Output Format
Respond according to the JSON schema below:

```json
{{
  "questions": [
    {{
      "id": "q1",
      "text": "When would you like to achieve this goal?",
      "type": "multiple",
      "options": [
        {{
          "id": "opt_1week",
          "text": "Within 1 week",
          "value": "1week"
        }},
        {{
          "id": "opt_1month", 
          "text": "Within 1 month",
          "value": "1month"
        }},
        {{
          "id": "opt_3months",
          "text": "Within 3 months", 
          "value": "3months"
        }},
        {{
          "id": "opt_flexible",
          "text": "Flexible timeline",
          "value": "flexible"
        }}
      ],
      "required": true
    }}
  ]
}}
```

Only output the above JSON format. Do not include any other text or explanations."""