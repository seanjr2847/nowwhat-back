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
    
    return f"""# # 범용 체크리스트 질문 생성 프롬프트

## 역할
당신은 사용자의 목표 달성을 위한 맞춤형 체크리스트 생성 전문가입니다. 다양한 도메인과 목표에 적응하여 핵심 정보를 수집하는 질문을 설계합니다.

## 입력 정보
```
사용자 정보:
- 목표: {goal}
- 선택한 의도: {intent_title}
- 거주 국가: {user_country}
- 사용 언어: {user_language}
- 국가별 맞춤화: {country_context}
- 언어별 맞춤화: {language_context}
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
- **중급 (4개 질문)**: 위 3개 + 방식/스타일
- **고급 (5개 질문)**: 위 4개 + 경험수준/제약조건

### 3. 질문 타입별 사용 기준

#### single 타입
- **사용 시기**: 하나만 선택해야 하는 상호배타적 옵션
- **예**: 주요 목표, 우선순위, 기간 선택

#### multiple 타입  
- **사용 시기**: 여러 개를 동시에 선택 가능한 옵션
- **예**: 선호하는 방법들, 고려사항들, 관심 분야들

#### text 타입
- **사용 시기**: 개인별로 매우 다른 구체적 정보
- **예**: 특별한 제약사항, 구체적인 목표 설명, 개인적 배경

### 4. required 필드 사용 기준
- **true (필수)**: 체크리스트 생성에 반드시 필요한 핵심 정보
  - 시간 프레임, 주요 목표, 예산/자원
- **false (선택)**: 있으면 더 나은 맞춤화가 가능하지만 없어도 기본 체크리스트 생성 가능
  - 선호사항, 추가 세부사항, 경험 수준

### 5. 언어 및 국가별 맞춤화 가이드
- **언어별 맞춤화 **: 
  - 질문과 선택지를 해당 언어의 문화적 뉘앙스에 맞게 조정
  - 격식체/비격식체 선택, 문화적으로 적절한 표현 사용
  
- **국가별 맞춤화 **:
  - 해당 국가의 관습, 법규, 일반적 관행 반영
  - 예: 운동 목표 → 미국은 마일/파운드, 한국은 km/kg 단위 사용

### 6. 선택지 설계 원칙
- 상호배타적: 겹치지 않는 명확한 구분
- 포괄적: 대부분의 사용자 상황 커버
- 현실적: 실제로 선택 가능한 옵션들
- 4개 선택지 권장 (최소 3개, 최대 5개)

## 출력 형식 및 예시

### 상 복잡도 예시 (5개 질문)
```json
{{
  "questions": [
    {{
      "id": "q1",
      "text": "창업하려는 분야는 무엇인가요?",
      "type": "single",
      "options": [
        {{"id": "opt_tech", "text": "IT/기술", "value": "tech"}},
        {{"id": "opt_service", "text": "서비스업", "value": "service"}},
        {{"id": "opt_product", "text": "제품 판매", "value": "product"}},
        {{"id": "opt_consulting", "text": "컨설팅/교육", "value": "consulting"}}
      ],
      "required": true
    }},
    {{
      "id": "q2",
      "text": "투자 가능한 초기 자본은?",
      "type": "single",
      "options": [
        {{"id": "opt_10M", "text": "1천만원 미만", "value": "10M"}},
        {{"id": "opt_10_50M", "text": "1천-5천만원", "value": "10-50M"}},
        {{"id": "opt_50_100M", "text": "5천만-1억원", "value": "50-100M"}},
        {{"id": "opt_100M_plus", "text": "1억원 이상", "value": "100M+"}}
      ],
      "required": true
    }},
    {{
      "id": "q3",
      "text": "창업 준비 기간은?",
      "type": "single",
      "options": [
        {{"id": "opt_3months", "text": "3개월 이내", "value": "3months"}},
        {{"id": "opt_6months", "text": "6개월", "value": "6months"}},
        {{"id": "opt_1year", "text": "1년", "value": "1year"}},
        {{"id": "opt_flexible", "text": "유연하게", "value": "flexible"}}
      ],
      "required": true
    }},
    {{
      "id": "q4",
      "text": "현재 준비된 것들을 모두 선택하세요",
      "type": "multiple",
      "options": [
        {{"id": "opt_idea", "text": "사업 아이디어", "value": "idea"}},
        {{"id": "opt_team", "text": "팀/파트너", "value": "team"}},
        {{"id": "opt_location", "text": "사업장", "value": "location"}},
        {{"id": "opt_network", "text": "고객 네트워크", "value": "network"}}
      ],
      "required": false
    }},
    {{
      "id": "q5",
      "text": "특별한 제약사항이나 고려사항이 있다면 설명해주세요",
      "type": "text",
      "placeholder": "예: 현재 직장 병행, 가족 부양, 특정 지역 제한 등",
      "required": false
    }}
  ]
}}
```

반드시 위 JSON 형식만 출력하세요. 다른 텍스트나 설명은 포함하지 마세요."""
