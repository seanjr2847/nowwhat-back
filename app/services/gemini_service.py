import json
import asyncio
from typing import List, Dict, Optional
import google.generativeai as genai
from app.core.config import settings
from app.schemas.nowwhat import IntentOption
from app.schemas.questions import Question, Option
from app.services.prompt_loader import prompt_loader
import logging
import uuid

logger = logging.getLogger(__name__)
# Gemini 서비스 디버깅을 위해 임시로 DEBUG 레벨 설정
logger.setLevel(logging.DEBUG)
# 콘솔 핸들러 추가 (이미 있다면 무시됨)
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

# Gemini API 설정
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)
    logger.info(f"Gemini API configured with key: {settings.GEMINI_API_KEY[:10]}...{settings.GEMINI_API_KEY[-4:]}")
else:
    logger.error("GEMINI_API_KEY not found in settings")

class GeminiService:
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            logger.error("Cannot initialize GeminiService: GEMINI_API_KEY not set")
            raise ValueError("GEMINI_API_KEY not configured")
        
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
        logger.info(f"GeminiService initialized with model: {settings.GEMINI_MODEL}")
        
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
        
        return prompt_loader.get_questions_generation_prompt(
            goal=goal,
            intent_title=intent_title,
            user_country=user_country,
            country_context=country_context
        )

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
            # 응답이 비어있는지 확인
            if not response or not response.strip():
                logger.warning("Gemini returned empty response")
                raise ValueError("Empty response from Gemini")
            
            # JSON 부분만 추출
            response = response.strip()
            logger.debug(f"Raw Gemini response: {response[:200]}...")  # 디버깅용
            
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            # 빈 응답 재확인
            if not response:
                logger.warning("Response became empty after cleaning")
                raise ValueError("Empty response after cleaning")
            
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
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}, Response: '{response[:500]}'")
            raise Exception(f"Failed to parse Gemini questions response: Invalid JSON - {str(e)}")
        except Exception as e:
            logger.error(f"Questions parsing error: {str(e)}, Response: '{response[:500] if 'response' in locals() else 'N/A'}'")
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
        return prompt_loader.get_intent_analysis_prompt(goal, user_country)

    async def _call_gemini_api(self, prompt: str) -> str:
        """Gemini API 호출"""
        try:
            logger.debug(f"Sending prompt to Gemini (length: {len(prompt)} chars)")
            response = await asyncio.to_thread(
                self.model.generate_content, 
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=4096,  # 더 큰 증가
                    temperature=0.7,
                    top_p=0.8,
                    top_k=40
                )
            )
            
            # 응답 상태 확인
            if not response:
                logger.error("Gemini returned None response")
                raise Exception("Gemini returned None response")
            
            # 응답 객체 구조 확인
            logger.debug(f"Gemini response type: {type(response)}")
            logger.debug(f"Gemini response attributes: {dir(response)}")
            
            # Safety rating 및 finish reason 확인
            if hasattr(response, 'candidates') and response.candidates:
                for i, candidate in enumerate(response.candidates):
                    finish_reason = candidate.finish_reason if hasattr(candidate, 'finish_reason') else 'N/A'
                    logger.debug(f"Candidate {i} finish_reason: {finish_reason}")
                    
                    # finish_reason 해석
                    if finish_reason == 2:
                        logger.warning("Response was truncated due to MAX_TOKENS limit - consider increasing max_output_tokens")
                    elif finish_reason == 3:
                        logger.warning("Response was blocked by safety filters")
                    elif finish_reason == 4:
                        logger.warning("Response was blocked due to recitation concerns")
                    
                    if hasattr(candidate, 'safety_ratings'):
                        logger.debug(f"Candidate {i} safety_ratings: {candidate.safety_ratings}")
            
            if not hasattr(response, 'text'):
                logger.error(f"Gemini response has no text attribute: {type(response)}")
                # 대안으로 candidates에서 텍스트 추출 시도
                if hasattr(response, 'candidates') and response.candidates:
                    for candidate in response.candidates:
                        if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                            for part in candidate.content.parts:
                                if hasattr(part, 'text') and part.text:
                                    logger.debug(f"Found text in candidate.content.parts: {part.text[:100]}...")
                                    response_text = part.text
                                    break
                    else:
                        raise Exception("Gemini response has no text attribute and no text in candidates")
                else:
                    raise Exception("Gemini response has no text attribute")
            else:
                response_text = response.text
            
            logger.debug(f"Raw Gemini response (length: {len(response_text) if response_text else 0}): '{response_text}'")
            
            if not response_text or not response_text.strip():
                logger.error("Gemini returned empty or whitespace-only response")
                raise Exception("Gemini returned empty response")
                
            return response_text
            
        except Exception as e:
            logger.error(f"Gemini API call error details: {str(e)}")
            raise Exception(f"Gemini API call failed: {str(e)}")
    
    def _parse_response(self, response: str) -> List[IntentOption]:
        """Gemini 응답 파싱"""
        try:
            logger.debug(f"Intent parsing - Raw response: '{response[:200]}...' (total length: {len(response)})")
            
            # JSON 부분만 추출 (마크다운 코드 블록 제거)
            response = response.strip()
            logger.debug(f"Intent parsing - After strip: '{response[:200]}...'")
            
            if response.startswith("```json"):
                response = response[7:]
                logger.debug("Intent parsing - Removed ```json prefix")
            if response.endswith("```"):
                response = response[:-3]
                logger.debug("Intent parsing - Removed ``` suffix")
            response = response.strip()
            
            logger.debug(f"Intent parsing - Final JSON to parse: '{response[:200]}...'")
            
            if not response:
                logger.error("Intent parsing - Response became empty after cleaning")
                raise ValueError("Empty response after cleaning")
            
            intents_data = json.loads(response)
            logger.debug(f"Intent parsing - Successfully parsed JSON with {len(intents_data) if isinstance(intents_data, list) else 'non-list'} items")
            
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