"""질문 생성을 위한 Gemini 프롬프트와 응답 형식"""
import json
from typing import Dict, List, Optional
from pydantic import BaseModel

# 응답 스키마 정의
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

def get_questions_generation_prompt(goal: str, intent_title: str, user_country: str, country_context: str) -> str:
    """질문 생성용 프롬프트 생성"""
    return f"""# 범용 체크리스트 질문 생성 프롬프트

## 역할
당신은 사용자의 목표 달성을 위한 맞춤형 체크리스트 생성 전문가입니다. 다양한 도메인과 목표에 적응하여 핵심 정보를 수집하는 질문을 설계합니다.

## 입력 정보
```
사용자 정보:
- 목표: "{goal}"
- 선택한 의도: "{intent_title}"
- 거주 국가: "{user_country}"
- 국가별 맞춤화: "{country_context}"
```

## 작업
사용자의 목표와 선택한 의도를 분석하여, 실행 가능한 체크리스트를 만들기 위해 필요한 3-10개의 핵심 질문을 생성하세요.

## 질문 개수 가이드
- **기본 원칙**: 3-10개 범위 내에서 목표 복잡도에 따라 조절
- **최소 3개**: 의미 있는 체크리스트 생성을 위한 최소 정보
- **최대 10개**: 사용자 피로도를 고려한 실용적 상한선
- **권장사항**: 
  - 대부분의 목표는 4-7개가 적절
  - 꼭 필요한 정보만 수집
  - 사용자가 지치지 않도록 고려

## 질문 생성 사고 과정 (Chain of Thought)

### 1단계: 도메인 식별
- 사용자의 목표가 어떤 카테고리에 속하는지 파악
- 선택한 의도가 도메인 내에서 어떤 단계인지 확인

### 2단계: 핵심 정보 매핑
- 해당 도메인에서 필수적인 정보 목록 작성
- 의도에 맞는 구체적 정보 요구사항 도출

### 3단계: 우선순위 설정
- 가장 중요한 정보부터 순서대로 배치
- 상황 파악 → 목표 구체화 → 자원 확인 → 제약 식별 순서 고려

### 4단계: 질문 타입 결정
- 표준화 가능한 답변은 multiple choice
- 개인차가 큰 답변은 text input

### 5단계: 국가별 조정
- 해당 국가의 특수성 반영
- 현지 관습, 법규, 인프라 고려

### 6단계: 최종 검증
- 질문들이 목표 달성에 직접적으로 도움이 되는지 확인
- 중복이나 불필요한 질문 제거

## 적응형 질문 설계 전략

### 도메인 분류
- **활동/경험형**: 여행, 운동, 취미, 이벤트
- **학습/성장형**: 교육, 기술 습득, 자격증
- **창작/구축형**: 사업, 프로젝트, 콘텐츠 제작
- **문제해결형**: 건강, 재정, 관계 개선
- **구매/선택형**: 제품 구매, 서비스 선택

### 도메인별 핵심 정보

**활동/경험형**
- 실행 시기와 기간
- 참여 인원과 대상
- 선호하는 스타일
- 예산과 제약사항

**학습/성장형**
- 현재 수준과 목표 수준
- 학습 가능 시간과 환경
- 구체적 목적
- 선호 학습 방식

**창작/구축형**
- 목표 규모와 범위
- 보유 자원과 역량
- 타임라인
- 성공 기준

**문제해결형**
- 현재 상황 진단
- 변화 목표
- 가용 자원
- 제약 조건

**구매/선택형**
- 사용 목적과 환경
- 예산 범위
- 필수 기능/요구사항
- 비교 기준

## 질문 설계 원칙
1. **계층적 구조**: 일반적인 것에서 구체적인 것으로 진행
2. **직접성**: 목표 달성에 직접 필요한 정보만 수집
3. **명확성**: 애매모호한 표현 지양, 구체적 선택지 제공
4. **적응성**: 도메인과 의도에 맞는 맞춤형 질문

## 국가별 맞춤화 가이드
- **법규/규제**: 해당 국가의 관련 법규나 제도 고려
- **문화적 맥락**: 현지 관습과 선호도 반영
- **인프라**: 이용 가능한 서비스나 시설 고려
- **언어/용어**: 현지에서 통용되는 표현 사용
- **경제적 맥락**: 현지 물가와 경제 수준 반영

## 질문 유형 선택 기준
- **multiple**: 표준화된 범주가 있고, 대부분 사용자가 비슷한 선택을 하는 경우
- **text**: 개인차가 크거나, 구체적인 정보가 필요한 경우

## 출력 형식
```json
[
  {
    "id": "q_001",
    "text": "구체적인 질문 (목표와 의도에 맞게)",
    "type": "multiple|text",
    "options": [  // multiple인 경우만
      {{{"id": "opt_1", "text": "선택지1", "value": "value1"}}},
      {{{"id": "opt_2", "text": "선택지2", "value": "value2"}}},
      {{{"id": "opt_3", "text": "선택지3", "value": "value3"}}},
      {{{"id": "opt_4", "text": "선택지4", "value": "value4"}}}
    ],
    "placeholder": "답변 가이드", // text인 경우만
    "required": true|false
  }
]
```

## 다양한 도메인 예시

### 예시 1: 창업 (창작/구축형)
**입력**: 
- goal: "온라인 쇼핑몰 시작하고 싶어"
- intent_title: "사업 모델 구체화"
- user_country: "한국"

**출력**:
```json
[
  {
    "id": "q_001",
    "text": "어떤 제품을 판매할 계획이신가요?",
    "type": "text",
    "placeholder": "예: 수제 액세서리, 해외 직구 상품, 디지털 콘텐츠 등",
    "required": true
  },
  {
    "id": "q_002",
    "text": "초기 투자 가능한 자본금은 어느 정도인가요?",
    "type": "multiple",
    "options": [
      {{"id": "opt_1", "text": "100만원 미만", "value": "under_1m"}},
      {{"id": "opt_2", "text": "100-500만원", "value": "1m_5m"}},
      {{"id": "opt_3", "text": "500-1000만원", "value": "5m_10m"}},
      {{"id": "opt_4", "text": "1000만원 이상", "value": "over_10m"}}
    ],
    "required": true
  },
  {
    "id": "q_003",
    "text": "언제까지 첫 매출을 목표로 하시나요?",
    "type": "multiple",
    "options": [
      {{"id": "opt_1", "text": "1개월 내", "value": "1month"}},
      {{"id": "opt_2", "text": "3개월 내", "value": "3months"}},
      {{"id": "opt_3", "text": "6개월 내", "value": "6months"}},
      {{"id": "opt_4", "text": "1년 내", "value": "1year"}}
    ],
    "required": true
  },
  {
    "id": "q_004",
    "text": "온라인 판매 경험이나 관련 지식이 있으신가요?",
    "type": "multiple",
    "options": [
      {{"id": "opt_1", "text": "전혀 없음", "value": "none"}},
      {{"id": "opt_2", "text": "기초 지식만", "value": "basic"}},
      {{"id": "opt_3", "text": "일부 경험 있음", "value": "some"}},
      {{"id": "opt_4", "text": "충분한 경험", "value": "experienced"}}
    ],
    "required": true
  }
]
```

### 예시 2: 건강 개선 (문제해결형)
**입력**:
- goal: "체중 감량하고 싶어"
- intent_title: "식단 관리 방법"
- user_country: "한국"

**출력**:
```json
[
  {
    "id": "q_001",
    "text": "현재 식습관에서 가장 개선이 필요한 부분은 무엇인가요?",
    "type": "multiple",
    "options": [
      {{"id": "opt_1", "text": "과식/폭식", "value": "overeating"}},
      {{"id": "opt_2", "text": "야식/간식", "value": "snacking"}},
      {{"id": "opt_3", "text": "불규칙한 식사", "value": "irregular"}},
      {{"id": "opt_4", "text": "영양 불균형", "value": "unbalanced"}}
    ],
    "required": true
  },
  {
    "id": "q_002",
    "text": "목표 감량 체중과 기간은 어떻게 되나요?",
    "type": "text",
    "placeholder": "예: 3개월 동안 5kg 감량",
    "required": true
  },
  {
    "id": "q_003",
    "text": "식단 조절에 영향을 줄 수 있는 환경적 요인이 있나요?",
    "type": "multiple",
    "options": [
      {{"id": "opt_1", "text": "직장인(외식 잦음)", "value": "office_worker"}},
      {{"id": "opt_2", "text": "교대근무", "value": "shift_work"}},
      {{"id": "opt_3", "text": "가족과 식사", "value": "family_meals"}},
      {{"id": "opt_4", "text": "특별한 제약 없음", "value": "no_constraints"}}
    ],
    "required": true
  }
]
```

### 예시 3: 이직 준비 (문제해결형 + 성장형)
**입력**:
- goal: "이직하고 싶어"
- intent_title: "포트폴리오 준비"
- user_country: "미국"

**출력**:
```json
[
  {
    "id": "q_001",
    "text": "어떤 분야로 이직을 준비하시나요?",
    "type": "text",
    "placeholder": "예: Backend Developer, UI/UX Designer, Marketing Manager 등",
    "required": true
  },
  {
    "id": "q_002",
    "text": "현재 경력은 어느 정도 되시나요?",
    "type": "multiple",
    "options": [
      {{"id": "opt_1", "text": "Entry Level (0-1년)", "value": "entry"}},
      {{"id": "opt_2", "text": "Junior (1-3년)", "value": "junior"}},
      {{"id": "opt_3", "text": "Mid-level (3-7년)", "value": "mid"}},
      {{"id": "opt_4", "text": "Senior (7년+)", "value": "senior"}}
    ],
    "required": true
  },
  {
    "id": "q_003",
    "text": "포트폴리오에 포함할 수 있는 프로젝트나 성과가 있나요?",
    "type": "multiple",
    "options": [
      {{"id": "opt_1", "text": "없음(새로 만들어야 함)", "value": "none"}},
      {{"id": "opt_2", "text": "1-2개", "value": "few"}},
      {{"id": "opt_3", "text": "3-5개", "value": "some"}},
      {{"id": "opt_4", "text": "5개 이상", "value": "many"}}
    ],
    "required": true
  },
  {
    "id": "q_004",
    "text": "목표 연봉 범위는 어떻게 되나요?",
    "type": "multiple",
    "options": [
      {{"id": "opt_1", "text": "$50k-80k", "value": "50k_80k"}},
      {{"id": "opt_2", "text": "$80k-120k", "value": "80k_120k"}},
      {{"id": "opt_3", "text": "$120k-180k", "value": "120k_180k"}},
      {{"id": "opt_4", "text": "$180k+", "value": "180k_plus"}}
    ],
    "required": true
  },
  {
    "id": "q_005",
    "text": "언제까지 이직을 완료하고 싶으신가요?",
    "type": "multiple",
    "options": [
      {{"id": "opt_1", "text": "1개월 내", "value": "1month"}},
      {{"id": "opt_2", "text": "3개월 내", "value": "3months"}},
      {{"id": "opt_3", "text": "6개월 내", "value": "6months"}},
      {{"id": "opt_4", "text": "구체적 계획 없음", "value": "flexible"}}
    ],
    "required": true
  }
]
```

### 예시 4: 복잡한 프로젝트 - 해외 이민 (문제해결형 + 창작형)
**입력**:
- goal: "캐나다로 이민 가고 싶어"
- intent_title: "이민 준비 계획"
- user_country: "한국"

**출력**:
```json
[
  {
    "id": "q_001",
    "text": "어떤 이민 프로그램을 고려하고 계신가요?",
    "type": "multiple",
    "options": [
      {{"id": "opt_1", "text": "기술이민(Express Entry)", "value": "express_entry"}},
      {{"id": "opt_2", "text": "주정부 이민(PNP)", "value": "pnp"}},
      {{"id": "opt_3", "text": "투자이민", "value": "investment"}},
      {{"id": "opt_4", "text": "아직 모르겠음", "value": "undecided"}}
    ],
    "required": true
  },
  {
    "id": "q_002",
    "text": "영어 능력 시험(IELTS/CELPIP) 점수가 있으신가요?",
    "type": "multiple",
    "options": [
      {{"id": "opt_1", "text": "있음(CLB 7 이상)", "value": "high"}},
      {{"id": "opt_2", "text": "있음(CLB 7 미만)", "value": "medium"}},
      {{"id": "opt_3", "text": "준비 중", "value": "preparing"}},
      {{"id": "opt_4", "text": "아직 없음", "value": "none"}}
    ],
    "required": true
  },
  {
    "id": "q_003",
    "text": "현재 직업과 경력은 어떻게 되시나요?",
    "type": "text",
    "placeholder": "예: 소프트웨어 개발자 5년, 간호사 3년 등",
    "required": true
  },
  {
    "id": "q_004",
    "text": "학력은 어떻게 되시나요?",
    "type": "multiple",
    "options": [
      {{"id": "opt_1", "text": "고졸 이하", "value": "high_school"}},
      {{"id": "opt_2", "text": "전문학사/학사", "value": "bachelor"}},
      {{"id": "opt_3", "text": "석사", "value": "master"}},
      {{"id": "opt_4", "text": "박사", "value": "phd"}}
    ],
    "required": true
  },
  {
    "id": "q_005",
    "text": "가족 구성은 어떻게 되나요?",
    "type": "multiple",
    "options": [
      {{"id": "opt_1", "text": "독신", "value": "single"}},
      {{"id": "opt_2", "text": "부부", "value": "couple"}},
      {{"id": "opt_3", "text": "부부+자녀", "value": "family"}},
      {{"id": "opt_4", "text": "기타", "value": "other"}}
    ],
    "required": true
  },
  {
    "id": "q_006",
    "text": "이민 준비 예산은 어느 정도 되시나요?",
    "type": "multiple",
    "options": [
      {{"id": "opt_1", "text": "3천만원 미만", "value": "under_30m"}},
      {{"id": "opt_2", "text": "3천-5천만원", "value": "30m_50m"}},
      {{"id": "opt_3", "text": "5천만원-1억", "value": "50m_100m"}},
      {{"id": "opt_4", "text": "1억 이상", "value": "over_100m"}}
    ],
    "required": true
  },
  {
    "id": "q_007",
    "text": "언제까지 이민을 완료하고 싶으신가요?",
    "type": "multiple",
    "options": [
      {{"id": "opt_1", "text": "1년 내", "value": "1year"}},
      {{"id": "opt_2", "text": "2년 내", "value": "2years"}},
      {{"id": "opt_3", "text": "3년 내", "value": "3years"}},
      {{"id": "opt_4", "text": "장기 계획", "value": "long_term"}}
    ],
    "required": true
  }
]
```

## 제약사항
- 목표와 의도에 맞지 않는 일반적인 질문 지양
- 도메인 특성을 고려한 맞춤형 질문 생성
- 사용자가 즉시 답할 수 있는 구체적 질문
- 전체 질문 수는 3-10개로 제한 (목표 복잡도에 따라 조절)
- 국가별 특성을 반영한 현지화된 질문과 선택지

## 최종 검증 체크리스트
□ 질문이 목표 달성에 직접적으로 필요한가?
□ 의도(intent_title)와 연관성이 있는가?
□ 사용자가 명확히 이해하고 답할 수 있는가?
□ 국가별 맞춤화가 적절히 반영되었는가?
□ 질문 순서가 논리적인가?
□ 중복되거나 불필요한 질문은 없는가?

---

사용자 입력: {goal}, {intent_title}, {user_country}, {country_context}

**응답 생성 과정**:
1. 목표와 의도를 분석하여 도메인 식별
2. 해당 도메인의 핵심 정보 요구사항 파악
3. 3-10개 범위에서 적절한 질문 개수 결정
4. 우선순위에 따라 질문 배치
5. 국가별 특성 반영하여 현지화
6. 최종 JSON 형식으로 출력"""