"""
Gemini API 저수준 클라이언트

비즈니스 로직:
- Google Gemini API와의 직접적인 통신 담당 (Infrastructure Layer)
- 도메인 로직과 외부 API 의존성 분리
- API 호출 방식 변경 시 이 클래스만 수정하면 됨 (OCP 원칙)
- 다른 서비스들은 이 클라이언트에만 의존 (DIP 원칙)
"""

import asyncio
import json
import logging
from typing import AsyncGenerator, Any, Dict
import google.generativeai as genai

from app.core.config import settings
from app.prompts.enhanced_prompts import get_enhanced_knowledge_prompt
from .config import GeminiConfig, GeminiAPIError, SearchResult
from .utils import create_error_result

logger = logging.getLogger(__name__)


class GeminiApiClient:
    """Gemini API 저수준 클라이언트
    
    비즈니스 로직:
    - Google Gemini API와의 모든 통신을 담당하는 Infrastructure 계층
    - 동기/비동기 호출, 스트리밍, 웹 검색 등 다양한 API 호출 방식 지원
    - API 응답의 원시 데이터만 반환하고 도메인 로직은 상위 서비스에 위임
    - 연결 상태, 인증, 네트워크 오류 등 API 수준의 문제만 처리
    """
    
    def __init__(self):
        """API 클라이언트 초기화
        
        비즈니스 로직:
        - Gemini API 키 검증 및 모델 초기화
        - API 키 미설정 시 즉시 오류 발생으로 조기 실패 감지
        - 초기화 성공 시 로깅으로 설정 상태 확인 가능
        """
        if not settings.GEMINI_API_KEY:
            logger.error("Cannot initialize GeminiApiClient: GEMINI_API_KEY not set")
            raise ValueError("GEMINI_API_KEY not configured")
        
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
        logger.info(f"GeminiApiClient initialized with model: {settings.GEMINI_MODEL}")
    
    async def call_api(self, prompt: str) -> str:
        """Gemini API 일반 호출 (비스트리밍)
        
        비즈니스 로직:
        - 동기식 Gemini API 호출로 전체 응답을 한 번에 수신
        - 생성 컨피그 설정으로 음성의 다양성과 품질 제어
        - 응답 구조 및 Safety Rating 상세 검증
        - 빈 응답 또는 매서드에서 텍스트 추출 실패 시 예외 발생
        """
        try:
            logger.debug(f"Sending prompt to Gemini (length: {len(prompt)} chars)")
            response = await asyncio.to_thread(
                self.model.generate_content, 
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=GeminiConfig.MAX_OUTPUT_TOKENS,
                    temperature=GeminiConfig.TEMPERATURE,
                    top_p=GeminiConfig.TOP_P,
                    top_k=GeminiConfig.TOP_K
                )
            )
            
            # 응답 상태 확인
            if not response:
                logger.error("Gemini returned None response")
                raise GeminiAPIError("Gemini returned None response")
            
            # Safety rating 및 finish reason 확인
            self._log_response_metadata(response)
            
            # 텍스트 추출
            response_text = self._extract_text_from_response(response)
            
            logger.debug(f"Raw Gemini response (length: {len(response_text) if response_text else 0})")
            
            if not response_text or not response_text.strip():
                logger.error("Gemini returned empty or whitespace-only response")
                raise GeminiAPIError("Gemini returned empty response")
                
            return response_text
            
        except Exception as e:
            logger.error(f"Gemini API call error: {str(e)}")
            raise GeminiAPIError(f"Gemini API call failed: {str(e)}")
    
    async def call_api_with_search(self, prompt: str) -> str:
        """Gemini API 웹 검색 기능 포함 호출
        
        비즈니스 로직:
        - Google Search Retrieval 기능을 활용한 실시간 정보 검색
        - 웹 검색 결과가 포함된 Structured Output JSON 응답
        - 검색 실패 시 일반 API로 자동 폴백하여 서비스 연속성 보장
        - grounding metadata 정보로 검색 품질 및 신뢰성 확인
        """
        try:
            logger.debug(f"Calling Gemini API with search enabled (prompt length: {len(prompt)} chars)")
            
            # Google Search Retrieval을 사용하는 모델로 생성
            model_with_search = genai.GenerativeModel(
                settings.GEMINI_MODEL,
                tools=[{"google_search_retrieval": {}}]
            )
            
            try:
                # 웹 검색 기능 활성화하여 호출
                response = await asyncio.to_thread(
                    model_with_search.generate_content,
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=GeminiConfig.MAX_OUTPUT_TOKENS * 0.8,  # 검색 기능 사용 시 토큰 여유
                        temperature=GeminiConfig.TEMPERATURE,
                        top_p=GeminiConfig.TOP_P,
                        top_k=GeminiConfig.TOP_K,
                        response_mime_type="application/json",
                        response_schema=self._create_search_schema()
                    )
                )
                
                # grounding metadata 확인
                self._log_grounding_metadata(response)
                
            except Exception as search_error:
                logger.warning(f"Web search failed, falling back to enhanced knowledge: {search_error}")
                
                # 웹 검색을 사용할 수 없는 경우, 최신 정보 요청 프롬프트 + Structured Output
                enhanced_prompt = get_enhanced_knowledge_prompt(prompt)
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    enhanced_prompt,
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=GeminiConfig.MAX_OUTPUT_TOKENS,
                        temperature=GeminiConfig.TEMPERATURE,
                        top_p=GeminiConfig.TOP_P,
                        top_k=GeminiConfig.TOP_K,
                        response_mime_type="application/json",
                        response_schema=self._create_search_schema()
                    )
                )
        
            # 응답 처리
            if not response:
                logger.error("Gemini returned None response")
                raise GeminiAPIError("Gemini returned None response")
            
            response_text = self._extract_text_from_response(response)
            
            logger.debug(f"Gemini search response received (length: {len(response_text) if response_text else 0})")
            
            if not response_text or not response_text.strip():
                logger.error("Gemini returned empty response")
                raise GeminiAPIError("Gemini returned empty response")
                
            return response_text
            
        except GeminiAPIError:
            raise
        except Exception as e:
            logger.error(f"Gemini search API call error: {str(e)}")
            # 웹 검색 실패시 일반 API로 폴백
            logger.info("Falling back to regular Gemini API without search")
            return await self.call_api(prompt)
    
    async def call_api_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        """Gemini API 실시간 스트리밍 호출
        
        비즈니스 로직:
        - Server-Sent Events 형식으로 실시간 데이터 전송
        - generator_content_stream() 함수로 청크 단위 데이터 수신
        - 스트리밍 중 오류 발생 시 진단 정보와 함께 예외 발생
        - 각 청크에 대한 로깅 및 오류 처리 포함
        """
        chunks_received = 0
        total_chars = 0
        
        try:
            logger.debug(f"Starting streaming request to Gemini (prompt length: {len(prompt)} chars)")
            
            # Gemini 스트리밍 설정
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=GeminiConfig.MAX_OUTPUT_TOKENS,
                temperature=GeminiConfig.TEMPERATURE,
                top_p=GeminiConfig.TOP_P,
                top_k=GeminiConfig.TOP_K
            )
            
            # 스트리밍 응답 생성
            response_stream = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=generation_config,
                stream=True
            )
            
            logger.debug("✅ Gemini streaming response initiated")
            
            # 스트리밍 응답 처리
            for chunk in response_stream:
                chunk_text = self._extract_chunk_text(chunk)
                
                if chunk_text:
                    chunks_received += 1
                    total_chars += len(chunk_text)
                    
                    # 주기적으로 진행 상황 로깅
                    if chunks_received % 10 == 0:
                        logger.debug(f"📊 Streaming: {chunks_received} chunks, {total_chars} chars")
                    
                    yield chunk_text
            
            logger.info(f"📋 Stream completed: {chunks_received} chunks, {total_chars} chars")
                                    
        except Exception as e:
            logger.error(f"🚨 Streaming API error: {str(e)}")
            logger.debug(f"Error details - Chunks received: {chunks_received}, Total chars: {total_chars}")
            raise GeminiAPIError(f"Gemini streaming failed: {str(e)}")
    
    def _extract_text_from_response(self, response) -> str:
        """응답 객체에서 텍스트 추출
        
        비즈니스 로직:
        - Gemini API 응답의 다양한 구조에서 텍스트 추출
        - response.text 속성이 없는 경우 candidates에서 추출
        - 여러 candidate가 있는 경우 첫 번째 유효한 텍스트 사용
        - 모든 추출 방법 실패 시 예외 발생
        """
        if hasattr(response, 'text') and response.text:
            return response.text
        
        # 대안으로 candidates에서 텍스트 추출 시도
        if hasattr(response, 'candidates') and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                    for part in candidate.content.parts:
                        if hasattr(part, 'text') and part.text:
                            logger.debug(f"Found text in candidate.content.parts")
                            return part.text
        
        raise GeminiAPIError("Gemini response has no extractable text")
    
    def _extract_chunk_text(self, chunk) -> str:
        """스트리밍 청크에서 텍스트 추출
        
        비즈니스 로직:
        - 스트리밍 응답의 개별 청크에서 텍스트 추출
        - chunk.text가 있으면 직접 사용
        - 없으면 candidates 구조에서 추출
        - 빈 청크의 경우 빈 문자열 반환 (정상)
        """
        chunk_text = ""
        
        if hasattr(chunk, 'text') and chunk.text:
            chunk_text = chunk.text
        elif hasattr(chunk, 'candidates') and chunk.candidates:
            for candidate in chunk.candidates:
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                    for part in candidate.content.parts:
                        if hasattr(part, 'text') and part.text:
                            chunk_text += part.text
        
        return chunk_text
    
    def _log_response_metadata(self, response):
        """응답 메타데이터 로깅 (Safety Rating, Finish Reason 등)
        
        비즈니스 로직:
        - API 응답의 품질 및 안전성 정보 기록
        - finish_reason으로 응답 완료/중단 원인 파악
        - safety_ratings로 컨텐츠 필터링 정보 확인
        - 디버깅 및 품질 모니터링에 활용
        """
        if hasattr(response, 'candidates') and response.candidates:
            for i, candidate in enumerate(response.candidates):
                finish_reason = getattr(candidate, 'finish_reason', 'N/A')
                logger.debug(f"Candidate {i} finish_reason: {finish_reason}")
                
                # finish_reason 해석
                if finish_reason == 2:
                    logger.warning("Response was truncated due to MAX_TOKENS limit")
                elif finish_reason == 3:
                    logger.warning("Response was blocked by safety filters")
                elif finish_reason == 4:
                    logger.warning("Response was blocked due to recitation concerns")
                
                if hasattr(candidate, 'safety_ratings'):
                    logger.debug(f"Candidate {i} safety_ratings: {candidate.safety_ratings}")
    
    def _log_grounding_metadata(self, response):
        """Grounding 메타데이터 로깅 (웹 검색 결과 정보)
        
        비즈니스 로직:
        - 웹 검색 기능 사용 시 검색 품질 정보 기록
        - grounding_chunks로 검색된 소스 개수 확인
        - search_entry_point로 검색 진입점 정보 기록
        - 검색 결과의 신뢰성 평가에 활용
        """
        if hasattr(response, 'candidates') and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, 'grounding_metadata'):
                    logger.info("Response includes grounding metadata (web search results)")
                    if hasattr(candidate.grounding_metadata, 'search_entry_point'):
                        logger.debug(f"Search entry point: {candidate.grounding_metadata.search_entry_point}")
                    if hasattr(candidate.grounding_metadata, 'grounding_chunks'):
                        logger.debug(f"Found {len(candidate.grounding_metadata.grounding_chunks)} grounding chunks")
    
    def _create_search_schema(self) -> Dict[str, Any]:
        """검색 응답용 JSON 스키마 생성
        
        비즈니스 로직:
        - Structured Output을 위한 Gemini API 호환 JSON 스키마
        - $defs와 $ref를 사용하지 않은 인라인 스키마 구조
        - tips, contacts, links, price, location 등 검색 결과에 필요한 모든 필드 정의
        - 일관되고 예측 가능한 응답 형식 보장
        """
        return {
            "type": "object",
            "properties": {
                "tips": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "실용적인 팁과 조언"
                },
                "contacts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "연락처 이름"},
                            "phone": {"type": "string", "description": "전화번호"},
                            "email": {"type": "string", "description": "이메일 주소"}
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
                            "title": {"type": "string", "description": "링크 제목"},
                            "url": {"type": "string", "description": "웹사이트 URL"}
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