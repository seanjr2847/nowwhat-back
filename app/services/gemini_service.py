import json
import asyncio
from typing import List, Dict, Optional
import google.generativeai as genai
from app.core.config import settings
from app.schemas.nowwhat import IntentOption
from app.schemas.questions import Question, Option
import logging
import uuid

logger = logging.getLogger(__name__)

# Gemini API 설정
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)

class GeminiService:
    def __init__(self):
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
        
    async def analyze_intent(self, goal: str, user_country: Optional[str] = None) -> List[IntentOption]:
        """사용자 목표를 분석하여 4가지 의도 옵션 생성"""
        try:
            prompt = self._create_prompt(goal, user_country)
            
            # 3회 재시도 로직
            for attempt in range(3):
                try:
                    response = await self._call_gemini_api(prompt)
                    intents = self._parse_response(response)
                    
                    if len(intents) == 4:
                        return intents
                    else:
                        logger.warning(f"Gemini returned {len(intents)} intents instead of 4 (attempt {attempt + 1})")
                        
                except Exception as e:
                    logger.error(f"Gemini API call failed (attempt {attempt + 1}): {str(e)}")
                    if attempt < 2:  # 마지막 시도가 아니면 지연 후 재시도
                        await asyncio.sleep(2 ** attempt)  # exponential backoff
                    
            # 모든 재시도 실패시 기본 템플릿 반환
            logger.warning("All Gemini API attempts failed, using default template")
            return self._get_default_template()
            
        except Exception as e:
            logger.error(f"Intent analysis failed: {str(e)}")
            return self._get_default_template()

    async def generate_questions(
        self, 
        goal: str, 
        intent_title: str, 
        user_country: Optional[str] = None
    ) -> List[Question]:
        """선택된 의도에 따른 맞춤 질문 생성 (3-5개)"""
        try:
            prompt = self._create_questions_prompt(goal, intent_title, user_country)
            
            # 3회 재시도 로직
            for attempt in range(3):
                try:
                    response = await self._call_gemini_api(prompt)
                    questions = self._parse_questions_response(response)
                    
                    if 3 <= len(questions) <= 5:
                        return questions
                    else:
                        logger.warning(f"Gemini returned {len(questions)} questions instead of 3-5 (attempt {attempt + 1})")
                        
                except Exception as e:
                    logger.error(f"Gemini questions API call failed (attempt {attempt + 1}): {str(e)}")
                    if attempt < 2:
                        await asyncio.sleep(2 ** attempt)
                    
            # 모든 재시도 실패시 캐시된 질문 템플릿 반환
            logger.warning("All Gemini questions API attempts failed, using cached template")
            return self._get_cached_questions_template(intent_title)
            
        except Exception as e:
            logger.error(f"Question generation failed: {str(e)}")
            return self._get_cached_questions_template(intent_title)

    def _create_questions_prompt(self, goal: str, intent_title: str, user_country: Optional[str] = None) -> str:
        """질문 생성용 프롬프트 생성"""
        country_context = self._get_country_context(user_country)
        
        return f"""당신은 개인 맞춤형 체크리스트 생성을 위한 질문 설계 전문가입니다.

사용자 정보:
- 목표: "{goal}"
- 선택한 의도: "{intent_title}"
- 거주 국가: {user_country or "알 수 없음"}
- 국가별 맞춤화: {country_context}

이 사용자가 목표를 달성하기 위해 필요한 핵심 정보를 수집하는 3-5개의 질문을 생성하세요.

질문 생성 규칙:
1. 첫 번째 질문: 시기/기간 파악 (언제)
2. 두 번째 질문: 규모/인원 파악 (누구와)
3. 세 번째 질문: 선호도/관심사 (무엇을)
4. 네 번째 질문: 예산/자원 (얼마나)
5. 다섯 번째 질문: 특별 요구사항 (기타)

질문 유형:
- "multiple": 명확한 선택지가 있을 때 (4개 옵션 고정)
- "text": 개인별 차이가 큰 정보일 때

응답 형식 (JSON):
[
  {{
    "id": "q_001",
    "text": "구체적인 질문 내용",
    "type": "multiple",
    "options": [
      {{"id": "opt_1", "text": "선택지1", "value": "value1"}},
      {{"id": "opt_2", "text": "선택지2", "value": "value2"}},
      {{"id": "opt_3", "text": "선택지3", "value": "value3"}},
      {{"id": "opt_4", "text": "선택지4", "value": "value4"}}
    ],
    "required": true
  }}
]

중요: 정확히 3-5개만 생성하고, 유효한 JSON 형식으로 응답하세요."""

    def _get_country_context(self, user_country: Optional[str]) -> str:
        """국가별 맞춤 컨텍스트"""
        contexts = {
            "KR": "한국 거주자 기준, 한국 문화와 환경 고려",
            "US": "미국 거주자 기준, 미국 문화와 환경 고려", 
            "JP": "일본 거주자 기준, 일본 문화와 환경 고려",
            "CN": "중국 거주자 기준, 중국 문화와 환경 고려"
        }
        return contexts.get(user_country, "글로벌 기준")

    def _parse_questions_response(self, response: str) -> List[Question]:
        """Gemini 질문 응답 파싱"""
        try:
            # JSON 부분만 추출
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            questions_data = json.loads(response)
            
            if not isinstance(questions_data, list):
                raise ValueError("Response is not a list")
                
            questions = []
            for item in questions_data:
                # 필수 필드 확인
                if not all(key in item for key in ["id", "text", "type", "required"]):
                    raise ValueError("Missing required fields in question")
                
                # options 처리
                options = None
                if item["type"] == "multiple" and "options" in item:
                    options = [
                        Option(
                            id=opt["id"],
                            text=opt["text"], 
                            value=opt["value"]
                        ) for opt in item["options"]
                    ]
                
                questions.append(Question(
                    id=item["id"],
                    text=item["text"],
                    type=item["type"],
                    options=options,
                    required=item["required"]
                ))
                
            return questions
            
        except Exception as e:
            raise Exception(f"Failed to parse Gemini questions response: {str(e)}")

    def _get_cached_questions_template(self, intent_title: str) -> List[Question]:
        """의도별 캐시된 질문 템플릿"""
        templates = {
            "여행 계획": [
                Question(
                    id="q_duration",
                    text="여행 기간은 얼마나 되나요?",
                    type="multiple",
                    options=[
                        Option(id="opt_3days", text="2박 3일", value="3days"),
                        Option(id="opt_5days", text="4박 5일", value="5days"),
                        Option(id="opt_1week", text="1주일", value="1week"),
                        Option(id="opt_longer", text="1주일 이상", value="longer")
                    ],
                    required=True
                ),
                Question(
                    id="q_companions",
                    text="누구와 함께 가시나요?",
                    type="multiple",
                    options=[
                        Option(id="opt_alone", text="혼자", value="alone"),
                        Option(id="opt_couple", text="연인/배우자와", value="couple"),
                        Option(id="opt_family", text="가족과", value="family"),
                        Option(id="opt_friends", text="친구들과", value="friends")
                    ],
                    required=True
                ),
                Question(
                    id="q_activities",
                    text="주로 하고 싶은 활동은 무엇인가요?",
                    type="multiple",
                    options=[
                        Option(id="opt_sightseeing", text="관광/명소 탐방", value="sightseeing"),
                        Option(id="opt_food", text="맛집 탐방", value="food"),
                        Option(id="opt_shopping", text="쇼핑", value="shopping"),
                        Option(id="opt_culture", text="문화 체험", value="culture")
                    ],
                    required=True
                )
            ],
            "계획 세우기": [
                Question(
                    id="q_timeline",
                    text="언제까지 계획을 완성하고 싶으신가요?",
                    type="multiple",
                    options=[
                        Option(id="opt_1week", text="1주일 내", value="1week"),
                        Option(id="opt_1month", text="1달 내", value="1month"),
                        Option(id="opt_3months", text="3달 내", value="3months"),
                        Option(id="opt_flexible", text="유연하게", value="flexible")
                    ],
                    required=True
                ),
                Question(
                    id="q_priority",
                    text="가장 중요하게 생각하는 것은?",
                    type="multiple",
                    options=[
                        Option(id="opt_time", text="시간 효율성", value="time"),
                        Option(id="opt_cost", text="비용 절약", value="cost"),
                        Option(id="opt_quality", text="품질/만족도", value="quality"),
                        Option(id="opt_convenience", text="편의성", value="convenience")
                    ],
                    required=True
                )
            ]
        }
        
        return templates.get(intent_title, self._get_default_questions_template())

    def _get_default_questions_template(self) -> List[Question]:
        """기본 질문 템플릿"""
        return [
            Question(
                id="q_when",
                text="언제까지 이 목표를 달성하고 싶으신가요?",
                type="multiple",
                options=[
                    Option(id="opt_1week", text="1주일 내", value="1week"),
                    Option(id="opt_1month", text="1달 내", value="1month"),
                    Option(id="opt_3months", text="3달 내", value="3months"),
                    Option(id="opt_6months", text="6달 내", value="6months")
                ],
                required=True
            ),
            Question(
                id="q_resources",
                text="이 목표를 위해 투자할 수 있는 자원은?",
                type="multiple", 
                options=[
                    Option(id="opt_time", text="주로 시간", value="time"),
                    Option(id="opt_money", text="주로 돈", value="money"),
                    Option(id="opt_both", text="시간과 돈 모두", value="both"),
                    Option(id="opt_minimal", text="최소한만", value="minimal")
                ],
                required=True
            ),
            Question(
                id="q_priority",
                text="가장 중요하게 생각하는 것은?",
                type="multiple",
                options=[
                    Option(id="opt_speed", text="빠른 달성", value="speed"),
                    Option(id="opt_quality", text="높은 품질", value="quality"),
                    Option(id="opt_cost", text="비용 절약", value="cost"),
                    Option(id="opt_balance", text="균형잡힌 접근", value="balance")
                ],
                required=True
            )
        ]
    
    def _create_prompt(self, goal: str, user_country: Optional[str] = None) -> str:
        """Gemini API용 프롬프트 생성"""
        # TODO: 언어 및 국가설정 나오면 붙이기기
        country_info = f"거주 국가: {user_country}" if user_country else ""
        
        return f"""  
# 사용자 의도 파악을 위한 4가지 선택지 생성 프롬프트

## 목적
사용자가 애매하거나 추상적인 목표를 말했을 때, 그들이 실제로 원하는 것이 무엇인지 파악하기 위한 4가지 구체적인 선택지를 생성합니다. 이를 통해 사용자의 진짜 의도를 빠르게 파악하고 맞춤형 도움을 제공할 수 있습니다.

## 의도 분류 기준
1. **"어떻게 할까?"** - 시작점/접근법 (첫 발걸음, 방법론)
2. **"뭐가 필요해?"** - 준비물/조건 (리소스, 도구, 환경)
3. **"뭘 선택할까?"** - 구체적 옵션 (종류, 타입, 스타일)
4. **"뭘 조심할까?"** - 주의점/현실적 팁 (장애물, 실수 방지)

## 선택지 생성 규칙
* 4가지 분류에서 각각 1개씩 선택지 생성
* 같은 카테고리로 치우치지 않기 (예: 모두 "종류" 관련 X)
* 각 선택지는 다른 관점에서 사용자를 도와야 함
* 중복되거나 유사한 선택지 금지

## 선택 우선순위 (상황별)
* 긴급한 느낌 → 즉시 실행 가능한 것 우선
* 계획적인 느낌 → 준비 단계부터 차근차근
* 고민이 많은 느낌 → 선택지와 장단점 중심
* 경험 공유 느낌 → 주의사항과 팁 중심

## 사용자 수준 반영
* 각 선택지에 난이도 암시적 포함
* 초보자 → 중급자 → 고급자 순서로 배치
* 예: "처음 시작" → "기초 다지기" → "실력 향상" → "전문가 되기"

## 응답 형식 규칙
* title: 핵심 키워드 2-3개 (5-10자)
* description: 구체적인 선택지를 포함한 질문 (20-35자)
* 의미 전달이 우선, 글자 수는 가이드라인
* 너무 전문적이거나 기술적인 용어 피하기

## description 작성 가이드
* 구체적인 선택지나 범위 제시 (예: "10만원? 100만원?")
* 2-3개의 대표적인 옵션 나열 (예: "독학? 부트캠프? 온라인?")
* 사용자의 상황을 구체화하는 질문 (예: "혼자? 함께?")
* 실질적인 도움 제안 (예: "~도움 필요하신가요?")
* 단순 질문보다는 선택 가능한 옵션 제시

## 특수 상황 처리
* **너무 구체적인 경우**: 
  - 예: "파이썬으로 웹 크롤러 만들기" 
  - 대응: 더 큰 맥락 제시 (프로젝트 목적, 활용 방안 등)
  
* **너무 추상적인 경우**:
  - 예: "행복해지고 싶어"
  - 대응: 가장 보편적인 해석 3가지 + 명확화 질문 1개
  
* **다중 목표인 경우**:
  - 예: "운동도 하고 공부도 하고 싶어"
  - 대응: 우선순위 파악 또는 통합적 접근 제시

## 단계별 사고 과정 (Chain of Thought)

### 1단계: 사용자 의도 분석
- 사용자의 목표가 무엇인지 파악
- 추상적 정도 판단 (매우 구체적 ↔ 매우 추상적)
- 긴급도/계획성 파악
- 예상 사용자 수준 (초보자/경험자)

### 2단계: 4가지 분류별 선택지 구상
- "어떻게 할까?" → 가능한 시작 방법들 나열 후 가장 대표적인 3-4개 선택
- "뭐가 필요해?" → 필수/선택 리소스 구분 후 핵심 요소 추출
- "뭘 선택할까?" → 주요 카테고리나 타입 분류
- "뭘 조심할까?" → 흔한 실수나 주의사항 중 가장 중요한 것 선택

### 3단계: 선택지 차별화 검증
- 각 선택지가 다른 관점인지 확인
- 중복되는 내용 제거
- 사용자가 명확히 구분할 수 있는지 검토

### 4단계: Description 구체화
- 각 선택지별로 2-3개의 구체적 옵션 포함
- 사용자가 바로 고를 수 있는 선택지인지 확인
- 전문용어를 쉬운 표현으로 변경

### 5단계: 최종 JSON 생성
- 위 과정을 거쳐 정제된 4개 선택지를 JSON 형식으로 출력

## 응답 형식 (JSON)
```json
[
  {
    "title": "핵심 키워드 2-3개로 구성된 제목",
    "description": "구체적인 옵션을 포함한 질문",
    "icon": "관련 이모지"
  }
]
```

## 예시 1
사용자 입력: "여행 가고 싶어"
응답:
```json
[
  {
    "title": "여행 계획",
    "description": "혼자 갈까요, 함께 갈까요?",
    "icon": "📝"
  },
  {
    "title": "여행 예산",
    "description": "10만원? 100만원? 그 이상?",
    "icon": "💰"
  },
  {
    "title": "여행지 선택",
    "description": "국내 여행? 해외 여행?",
    "icon": "🗺️"
  },
  {
    "title": "여행 주의사항",
    "description": "여행 보험이나 준비물 궁금하신가요?",
    "icon": "⚠️"
  }
]
```

## 예시 2
사용자 입력: "운동 시작하고 싶어"
응답:
```json
[
  {
    "title": "운동 시작법",
    "description": "홈트? 헬스장? 야외 운동?",
    "icon": "🚀"
  },
  {
    "title": "운동 준비물",
    "description": "운동복, 기구 추천 필요하신가요?",
    "icon": "🎒"
  },
  {
    "title": "운동 종류",
    "description": "근력? 유산소? 스트레칭?",
    "icon": "🏃"
  },
  {
    "title": "부상 예방",
    "description": "준비운동, 자세 교정 알려드릴까요?",
    "icon": "⚠️"
  }
]
```

## 예시 3
사용자 입력: "프로그래밍 배우고 싶어"
응답:
```json
[
  {
    "title": "학습 방법",
    "description": "독학? 부트캠프? 온라인 강의?",
    "icon": "📚"
  },
  {
    "title": "개발 환경",
    "description": "컴퓨터 사양, 프로그램 설치 도움 필요?",
    "icon": "💻"
  },
  {
    "title": "언어 선택",
    "description": "웹? 앱? 데이터 분석? 게임?",
    "icon": "🔤"
  },
  {
    "title": "초보자 실수",
    "description": "포기하지 않는 학습 전략 필요하신가요?",
    "icon": "⚠️"
  }
]
```

## 예시 4
사용자 입력: "돈 벌고 싶어"
응답:
```json
[
  {
    "title": "수익 창출법",
    "description": "부업? 창업? 투자? 이직?",
    "icon": "💡"
  },
  {
    "title": "필요 자원",
    "description": "시간? 자본금? 기술? 인맥?",
    "icon": "🔧"
  },
  {
    "title": "수익 모델",
    "description": "단기 수익? 장기 투자? 패시브 인컴?",
    "icon": "💸"
  },
  {
    "title": "위험 관리",
    "description": "사기 예방, 세금 처리 정보 필요하신가요?",
    "icon": "⚠️"
  }
]
```

## 예시 5
사용자 입력: "건강해지고 싶어"
응답:
```json
[
  {
    "title": "건강 관리법",
    "description": "식단? 운동? 수면? 스트레스 관리?",
    "icon": "🌱"
  },
  {
    "title": "건강 검진",
    "description": "병원 검진, 체크리스트 필요하신가요?",
    "icon": "🏥"
  },
  {
    "title": "생활 습관",
    "description": "금연? 금주? 다이어트? 규칙적 생활?",
    "icon": "🎯"
  },
  {
    "title": "주의 신호",
    "description": "놓치기 쉬운 건강 적신호 알려드릴까요?",
    "icon": "⚠️"
  }
]
```

## 최종 검증
□ 4개 선택지가 각각 다른 분류에 속하는가?
□ 선택지끼리 겹치는 부분이 없는가?
□ description에 구체적인 옵션이 포함되어 있는가?
□ 사용자가 바로 선택할 수 있을 만큼 명확한가?
□ 너무 전문적이거나 어려운 용어는 없는가?
□ 각 선택지가 실질적인 다음 단계로 이어지는가?

---

## 사용 방법

사용자 입력: "{goal}"

**응답 생성 과정**:
1. 먼저 사용자의 "{goal}"를 분석하여 의도와 상황을 파악합니다
2. 4가지 분류 기준에 따라 각각의 선택지를 구상합니다
3. 선택지들이 서로 겹치지 않고 명확히 구분되는지 확인합니다
4. 각 description에 구체적인 옵션 2-3개를 포함시킵니다
5. 최종적으로 아래 JSON 형식으로 출력합니다

```json
[
  {
    "title": "분류1에 해당하는 제목",
    "description": "구체적 옵션을 포함한 질문",
    "icon": "적절한 이모지"
  },
  {
    "title": "분류2에 해당하는 제목",
    "description": "구체적 옵션을 포함한 질문",
    "icon": "적절한 이모지"
  },
  {
    "title": "분류3에 해당하는 제목",
    "description": "구체적 옵션을 포함한 질문",
    "icon": "적절한 이모지"
  },
  {
    "title": "분류4에 해당하는 제목",
    "description": "구체적 옵션을 포함한 질문",
    "icon": "적절한 이모지"
  }
]
```

**중요**: 
- 위 5단계를 거쳐 신중하게 선택지를 생성하세요
- 정확히 4개의 선택지만 생성하고, 각 선택지가 4가지 분류 기준에 맞게 하나씩 배치되도록 하세요
- description은 반드시 구체적인 선택 옵션을 2-3개 이상 포함해야 합니다
- 사용자가 즉시 선택할 수 있는 명확한 옵션을 제시하세요
"""

    async def _call_gemini_api(self, prompt: str) -> str:
        """Gemini API 호출"""
        try:
            response = await asyncio.to_thread(
                self.model.generate_content, 
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=1000,
                    temperature=0.7,
                )
            )
            return response.text
        except Exception as e:
            raise Exception(f"Gemini API call failed: {str(e)}")
    
    def _parse_response(self, response: str) -> List[IntentOption]:
        """Gemini 응답 파싱"""
        try:
            # JSON 부분만 추출 (마크다운 코드 블록 제거)
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            intents_data = json.loads(response)
            
            if not isinstance(intents_data, list):
                raise ValueError("Response is not a list")
                
            intents = []
            for item in intents_data:
                if not all(key in item for key in ["title", "description", "icon"]):
                    raise ValueError("Missing required fields in intent")
                    
                intents.append(IntentOption(
                    title=item["title"],
                    description=item["description"],
                    icon=item["icon"]
                ))
                
            return intents
            
        except Exception as e:
            raise Exception(f"Failed to parse Gemini response: {str(e)}")
    
    def _get_default_template(self) -> List[IntentOption]:
        """기본 의도 템플릿"""
        return [
            IntentOption(
                title="계획 세우기",
                description="목표를 달성하기 위한 구체적인 계획을 세우고 싶으신가요?",
                icon="📋"
            ),
            IntentOption(
                title="준비하기",
                description="필요한 것들을 준비하고 체크리스트를 만들고 싶으신가요?",
                icon="✅"
            ),
            IntentOption(
                title="정보 찾기",
                description="관련된 정보를 조사하고 알아보고 싶으신가요?",
                icon="🔍"
            ),
            IntentOption(
                title="바로 시작하기",
                description="지금 당장 실행할 수 있는 방법을 알고 싶으신가요?",
                icon="🚀"
            )
        ]

# 서비스 인스턴스
gemini_service = GeminiService() 