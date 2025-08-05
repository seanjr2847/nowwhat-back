"""질문 생성을 위한 Gemini 프롬프트와 응답 형식 (한글 버전)"""
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
    """질문 생성용 프롬프트 생성 (한글)"""
    # 국가 정보가 있으면 국가 맞춤 검색 프롬프트 추가
    country_search_prompt = ""
    if user_country and user_country != "정보 없음":
        country_search_prompt = f"\n\n해당 국가에 맞는 국가 정보 위주로 검색해주세요. {user_country}"
    
    return f"""# 범용 체크리스트 질문 생성 프롬프트

## 역할
당신은 사용자의 목표 달성을 위한 맞춤형 체크리스트 생성 전문가입니다. 다양한 도메인과 목표에 적응하여 핵심 정보를 수집하는 질문을 설계합니다.{country_search_prompt}

## 입력 정보
```
사용자 정보:
- 목표: "{goal}"
- 선택한 의도: "{intent_title}"
- 거주 국가: "{user_country}"
- 사용 언어: "{user_language}"
- 국가별 맞춤화: "{country_context}"
- 언어별 맞춤화: "{language_context}"
```

## 작업
사용자의 목표와 선택한 의도를 분석하여, 실행 가능한 체크리스트를 만들기 위해 필요한 핵심 질문을 생성하세요.

## 목표 복잡도 분석 및 질문 개수 결정
먼저 목표의 복잡도를 평가하고, 그에 따라 질문 개수를 결정하세요:

### 복잡도 평가 기준
- **하 (단순)**: 단일 활동, 명확한 목표, 짧은 기간
  - 예: "물 많이 마시기", "일찍 잠자리에 들기"
  - 질문 개수: 3개

- **중 (보통)**: 여러 단계, 선택지 존재, 중간 기간
  - 예: "운동 시작하기", "새로운 취미 배우기"
  - 질문 개수: 4개

- **상 (복잡)**: 다단계 프로세스, 많은 변수, 장기간
  - 예: "창업하기", "새로운 언어 마스터하기"
  - 질문 개수: 5개

## 질문 설계 원칙

### 1. 필수 정보 카테고리 (모든 복잡도 공통)
1. **시간 프레임**: 언제까지, 얼마나 자주
2. **자원/예산**: 투자 가능한 시간, 돈, 노력
3. **우선순위**: 가장 중요하게 생각하는 것

### 2. 복잡도별 추가 카테고리
**중급 (4개 질문)**: 위 3개 + 방식/스타일
**고급 (5개 질문)**: 위 4개 + 경험수준/제약조건

### 3. 질문 형태 가이드라인
- **객관식**: 선택지가 명확한 경우 (시간, 예산, 방식 등)
- **주관식**: 개인적 상황이나 세부사항 (구체적 목표, 특별한 제약 등)

### 4. 선택지 설계 원칙
- 상호배타적: 겹치지 않는 명확한 구분
- 포괄적: 대부분의 사용자 상황 커버
- 현실적: 실제로 선택 가능한 옵션들
- 4개 선택지 권장 (최소 3개, 최대 5개)

## 출력 형식
아래 JSON 스키마에 맞춰 응답하세요:

```json
{{
  "questions": [
    {{
      "id": "q1",
      "text": "언제까지 이 목표를 달성하고 싶으신가요?",
      "type": "multiple",
      "options": [
        {{
          "id": "opt_1week",
          "text": "1주일 내",
          "value": "1week"
        }},
        {{
          "id": "opt_1month", 
          "text": "1개월 내",
          "value": "1month"
        }},
        {{
          "id": "opt_3months",
          "text": "3개월 내", 
          "value": "3months"
        }},
        {{
          "id": "opt_flexible",
          "text": "유연하게",
          "value": "flexible"
        }}
      ],
      "required": true
    }}
  ]
}}
```

반드시 위 JSON 형식만 출력하세요. 다른 텍스트나 설명은 포함하지 마세요."""