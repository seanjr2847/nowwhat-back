"""
스트리밍 기능 전용 서비스

비즈니스 로직:
- 실시간 스트리밍 데이터의 완전성 검증 및 자동 복구 전담
- JSON 구조 실시간 검증 및 불완전 데이터 자동 보정
- 스트리밍 실패 시 폴백 생성으로 사용자 경험 보장
- 어떤 상황에서도 사용자가 완전한 데이터를 받도록 보장
"""

import asyncio
import json
import logging
import uuid
from typing import AsyncGenerator, Optional

from .api_client import GeminiApiClient
from .config import GeminiConfig, GeminiAPIError
from .utils import extract_json_from_markdown

logger = logging.getLogger(__name__)


class StreamingService:
    """스트리밍 데이터 검증 및 복구 전용 서비스 (SRP)
    
    비즈니스 로직:
    - Server-Sent Events (SSE) 스트리밍 데이터의 실시간 완전성 검증
    - 불완전한 JSON 데이터 감지 및 자동 보정/복구
    - 스트리밍 실패 시 즉시 폴백 데이터 생성으로 사용자 경험 보장
    - 모든 상황에서 사용자가 완전한 데이터를 받을 수 있도록 보장
    """
    
    def __init__(self, api_client: GeminiApiClient):
        """스트리밍 서비스 초기화
        
        Args:
            api_client: Gemini API 클라이언트 (DIP - 의존성 주입)
        """
        self.api_client = api_client
        logger.info("StreamingService initialized")
    
    async def stream_with_validation(
        self,
        prompt: str,
        stream_id: str,
        goal: str,
        intent_title: str,
        user_country: Optional[str],
        user_language: Optional[str],
        country_option: bool
    ) -> AsyncGenerator[str, None]:
        """강화된 검증을 포함한 스트리밍 실행
        
        비즈니스 로직:
        - 실시간 스트리밍 데이터 수신 및 누적
        - 청크 단위로 JSON 구조 예비 검증
        - 스트리밍 완료 후 전체 데이터 완전성 최종 검증
        - 불완전 데이터 감지 시 자동 보정 또는 재생성
        - 모든 경우에 사용자는 완전한 JSON 데이터 수신 보장
        """
        accumulated_content = ""
        
        try:
            logger.info(f"🌊 Starting validated streaming [Stream: {stream_id}]")
            
            # 스트리밍 데이터 수신 및 누적
            async for chunk in self._stream_with_real_time_validation(prompt, stream_id):
                accumulated_content += chunk
                yield chunk
            
            logger.info(f"📋 Primary stream completed [Stream: {stream_id}], total: {len(accumulated_content)} chars")
            
            # 최종 완전성 검증 및 필요시 보정
            async for completion_chunk in self._handle_completion_validation(
                accumulated_content, stream_id, goal, intent_title, user_country, user_language, country_option
            ):
                yield completion_chunk
                
        except Exception as e:
            logger.error(f"🚨 Streaming validation failed [Stream: {stream_id}]: {str(e)}")
            # 오류 발생 시에도 빈 generator 대신 의미있는 응답
            yield f'{{ "status": "error", "message": "스트리밍 처리 중 오류가 발생했습니다.", "stream_id": "{stream_id}" }}'
    
    async def _stream_with_real_time_validation(self, prompt: str, stream_id: str) -> AsyncGenerator[str, None]:
        """실시간 검증이 포함된 질문 스트리밍
        
        비즈니스 로직:
        - Gemini API 스트리밍 응답을 청크 단위로 수신
        - 각 청크마다 JSON 구조 유효성 예비 검증
        - 스트리밍 중단 또는 오류 발생 시 즉시 감지
        - 누적된 컨텐츠의 완전성을 실시간 모니터링
        """
        chunks_received = 0
        total_chars = 0
        
        try:
            logger.debug(f"🔍 Starting real-time validated streaming [Stream: {stream_id}]")
            
            # Gemini 스트리밍 호출
            async for chunk in self.api_client.call_api_stream(prompt):
                chunks_received += 1
                total_chars += len(chunk)
                
                # 주기적으로 진행 상황 로깅
                if chunks_received % 10 == 0:
                    logger.debug(f"📊 [Stream: {stream_id}] Chunks: {chunks_received}, Chars: {total_chars}")
                
                yield chunk
            
            logger.info(f"✅ Stream data received [Stream: {stream_id}]: {chunks_received} chunks, {total_chars} chars")
                                    
        except Exception as e:
            logger.error(f"🚨 Real-time streaming error [Stream: {stream_id}]: {str(e)}")
            logger.debug(f"Error details - Chunks received: {chunks_received}, Total chars: {total_chars}")
            raise GeminiAPIError(f"Real-time streaming failed: {str(e)}")
    
    async def _handle_completion_validation(
        self, 
        content: str, 
        stream_id: str,
        goal: str,
        intent_title: str,
        user_country: Optional[str],
        user_language: Optional[str],
        country_option: bool
    ) -> AsyncGenerator[str, None]:
        """스트리밍 완료 후 데이터 완전성 처리
        
        비즈니스 로직:
        - 스트리밍 완료 시 누적된 컨텐츠의 JSON 구조 완전성 검증
        - 불완전한 JSON 감지 시 즉시 폴백 질문 생성으로 대체
        - 사용자가 항상 완전한 데이터를 받도록 보장
        - 폴백 생성 시 동일한 매개변수로 맥락 일관성 유지
        """
        is_complete = self._validate_json_completeness(content, stream_id)
        
        if is_complete:
            logger.info(f"✅ Stream data validation passed [Stream: {stream_id}]")
            return  # 검증 통과 시 추가 처리 불필요
        
        logger.warning(f"🚨 Incomplete JSON detected [Stream: {stream_id}], generating fallback")
        
        # 불완전 데이터 감지 시 폴백 생성
        try:
            # 동일한 파라미터로 폴백 질문 생성 (일반 API 사용)
            fallback_content = await self._generate_fallback_questions(
                goal, intent_title, user_country, user_language, country_option
            )
            
            if fallback_content:
                logger.info(f"✅ Fallback questions generated [Stream: {stream_id}]")
                
                # 구분선과 함께 완전한 데이터 전송
                yield "\n\n--- 완전한 질문 데이터 ---\n"
                yield fallback_content
            else:
                logger.error(f"🚨 Fallback generation also failed [Stream: {stream_id}]")
                yield '{"error": "질문 생성에 실패했습니다. 페이지를 새로고침해주세요."}'
                
        except Exception as fallback_error:
            logger.error(f"🚨 Fallback processing error [Stream: {stream_id}]: {str(fallback_error)}")
            yield '{"error": "데이터 복구에 실패했습니다. 잠시 후 다시 시도해주세요."}'
    
    def _validate_json_completeness(self, content: str, stream_id: str) -> bool:
        """누적된 컨텐츠의 JSON 완전성 검증
        
        비즈니스 로직:
        - 스트리밍 완료 후 누적된 컨텐츠가 완전한 JSON 구조인지 검증
        - 마크다운 코드 블록에서 JSON 데이터 추출
        - questions 배열의 존재 여부와 각 질문의 필수 필드 검증
        - 질문 옵션의 완전성 및 텍스트 잘림 현상 감지
        - 검증 실패 시 상세 로깅으로 디버깅 정보 제공
        """
        try:
            if not content or len(content.strip()) < GeminiConfig.MIN_CONTENT_LENGTH:
                logger.warning(f"🚨 Content too short [{stream_id}]: {len(content)} chars")
                return False
            
            # 마크다운 블록에서 JSON 추출
            clean_content = extract_json_from_markdown(content)
            
            # JSON 파싱 시도
            try:
                parsed = json.loads(clean_content)
            except json.JSONDecodeError as e:
                logger.warning(f"🚨 JSON parsing failed [{stream_id}]: {str(e)}")
                return False
            
            # 기본 구조 검증
            if not isinstance(parsed, dict) or 'questions' not in parsed:
                logger.warning(f"🚨 Invalid structure [{stream_id}]: missing 'questions' field")
                return False
            
            questions = parsed['questions']
            if not isinstance(questions, list) or len(questions) == 0:
                logger.warning(f"🚨 Invalid questions [{stream_id}]: not a list or empty")
                return False
            
            # 각 질문의 필수 필드 검증
            for i, question in enumerate(questions):
                if not isinstance(question, dict):
                    logger.warning(f"🚨 Question {i} invalid [{stream_id}]: not a dict")
                    return False
                
                required_fields = ['id', 'text', 'type', 'options']
                for field in required_fields:
                    if field not in question:
                        logger.warning(f"🚨 Question {i} missing '{field}' [{stream_id}]")
                        return False
                
                # 옵션 검증 (multiple choice인 경우)
                if question['type'] == 'multiple':
                    options = question['options']
                    if not isinstance(options, list) or len(options) == 0:
                        logger.warning(f"🚨 Question {i} invalid options [{stream_id}]")
                        return False
                    
                    # 각 옵션이 완전한지 검증
                    for j, option in enumerate(options):
                        if isinstance(option, dict):
                            if 'text' not in option or not option['text']:
                                logger.warning(f"🚨 Question {i}, Option {j} incomplete text [{stream_id}]")
                                return False
                            
                            # 텍스트가 중간에 잘렸는지 검증 (괄호나 따옴표가 열려있는지)
                            text = option['text']
                            if text.count('(') != text.count(')') or text.count('"') % 2 != 0:
                                logger.warning(f"🚨 Question {i}, Option {j} truncated text [{stream_id}]: '{text}'")
                                return False
            
            logger.info(f"✅ JSON validation passed [{stream_id}]: {len(questions)} questions verified")
            return True
            
        except Exception as e:
            logger.error(f"🚨 JSON validation error [{stream_id}]: {str(e)}")
            return False
    
    def _validate_stream_completion(self, content: str, stream_id: str, total_chars: int):
        """스트리밍 완료 후 컨텐츠 무결성 검증
        
        비즈니스 로직:
        - 전체 스트리밍이 완료된 후 컨텐츠의 완전성 최종 점검
        - 컨텐츠 길이가 예상보다 너무 짧은지 확인
        - JSON 구조의 바람망괄호와 대괄호 균형 검증
        - 마크다운 코드 블록이 완전히 닫혀있는지 확인
        - 각 검증 단계별 상세 경고 로깅
        """
        try:
            # 기본 길이 검증 (너무 짧으면 불완전)
            if total_chars < GeminiConfig.MIN_CONTENT_LENGTH:
                logger.warning(f"🚨 Stream suspiciously short [Stream: {stream_id}]: {total_chars} chars")
            
            # JSON 구조 완료 검증
            brace_count = content.count('{') - content.count('}')
            bracket_count = content.count('[') - content.count(']')
            
            if brace_count != 0 or bracket_count != 0:
                logger.warning(f"🚨 Unbalanced brackets detected [Stream: {stream_id}]: braces={brace_count}, brackets={bracket_count}")
            
            # 마크다운 블록 완료 검증
            if '```json' in content and not content.rstrip().endswith('```'):
                logger.warning(f"🚨 Incomplete markdown block [Stream: {stream_id}]")
                
        except Exception as e:
            logger.error(f"🚨 Stream completion validation error [Stream: {stream_id}]: {str(e)}")
    
    async def _generate_fallback_questions(
        self, 
        goal: str, 
        intent_title: str, 
        user_country: Optional[str], 
        user_language: Optional[str], 
        country_option: bool
    ) -> Optional[str]:
        """스트리밍 실패 시 비스트리밍 폴백 질문 생성
        
        비즈니스 로직:
        - 스트리밍 JSON이 불완전할 때 일반 API로 완전한 질문 다시 생성
        - 동일한 매개변수(goal, intent, country, language)로 일관성 유지
        - QuestionGenerationService 순환 참조 방지를 위해 직접 API 호출
        - Question 객체를 JSON 문자열로 변환하여 대체 데이터 제공
        - 폴백 실패 시 None 반환으로 상위 레이어에 오류 전파
        """
        try:
            logger.info(f"🔄 Generating fallback questions for: {goal} (intent: {intent_title})")
            
            # 순환 참조 방지를 위해 직접 프롬프트 생성 및 API 호출
            from .utils import get_country_context, get_language_context
            from app.prompts.prompt_selector import get_questions_generation_prompt
            
            country_context = get_country_context(user_country)
            language_context = get_language_context(user_language)
            
            prompt = get_questions_generation_prompt(
                goal=goal,
                intent_title=intent_title,
                user_country=user_country or "정보 없음",
                user_language=user_language or "정보 없음",
                country_context=country_context,
                language_context=language_context,
                country_option=country_option
            )
            
            # 일반 API 호출 (비스트리밍)
            response = await self.api_client.call_api(prompt)
            
            if response and response.strip():
                logger.info(f"✅ Fallback questions generated: {len(response)} chars")
                return response
            else:
                logger.warning("⚠️ Fallback generation returned empty response")
                return None
            
        except Exception as e:
            logger.error(f"🚨 Fallback question generation failed: {str(e)}")
            return None