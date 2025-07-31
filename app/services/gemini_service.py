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
        country_info = f"거주 국가: {user_country}" if user_country else ""
        
        return f"""당신은 사용자의 막연한 목표를 명확한 의도로 분류하는 전문가입니다.

사용자 입력: "{goal}"
{country_info}

사용자의 애매한 목표를 구체화하기 위해 가능한 4가지 의도를 파악하세요.

의도 분류 기준:
1. **시작/전환** - 목표를 처음 시작하거나 현재 상황에서 전환하는 방법
2. **핵심 요소** - 목표 달성에 필수적인 핵심 요소나 수단 (수입, 도구, 기술 등)
3. **구체적 선택** - 실제 선택해야 하는 구체적 옵션들 (장소, 시기, 종류 등)
4. **현실적 고려사항** - 실행 시 맞닥뜨릴 실무적 문제나 장애물 해결

선택 우선순위:
- 초보자가 가장 많이 궁금해하는 순서
- 추상적 → 구체적 순서
- 준비 → 실행 → 유지 단계 순서

응답 형식 (JSON):
[
  {
    "title": "핵심 키워드 2-3개로 구성된 제목",
    "description": "~에 대해 알고 싶으신가요? / ~을 찾고 계신가요? 형식",
    "icon": "관련 이모지"
  }
]

예시:
- "여행 가고 싶어" → 여행지 추천 / 예산 계획 / 일정 짜기 / 준비물 체크
- "운동 시작하고 싶어" → 운동 종류 선택 / 루틴 만들기 / 헬스장 찾기 / 식단 관리

중요: 정확히 4개만 생성하고, 각 의도가 서로 겹치지 않도록 하세요."""

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