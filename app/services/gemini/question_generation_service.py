"""
질문 생성 전용 서비스

비즈니스 로직:
- 선택된 의도를 기반으로 맞춤형 질문 생성하는 단일 책임
- 일반 API 호출과 스트리밍 방식 모두 지원
- 지역정보와 언어 정보를 활용한 본화된 질문 제공
- API 실패 시 범용 질문 템플릿으로 폴백하여 서비스 연속성 보장
"""

import asyncio
import json
import logging
import uuid
from typing import List, Optional, AsyncGenerator

from app.schemas.questions import Question, Option
from app.prompts.prompt_selector import get_questions_generation_prompt
from .api_client import GeminiApiClient
from .config import GeminiConfig, GeminiResponseError
from .utils import get_country_context, get_language_context, validate_json_structure
from .streaming_service import StreamingService

logger = logging.getLogger(__name__)


class QuestionGenerationService:
    """질문 생성 전용 서비스 (SRP)
    
    비즈니스 로직:
    - 사용자의 목표와 선택된 의도에 따라 3-5개의 상세 질문 생성
    - 지역정보와 언어 정보를 활용하여 본화된 질문 제공
    - 각 질문에 대한 다중 선택 옵션도 함께 생성
    - API 실패 시 범용 질문 템플릿으로 폴백하여 서비스 연속성 보장
    """
    
    def __init__(self, api_client: GeminiApiClient):
        """질문 생성 서비스 초기화
        
        Args:
            api_client: Gemini API 클라이언트 (DIP - 의존성 주입)
        """
        self.api_client = api_client
        self.streaming_service = StreamingService(api_client)
        logger.info("QuestionGenerationService initialized")
    
    async def generate_questions(
        self, 
        goal: str, 
        intent_title: str, 
        user_country: Optional[str] = None,
        user_language: Optional[str] = None,
        country_option: bool = True
    ) -> List[Question]:
        """선택된 의도를 기반으로 맞춤형 질문 생성
        
        비즈니스 로직:
        - 사용자의 목표와 선택된 의도에 따라 3-5개의 상세 질문 생성
        - 지역정보와 언어 정보를 활용하여 본화된 질문 제공
        - 각 질문에 대한 다중 선택 옵션도 함께 생성
        - API 실패 시 범용 질문 템플릿으로 폴백하여 서비스 연속성 보장
        
        Args:
            goal: 사용자 목표
            intent_title: 선택된 의도 제목
            user_country: 사용자 국가 정보
            user_language: 사용자 언어 정보  
            country_option: 지역정보 포함 여부
            
        Returns:
            List[Question]: 생성된 질문 리스트
        """
        try:
            prompt = self._create_questions_prompt(
                goal, intent_title, user_country, user_language, country_option
            )
            
            questions = await self._generate_with_retry(prompt, intent_title)
            return questions if questions else self._get_cached_template(intent_title)
            
        except Exception as e:
            logger.error(f"Question generation failed: {str(e)}")
            return self._get_cached_template(intent_title)
    
    async def generate_questions_stream(
        self, 
        goal: str, 
        intent_title: str, 
        user_country: Optional[str] = None,
        user_language: Optional[str] = None,
        country_option: bool = True
    ) -> AsyncGenerator[str, None]:
        """실시간 스트리밍으로 맞춤형 질문 생성
        
        비즈니스 로직:
        - Server-Sent Events (SSE) 형식으로 실시간 질문 생성 과정을 사용자에게 전송
        - 스트리밍 중 데이터 무결성 실시간 검증
        - JSON 데이터 완전성 검증 및 불완전 시 자동 수정
        - 스트리밍 실패 시 즉시 폴백 질문 생성으로 사용자 경험 보장
        - 어떤 상황에서도 사용자는 항상 완전한 데이터 수신
        """
        stream_id = str(uuid.uuid4())[:8]
        logger.info(f"🌊 Starting streaming question generation [Stream: {stream_id}]")
        logger.info(f"   Goal: '{goal}', Intent: '{intent_title}'")
        
        try:
            prompt = self._create_questions_prompt(
                goal, intent_title, user_country, user_language, country_option
            )
            
            # 스트리밍 서비스에 위임
            async for chunk in self.streaming_service.stream_with_validation(
                prompt, stream_id, goal, intent_title, user_country, user_language, country_option
            ):
                yield chunk
                
        except Exception as e:
            logger.error(f"🚨 Question streaming failed [Stream: {stream_id}]: {str(e)}")
            
            # 오류 시 폴백 처리
            async for chunk in self._handle_stream_error(stream_id, intent_title):
                yield chunk
    
    async def _generate_with_retry(self, prompt: str, intent_title: str) -> Optional[List[Question]]:
        """재시도 메커니즘을 통한 안정적인 질문 생성
        
        비즈니스 로직:
        - Gemini API로 질문 생성 시 최대 3회 재시도로 안정성 확보
        - API 실패 또는 무효한 응답 시 지수백오프로 재시도 주기 조절
        - 각 시도에서 질문 수와 구조 유효성 검증
        - 모든 시도 실패 시 캐시된 템플릿으로 폴백
        """
        for attempt in range(GeminiConfig.RETRY_ATTEMPTS):
            try:
                response = await self.api_client.call_api(prompt)
                questions = self._parse_questions_response(response)
                
                if questions:
                    logger.info(f"✅ Generated {len(questions)} questions (attempt {attempt + 1})")
                    return questions
                else:
                    logger.warning(f"⚠️ No valid questions generated (attempt {attempt + 1})")
                    
            except Exception as e:
                logger.error(f"❌ Question generation attempt {attempt + 1} failed: {str(e)}")
                if attempt < GeminiConfig.RETRY_ATTEMPTS - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"⏳ Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                
        logger.warning("🚨 All question generation attempts failed, using cached template")
        return None
    
    def _create_questions_prompt(
        self, 
        goal: str, 
        intent_title: str, 
        user_country: Optional[str] = None, 
        user_language: Optional[str] = None, 
        country_option: bool = True
    ) -> str:
        """질문 생성을 위한 맞춤형 프롬프트 생성
        
        비즈니스 로직:
        - 사용자의 목표와 선택된 의도를 중심으로 배경 정보 통합
        - 지역정보(country) 및 언어정보(language)를 활용한 본화
        - country_option 설정에 따른 상세 지역 정보 포함 여부 결정
        - 프롬프트 생성기에 전달할 구조화된 매개변수 준비
        """
        country_context = get_country_context(user_country)
        language_context = get_language_context(user_language)
        
        return get_questions_generation_prompt(
            goal=goal,
            intent_title=intent_title,
            user_country=user_country or "정보 없음",
            user_language=user_language or "정보 없음",
            country_context=country_context,
            language_context=language_context,
            country_option=country_option
        )
    
    def _parse_questions_response(self, response: str) -> List[Question]:
        """Gemini API 질문 생성 응답 파싱
        
        비즈니스 로직:
        - Gemini에서 수신한 JSON 형태의 질문 데이터를 Question 객체로 변환
        - 마크다운 코드 블록 내에서 JSON 데이터 추출
        - 질문 구조 및 필수 필드 유효성 검증
        - 파싱 실패 시 예외 발생으로 상위 레이어에 오류 전파
        """
        try:
            # 응답이 비어있는지 확인
            if not response or not response.strip():
                logger.warning("Gemini returned empty response")
                raise GeminiResponseError("Empty response from Gemini")
            
            # JSON 구조 검증 및 파싱
            is_valid, parsed_data = validate_json_structure(response, [])
            if not is_valid:
                raise GeminiResponseError("Invalid JSON structure")
            
            # questions 배열이 있는지 확인
            questions_data = parsed_data
            if isinstance(parsed_data, dict) and 'questions' in parsed_data:
                questions_data = parsed_data['questions']
            
            if not isinstance(questions_data, list):
                raise GeminiResponseError("Response is not a question list")
                
            questions = []
            for item in questions_data:
                # 필수 필드 확인
                required_fields = ["id", "text", "type", "required"]
                if not all(key in item for key in required_fields):
                    missing = [f for f in required_fields if f not in item]
                    raise GeminiResponseError(f"Missing required fields in question: {missing}")
                
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
            
            logger.info(f"✅ Successfully parsed {len(questions)} questions")
            return questions
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            raise GeminiResponseError(f"Failed to parse questions response: Invalid JSON - {str(e)}")
        except Exception as e:
            logger.error(f"Questions parsing error: {str(e)}")
            raise GeminiResponseError(f"Failed to parse questions response: {str(e)}")
    
    def _get_cached_template(self, intent_title: str) -> List[Question]:
        """의도별 폴백 질문 템플릿 제공
        
        비즈니스 로직:
        - Gemini API 실패 시 사용할 의도별 기본 질문 세트 제공
        - 주요 의도(여행, 건강, 개발, 자기계발)에 대해 미리 정의된 질문 세트
        - 각 질문은 다중 선택 형태로 바로 사용 가능한 구조
        - 지원되지 않는 의도에 대해서도 범용 질문 제공
        """
        templates = {
            "여행 계획": self._get_travel_template(),
            "건강 관리": self._get_health_template(),
            "개발 공부": self._get_development_template(),
            "자기계발": self._get_self_development_template()
        }
        
        # 의도별 템플릿이 있으면 사용, 없으면 범용 템플릿 사용
        return templates.get(intent_title, self._get_generic_template())
    
    def _get_travel_template(self) -> List[Question]:
        """여행 계획 의도 전용 질문 템플릿"""
        return [
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
                id="q_budget",
                text="예상 예산은 어느 정도인가요?",
                type="multiple",
                options=[
                    Option(id="opt_budget", text="50만원 이하", value="budget"),
                    Option(id="opt_moderate", text="50-100만원", value="moderate"),
                    Option(id="opt_premium", text="100만원 이상", value="premium"),
                    Option(id="opt_flexible", text="예산 상관없음", value="flexible")
                ],
                required=True
            )
        ]
    
    def _get_health_template(self) -> List[Question]:
        """건강 관리 의도 전용 질문 템플릿"""
        return [
            Question(
                id="q_health_goal",
                text="주요 건강 목표는 무엇인가요?",
                type="multiple",
                options=[
                    Option(id="opt_weight", text="체중 관리", value="weight"),
                    Option(id="opt_fitness", text="체력 향상", value="fitness"),
                    Option(id="opt_diet", text="식습관 개선", value="diet"),
                    Option(id="opt_mental", text="정신 건강", value="mental")
                ],
                required=True
            ),
            Question(
                id="q_activity_level",
                text="현재 운동 수준은 어떤가요?",
                type="multiple",
                options=[
                    Option(id="opt_beginner", text="초보자", value="beginner"),
                    Option(id="opt_intermediate", text="중급자", value="intermediate"),
                    Option(id="opt_advanced", text="상급자", value="advanced"),
                    Option(id="opt_none", text="운동 안함", value="none")
                ],
                required=True
            )
        ]
    
    def _get_development_template(self) -> List[Question]:
        """개발 공부 의도 전용 질문 템플릿"""
        return [
            Question(
                id="q_dev_level",
                text="현재 개발 경험 수준은?",
                type="multiple",
                options=[
                    Option(id="opt_newbie", text="완전 초보", value="newbie"),
                    Option(id="opt_beginner", text="기초 수준", value="beginner"),
                    Option(id="opt_intermediate", text="중급 수준", value="intermediate"),
                    Option(id="opt_advanced", text="고급 수준", value="advanced")
                ],
                required=True
            ),
            Question(
                id="q_tech_stack",
                text="관심 있는 기술 분야는?",
                type="multiple",
                options=[
                    Option(id="opt_web", text="웹 개발", value="web"),
                    Option(id="opt_mobile", text="모바일 개발", value="mobile"),
                    Option(id="opt_ai", text="AI/ML", value="ai"),
                    Option(id="opt_backend", text="백엔드", value="backend")
                ],
                required=True
            )
        ]
    
    def _get_self_development_template(self) -> List[Question]:
        """자기계발 의도 전용 질문 템플릿"""
        return [
            Question(
                id="q_dev_area",
                text="어떤 분야를 개발하고 싶으신가요?",
                type="multiple",
                options=[
                    Option(id="opt_skill", text="전문 기술", value="skill"),
                    Option(id="opt_leadership", text="리더십", value="leadership"),
                    Option(id="opt_communication", text="소통 능력", value="communication"),
                    Option(id="opt_creativity", text="창의성", value="creativity")
                ],
                required=True
            )
        ]
    
    def _get_generic_template(self) -> List[Question]:
        """범용 질문 템플릿 (의도를 특정할 수 없을 때)"""
        return [
            Question(
                id="q_emergency_1",
                text="언제까지 이 목표를 달성하고 싶으신가요?",
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
                id="q_emergency_2",
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
                id="q_emergency_3",
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
    
    async def _handle_stream_error(self, stream_id: str, intent_title: str) -> AsyncGenerator[str, None]:
        """스트리밍 오류 시 비상 대응 처리
        
        비즈니스 로직:
        - 스트리밍 API 실패 시 짆시 없이 대안 데이터 제공
        - 의도별 캐시된 질문 템플릿을 스트리밍 형식으로 전송
        - 청크 단위 전솨으로 실시간 전송 효과 유지
        - 폴백 데이터도 실패 시 기본 오류 메시지 대신 JSON 형태로 제공
        """
        try:
            cached_questions = self._get_cached_template(intent_title)
            questions_json = json.dumps(
                {"questions": [q.dict() for q in cached_questions]}, 
                ensure_ascii=False, indent=2
            )
            
            logger.info(f"📦 Sending cached questions [Stream: {stream_id}], size: {len(questions_json)} chars")
            
            # 청크 단위로 전송
            for i in range(0, len(questions_json), GeminiConfig.CHUNK_SIZE):
                chunk = questions_json[i:i + GeminiConfig.CHUNK_SIZE]
                yield chunk
                await asyncio.sleep(GeminiConfig.STREAM_DELAY)
                
        except Exception as fallback_error:
            logger.error(f"🚨 Fallback generation also failed [Stream: {stream_id}]: {str(fallback_error)}")
            yield '{"error": "질문 생성에 실패했습니다. 다시 시도해주세요."}'