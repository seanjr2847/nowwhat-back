import json
import asyncio
from typing import List, Dict, Optional
import google.generativeai as genai
from app.core.config import settings
from app.schemas.nowwhat import IntentOption
from app.schemas.questions import Question, Option
from app.prompts.intent_analysis import get_intent_analysis_prompt, IntentAnalysisResponse
from app.prompts.search_prompts import get_search_prompt, SearchResponse
from app.prompts.checklist_prompts import ChecklistResponse
from app.prompts.questions_generation import get_questions_generation_prompt, QuestionsListResponse
from app.prompts.enhanced_prompts import get_enhanced_knowledge_prompt
import logging
import uuid
from dataclasses import dataclass
from typing import Any
from pydantic import BaseModel

logger = logging.getLogger(__name__)
# Gemini 서비스 디버깅을 위해 임시로 DEBUG 레벨 설정
logger.setLevel(logging.DEBUG)

# Pydantic 모델들은 이제 프롬프트 파일에서 import

@dataclass
class SearchResult:
    """Gemini API 검색 결과"""
    query: str
    content: str
    sources: List[str]
    success: bool
    error_message: Optional[str] = None
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
        
        return get_questions_generation_prompt(
            goal=goal,
            intent_title=intent_title,
            user_country=user_country or "정보 없음",
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
        country_info = f"사용자 거주 국가: {user_country}" if user_country else ""
        return get_intent_analysis_prompt(goal, country_info)

    async def _call_gemini_api_with_search(self, prompt: str) -> str:
        """Gemini API 호출 (공식 Google Search 기능 사용)"""
        try:
            logger.debug(f"Sending search prompt to Gemini (length: {len(prompt)} chars)")
            
            # 공식 Google Search grounding 구현 + Structured Output
            try:
                # Google Search 도구 설정 (공식 방법)
                search_tool = genai.protos.Tool(
                    google_search_retrieval=genai.protos.GoogleSearchRetrieval()
                )
                
                logger.debug("Using Google Search grounding tool with structured output")
                
                # SearchResponse를 Gemini 호환 스키마로 변환
                response_schema = self._create_gemini_compatible_schema()
                
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    prompt,
                    tools=[search_tool],
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=8192,
                        temperature=0.7,
                        top_p=0.8,
                        top_k=40,
                        response_mime_type="application/json",
                        response_schema=response_schema
                    )
                )
                
                logger.debug("Google Search grounding with structured output completed")
                
            except Exception as tool_error:
                logger.warning(f"Google Search grounding failed: {tool_error}")
                logger.debug(f"Error type: {type(tool_error).__name__}")
                logger.info("Trying alternative Google Search implementation")
                
                try:
                    # 대안적 구현 (최신 SDK) + Structured Output
                    from google.generativeai.types import Tool
                    
                    # 최신 SDK의 GoogleSearch 도구
                    search_tool = Tool(
                        google_search_retrieval={}
                    )
                    
                    # SearchResponse를 JSON Schema로 변환
                    response_schema = SearchResponse.model_json_schema()
                    
                    response = await asyncio.to_thread(
                        self.model.generate_content,
                        prompt,
                        tools=[search_tool],
                        generation_config=genai.types.GenerationConfig(
                            max_output_tokens=8192,
                            temperature=0.7,
                            top_p=0.8,
                            top_k=40,
                            response_mime_type="application/json",
                            response_schema=response_schema
                        )
                    )
                    
                except Exception as alt_error:
                    logger.warning(f"Alternative Google Search failed: {alt_error}")
                    logger.debug(f"Alternative error type: {type(alt_error).__name__}")
                    logger.info("Using enhanced knowledge-based prompt")
                    
                    # 웹 검색을 사용할 수 없는 경우, 최신 정보 요청 프롬프트 + Structured Output
                    enhanced_prompt = get_enhanced_knowledge_prompt(prompt)

                    # SearchResponse를 JSON Schema로 변환
                    response_schema = SearchResponse.model_json_schema()
                    
                    response = await asyncio.to_thread(
                        self.model.generate_content,
                        enhanced_prompt,
                        generation_config=genai.types.GenerationConfig(
                            max_output_tokens=8192,
                            temperature=0.7,
                            top_p=0.8,
                            top_k=40,
                            response_mime_type="application/json",
                            response_schema=response_schema
                        )
                    )
            
            # 응답 처리
            if not response:
                logger.error("Gemini returned None response")
                raise Exception("Gemini returned None response")
            
            # grounding metadata 확인 (웹 검색 결과가 있는지)
            if hasattr(response, 'candidates') and response.candidates:
                for candidate in response.candidates:
                    if hasattr(candidate, 'grounding_metadata'):
                        logger.info("Response includes grounding metadata (web search results)")
                        if hasattr(candidate.grounding_metadata, 'search_entry_point'):
                            logger.debug(f"Search entry point: {candidate.grounding_metadata.search_entry_point}")
                        if hasattr(candidate.grounding_metadata, 'grounding_chunks'):
                            logger.debug(f"Found {len(candidate.grounding_metadata.grounding_chunks)} grounding chunks")
            
            # 텍스트 추출
            if not hasattr(response, 'text'):
                logger.debug("Extracting text from candidates...")
                if hasattr(response, 'candidates') and response.candidates:
                    for candidate in response.candidates:
                        if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                            for part in candidate.content.parts:
                                if hasattr(part, 'text') and part.text:
                                    response_text = part.text
                                    break
                    else:
                        raise Exception("No text found in candidates")
                else:
                    raise Exception("No candidates in response")
            else:
                response_text = response.text
            
            logger.debug(f"Gemini search response received (length: {len(response_text) if response_text else 0})")
            
            if not response_text or not response_text.strip():
                logger.error("Gemini returned empty response")
                raise Exception("Gemini returned empty response")
                
            return response_text
            
        except Exception as e:
            logger.error(f"Gemini search API call error: {str(e)}")
            logger.debug(f"Final error type: {type(e).__name__}")
            # 웹 검색 실패시 일반 API로 폴백
            logger.info("Falling back to regular Gemini API without search")
            return await self._call_gemini_api(prompt)
    
    async def _call_gemini_api(self, prompt: str) -> str:
        """Gemini API 호출"""
        try:
            logger.debug(f"Sending prompt to Gemini (length: {len(prompt)} chars)")
            response = await asyncio.to_thread(
                self.model.generate_content, 
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=8192,  # 체크리스트 생성을 위해 더 큰 토큰 수 설정
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
    
    async def parallel_search(self, queries: List[str]) -> List[SearchResult]:
        """여러 검색 쿼리를 병렬로 실행"""
        logger.info("🚀 GEMINI 병렬 검색 시작")
        logger.info(f"   📝 요청된 쿼리 수: {len(queries)}개")
        
        if not queries:
            logger.warning("⚠️  검색 쿼리가 비어있습니다")
            return []
        
        # 쿼리 내용 로깅
        for i, query in enumerate(queries[:5]):  # 처음 5개만 로깅
            logger.info(f"   🔍 쿼리 {i+1}: {query}")
        if len(queries) > 5:
            logger.info(f"   ... 그 외 {len(queries) - 5}개 더")
        
        # 체크리스트 아이템 수에 맞게 모든 쿼리 처리 (API 제한 고려)
        max_concurrent_searches = min(len(queries), settings.MAX_CONCURRENT_SEARCHES)
        limited_queries = queries  # 모든 쿼리를 처리하되 배치로 나누어 실행
        
        if len(queries) > settings.MAX_CONCURRENT_SEARCHES:
            logger.info(f"📦 {len(queries)}개 쿼리를 {settings.MAX_CONCURRENT_SEARCHES}개씩 배치로 처리")
        else:
            logger.info(f"✅ {len(queries)}개 쿼리 모두 병렬 처리")
        
        try:
            logger.info(f"⚡ {len(limited_queries)}개 쿼리 실행 중...")
            
            # 모든 쿼리를 배치로 나누어 병렬 처리
            all_results = []
            batch_size = settings.MAX_CONCURRENT_SEARCHES
            
            for i in range(0, len(limited_queries), batch_size):
                batch_queries = limited_queries[i:i+batch_size]
                logger.info(f"🔄 배치 {i//batch_size + 1}: {len(batch_queries)}개 쿼리 처리 중...")
                
                # 배치별 병렬 검색 실행
                tasks = [self._search_single_query(query) for query in batch_queries]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                all_results.extend(batch_results)
            
            results = all_results
            
            # 예외 처리 및 결과 정리
            processed_results = []
            success_queries = []
            failed_queries = []
            
            for i, result in enumerate(results):
                query = limited_queries[i]
                if isinstance(result, Exception):
                    logger.error(f"❌ 검색 실패 [{i+1}]: '{query[:50]}...' - {str(result)}")
                    processed_results.append(self._create_error_result(query, str(result)))
                    failed_queries.append(query)
                else:
                    if result.success:
                        logger.info(f"✅ 검색 성공 [{i+1}]: '{query[:50]}...' ({len(result.content)}자)")
                        success_queries.append(query)
                    else:
                        logger.warning(f"⚠️  검색 실패 [{i+1}]: '{query[:50]}...' - {result.error_message}")
                        failed_queries.append(query)
                    processed_results.append(result)
            
            success_count = len(success_queries)
            failed_count = len(failed_queries)
            
            # 결과 요약
            logger.info("=" * 60)
            logger.info("📊 GEMINI 검색 결과 요약")
            logger.info("=" * 60)
            logger.info(f"✅ 성공: {success_count}개")
            logger.info(f"❌ 실패: {failed_count}개")
            logger.info(f"📈 성공률: {(success_count/len(limited_queries)*100):.1f}%")
            
            if success_count > 0:
                # 성공한 검색 결과의 내용 길이 통계
                content_lengths = [len(r.content) for r in processed_results if r.success and r.content]
                if content_lengths:
                    avg_length = sum(content_lengths) / len(content_lengths)
                    min_length = min(content_lengths)
                    max_length = max(content_lengths)
                    logger.info(f"📏 응답 길이: 평균 {avg_length:.0f}자 (최소 {min_length}, 최대 {max_length})")
                
                # 성공한 쿼리 몇 개 예시
                for query in success_queries[:3]:
                    logger.info(f"   ✅ '{query[:40]}...'")
            
            if failed_count > 0:
                logger.warning(f"⚠️  실패한 쿼리 {min(3, failed_count)}개 예시:")
                for query in failed_queries[:3]:
                    logger.warning(f"   ❌ '{query[:40]}...'")
            
            logger.info("=" * 60)
            
            return processed_results
            
        except Exception as e:
            logger.error(f"💥 병렬 검색 전체 실패: {str(e)}")
            logger.error(f"   🔄 모든 쿼리를 실패 처리합니다")
            return [self._create_error_result(query, str(e)) for query in limited_queries]
    
    async def _search_single_query(self, query: str) -> SearchResult:
        """단일 검색 쿼리 실행 (Gemini 웹 검색 기능 사용)"""
        start_time = asyncio.get_event_loop().time()
        logger.debug(f"🔍 단일 검색 시작: '{query[:50]}...'")
        
        try:
            # Gemini에게 웹 검색을 통한 최신 정보를 요청하는 프롬프트 생성 (Structured Output 사용)
            prompt = get_search_prompt(query)

            # Gemini API 호출 (웹 검색 활성화)
            response = await self._call_gemini_api_with_search(prompt)
            elapsed = asyncio.get_event_loop().time() - start_time
            
            # 응답 파싱
            result = self._parse_search_response(query, response)
            
            if result.success:
                logger.debug(f"✅ 검색 완료 ({elapsed:.2f}초): {len(result.content)}자 응답")
            else:
                logger.warning(f"⚠️  검색 실패 ({elapsed:.2f}초): {result.error_message}")
            
            return result
                        
        except asyncio.TimeoutError:
            elapsed = asyncio.get_event_loop().time() - start_time
            logger.error(f"⏰ 검색 타임아웃 ({elapsed:.2f}초)")
            logger.error(f"   쿼리: '{query[:50]}...'")
            return self._create_error_result(query, f"Search timeout after {elapsed:.2f}s")
        except Exception as e:
            elapsed = asyncio.get_event_loop().time() - start_time
            logger.error(f"💥 검색 예외 발생 ({elapsed:.2f}초)")
            logger.error(f"   쿼리: '{query[:50]}...'")
            logger.error(f"   오류: {str(e)}")
            return self._create_error_result(query, f"Exception: {str(e)}")
    
    def _parse_search_response(self, query: str, response: str) -> SearchResult:
        """Gemini 검색 응답 파싱 (Structured Output JSON)"""
        try:
            if not response or not response.strip():
                return self._create_error_result(query, "Empty response")
            
            content = response.strip()
            logger.debug(f"Parsing structured output response: {content[:200]}...")
            
            # Structured Output으로 인해 이미 올바른 JSON 형식이어야 함
            try:
                structured_data = json.loads(content)
                logger.info(f"Successfully parsed structured JSON response for query: {query[:50]}...")
                
                # 응답 구조 검증
                if not isinstance(structured_data, dict):
                    logger.warning("Response is not a dictionary, using as-is")
                    structured_data = {"tips": [content], "contacts": [], "links": [], "price": None, "location": None}
                
                # 링크 정보를 sources로 변환
                sources = []
                if "links" in structured_data and isinstance(structured_data["links"], list):
                    for link in structured_data["links"]:
                        if isinstance(link, dict) and "url" in link:
                            sources.append(link["url"])
                        elif isinstance(link, str):
                            sources.append(link)
                
                return SearchResult(
                    query=query,
                    content=json.dumps(structured_data, ensure_ascii=False),
                    sources=sources,
                    success=True
                )
                
            except json.JSONDecodeError as json_err:
                logger.warning(f"Failed to parse structured JSON for query '{query}': {json_err}")
                logger.warning(f"Raw content: {content[:200]}...")
                
                # Structured Output 실패시 폴백
                fallback_data = {
                    "tips": [content] if content else ["정보를 찾을 수 없습니다."],
                    "contacts": [],
                    "links": [],
                    "price": None,
                    "location": None
                }
                
                return SearchResult(
                    query=query,
                    content=json.dumps(fallback_data, ensure_ascii=False),
                    sources=[],
                    success=True
                )
            
        except Exception as e:
            logger.error(f"Failed to parse Gemini structured response for query '{query}': {str(e)}")
            return self._create_error_result(query, f"Parse error: {str(e)}")
    
    def _create_error_result(self, query: str, error_message: str) -> SearchResult:
        """에러 결과 생성"""
        return SearchResult(
            query=query,
            content="",
            sources=[],
            success=False,
            error_message=error_message
        )
    
    def generate_search_queries_from_checklist(
        self,
        checklist_items: List[str],
        goal: str,
        answers: List[Dict[str, Any]]
    ) -> List[str]:
        """체크리스트 아이템 기반으로 검색 쿼리 생성 (Perplexity와 동일한 인터페이스)"""
        
        logger.info("🎯 GEMINI 검색 쿼리 생성 시작")
        logger.info(f"   📋 체크리스트 아이템: {len(checklist_items)}개")
        logger.info(f"   🎯 목표: {goal[:50]}...")
        logger.info(f"   💬 답변: {len(answers)}개")
        
        # 답변에서 핵심 컨텍스트 추출
        answer_context = self._extract_answer_context(answers)
        logger.info(f"   🔍 추출된 컨텍스트: '{answer_context[:80]}...' ({len(answer_context)}자)")
        
        search_queries = []
        
        # 각 체크리스트 아이템을 기반으로 1:1 검색 쿼리 생성
        logger.info(f"   📝 1:1 매핑으로 처리할 아이템: {len(checklist_items)}개")
        
        for i, item in enumerate(checklist_items):
            logger.debug(f"   🔍 아이템 {i+1} 처리: '{item[:50]}...'")
            
            # 아이템에서 핵심 키워드 추출
            core_keywords = self._extract_core_keywords_from_item(item)
            logger.debug(f"      키워드: {core_keywords}")
            
            if core_keywords:
                # 단일 검색 쿼리 생성 (1:1 매핑)
                queries = self._generate_item_specific_queries(core_keywords, answer_context)
                logger.debug(f"      생성된 쿼리: {queries}")
                search_queries.extend(queries)  # 이제 항상 1개만 추가됨
            else:
                # 키워드 추출 실패시 기본 쿼리 생성
                fallback_query = f"{item[:20]} 방법"
                search_queries.append(fallback_query)
                logger.warning(f"      ⚠️  키워드 추출 실패 → 기본 쿼리: '{fallback_query}'")
        
        # 중복 제거하지 않고 순서 유지 (1:1 매핑을 위해)
        unique_queries = search_queries  # 중복 제거 없이 모든 쿼리 유지
        
        logger.info("=" * 50)
        logger.info("📝 1:1 매핑 검색 쿼리 목록")
        logger.info("=" * 50)
        for i, (item, query) in enumerate(zip(checklist_items, unique_queries)):
            logger.info(f"   {i+1:2d}. '{item[:30]}...' → '{query}'")
        logger.info("=" * 50)
        
        logger.info(f"✅ 1:1 쿼리 생성 완료: {len(checklist_items)}개 아이템 → {len(unique_queries)}개 쿼리")
        
        if not unique_queries:
            logger.error("🚨 생성된 검색 쿼리가 없습니다!")
            logger.error("   체크리스트 아이템에서 키워드 추출이 실패했을 수 있습니다.")
        elif len(unique_queries) != len(checklist_items):
            logger.warning(f"⚠️  쿼리 수 불일치: {len(checklist_items)}개 아이템 vs {len(unique_queries)}개 쿼리")
        
        return unique_queries
    
    def _extract_core_keywords_from_item(self, item: str) -> List[str]:
        """체크리스트 아이템에서 검색에 유용한 핵심 키워드 추출 (개선된 버전)"""
        import re
        
        logger.debug(f"키워드 추출 대상: '{item}'")
        
        # 확장된 불용어 리스트
        stopwords = [
            '을', '를', '이', '가', '은', '는', '의', '에', '에서', '와', '과',
            '하기', '하세요', '합니다', '위한', '위해', '통해', '대한', '함께',
            '있는', '있다', '되는', '되다', '같은', '같이', '모든', '각각',
            '검색', '찾기', '확인', '준비', '방법', '추천', '또는', '주변'  # 일반적인 단어들 제외
        ]
        
        # 우선순위 키워드 패턴 (구체적인 것들)
        priority_patterns = [
            # 구체적인 서비스/도구
            r'(?:화상|온라인|모바일)?(?:영어|중국어|일본어|스페인어|프랑스어)(?:앱|어플|수업|강의|교재)',
            r'(?:홈|실내|헬스|피트니스)?(?:트레이닝|운동|요가|필라테스)(?:앱|어플|기구|매트)',
            r'(?:월세|전세|부동산|렌트)?(?:계약|임대|중개|관리)(?:사이트|앱|업체)',
            r'(?:투자|재테크|주식|펀드|적금)(?:앱|플랫폼|상품|계좌)',
            
            # 구체적인 물건/재료
            r'[가-힣]{2,}(?:재료|도구|장비|기구|용품|제품)',
            r'[가-힣]{2,}(?:카드|계좌|보험|통장)',
            r'[가-힣]{2,}(?:비자|여권|항공편|숙박)',
            
            # 구체적인 서비스/기관
            r'[가-힣]{2,}(?:병원|클리닉|센터|학원|학교)',
            r'[가-힣]{2,}(?:은행|증권|보험사|카드사)',
            
            # 구체적인 활동
            r'[가-힣]{2,}(?:시험|자격증|면접|상담)',
            r'[가-힣]{2,}(?:여행|투어|관광|맛집)',
        ]
        
        keywords = []
        
        # 1. 우선순위 패턴으로 구체적 키워드 추출
        for pattern in priority_patterns:
            matches = re.findall(pattern, item)
            for match in matches:
                if match not in keywords:
                    keywords.append(match)
                    logger.debug(f"  우선순위 키워드: '{match}'")
        
        # 2. 영어 키워드 추출 (브랜드명, 서비스명 등)
        english_words = re.findall(r'[A-Za-z]{3,}', item)
        for word in english_words:
            if word.lower() not in ['and', 'the', 'for', 'app'] and word not in keywords:
                keywords.append(word)
                logger.debug(f"  영어 키워드: '{word}'")
        
        # 3. 한글 명사 추출 (3글자 이상, 불용어 제외)
        korean_words = re.findall(r'[가-힣]{3,}', item)
        for word in korean_words:
            if word not in stopwords and word not in keywords:
                # 의미있는 명사인지 추가 검증
                if self._is_meaningful_keyword(word):
                    keywords.append(word)
                    logger.debug(f"  한글 키워드: '{word}'")
        
        # 4. 숫자 포함 키워드 (예: 2인실, 3개월 등)
        number_keywords = re.findall(r'\d+[가-힣]{1,3}', item)
        for keyword in number_keywords:
            if keyword not in keywords:
                keywords.append(keyword)
                logger.debug(f"  숫자 키워드: '{keyword}'")
        
        # 5. 최종 키워드 정제 및 순서 조정
        final_keywords = []
        
        # 우선순위: 구체적 키워드 > 영어 키워드 > 한글 키워드 > 숫자 키워드
        for keyword in keywords:
            if len(final_keywords) >= 4:  # 최대 4개로 제한
                break
            if len(keyword) >= 2 and keyword not in final_keywords:
                final_keywords.append(keyword)
        
        logger.debug(f"  최종 키워드: {final_keywords}")
        return final_keywords
    
    def _is_meaningful_keyword(self, word: str) -> bool:
        """키워드가 검색에 의미있는지 판단"""
        # 너무 일반적이거나 추상적인 단어들 제외
        generic_words = [
            '계획', '준비', '확인', '방법', '추천', '정보', '조사',
            '선택', '결정', '고려', '검토', '점검', '관리', '진행',
            '완료', '달성', '성공', '실패', '문제', '해결', '개선',
            '시작', '마무리', '체크', '리스트', '목록', '항목'
        ]
        
        return word not in generic_words and len(word) >= 2
    
    def _generate_item_specific_queries(self, keywords: List[str], context: str = "") -> List[str]:
        """키워드를 기반으로 단일 검색 쿼리 생성 (1:1 매핑)"""
        if not keywords:
            return []
        
        main_keyword = keywords[0]
        additional_keywords = " ".join(keywords[1:2]) if len(keywords) > 1 else ""
        
        # 가장 적절한 단일 쿼리 생성
        if additional_keywords:
            primary_query = f"{main_keyword} {additional_keywords} 방법 추천"
        else:
            primary_query = f"{main_keyword} 방법 추천"
        
        # 컨텍스트가 있으면 개인화 (더 구체적인 쿼리 선호)
        if context and len(context) > 5:
            context_short = context[:30]  # 너무 길지 않게
            contextual_query = f"{main_keyword} {context_short} 추천"
            return [contextual_query]  # 컨텍스트가 있으면 이를 우선
        
        return [primary_query]  # 아이템당 정확히 1개 쿼리
    
    def _extract_answer_context(self, answers: List[Dict[str, Any]]) -> str:
        """답변에서 검색에 유용한 컨텍스트 추출 (유연한 방식)"""
        meaningful_answers = []
        
        for answer_item in answers:
            answer = answer_item.get("answer", "")
            
            if isinstance(answer, list):
                answer = " ".join(answer)
            
            # 의미있는 답변 필터링 (일반적인 조건들)
            if self._is_meaningful_answer(answer):
                meaningful_answers.append(answer.strip())
        
        # 답변 길이와 구체성을 기준으로 정렬 (긴 답변이 더 구체적일 가능성)
        meaningful_answers.sort(key=len, reverse=True)
        
        # 상위 답변들을 조합 (최대 3개)
        selected_answers = meaningful_answers[:3]
        final_context = " ".join(selected_answers)
        
        # 검색 쿼리에 적합한 길이로 조정
        if len(final_context) > 120:
            final_context = final_context[:117] + "..."
        
        return final_context
    
    def _is_meaningful_answer(self, answer: str) -> bool:
        """답변이 의미있는 컨텍스트인지 판단"""
        if not answer or len(answer.strip()) < 2:
            return False
        
        answer = answer.strip()
        
        # 명백히 의미없는 답변들 제외
        meaningless_patterns = [
            # 단일 문자나 기호
            r'^[ㄱ-ㅎㅏ-ㅣ]$',  # 단일 한글 자음/모음
            r'^[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]$',  # 단일 특수문자
            r'^\d+$',  # 숫자만
            # 무의미한 반복
            r'^(.)\1{2,}$',  # 같은 문자 3번 이상 반복
            # 임시/빈 답변 패턴
            r'^(없음|없다|모름|잘모름|해당없음|패스)$',
            r'^(.|_|-|\s)*$',  # 특수문자나 공백만
        ]
        
        import re
        for pattern in meaningless_patterns:
            if re.match(pattern, answer, re.IGNORECASE):
                return False
        
        # 최소 길이 체크 (너무 짧은 답변 제외)
        if len(answer) < 3:
            return False
        
        # 의미있는 단어가 포함되어 있는지 체크
        meaningful_chars = re.findall(r'[가-힣a-zA-Z0-9]', answer)
        if len(meaningful_chars) < 2:
            return False
        
        return True
    
    def _create_gemini_compatible_schema(self) -> Dict[str, Any]:
        """Gemini API 호환 JSON Schema 생성 (SearchResponse를 기반으로)"""
        # Gemini는 $defs와 $ref를 지원하지 않으므로 인라인 스키마로 변환
        return {
            "type": "object",
            "properties": {
                "tips": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "실용적인 팁과 조언"
                },
                "contacts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "연락처 이름"
                            },
                            "phone": {
                                "type": "string",
                                "description": "전화번호"
                            },
                            "email": {
                                "type": "string",
                                "description": "이메일 주소"
                            }
                        },
                        "required": ["name"]
                    },
                    "description": "관련 연락처 정보"
                },
                "links": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "링크 제목"
                            },
                            "url": {
                                "type": "string",
                                "description": "웹사이트 URL"
                            }
                        },
                        "required": ["title", "url"]
                    },
                    "description": "유용한 웹사이트 링크"
                },
                "price": {
                    "type": "string",
                    "description": "예상 비용 또는 가격 정보"
                },
                "location": {
                    "type": "string", 
                    "description": "위치 또는 장소 정보"
                }
            },
            "required": ["tips", "contacts", "links"]
        }

# 서비스 인스턴스
gemini_service = GeminiService() 