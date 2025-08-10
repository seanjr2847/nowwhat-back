"""
Gemini 서비스 Facade 패턴

비즈니스 로직:
- 기존 코드와의 호환성을 유지하면서 리팩토링된 서비스들을 통합
- 복잡한 서비스 간 의존성을 Facade 뒤에 숨겨서 클라이언트 코드 단순화
- 단일 진입점으로 모든 Gemini 관련 기능 제공
- 의존성 주입을 통한 느슨한 결합 유지 (DIP 원칙)
"""

import logging
from typing import List, Optional, AsyncGenerator, Dict, Any

from app.schemas.nowwhat import IntentOption
from app.schemas.questions import Question
from .api_client import GeminiApiClient
from .intent_analysis_service import IntentAnalysisService
from .question_generation_service import QuestionGenerationService
from .search_service import SearchService
from .config import SearchResult

logger = logging.getLogger(__name__)


class GeminiService:
    """Gemini 서비스 Facade (기존 코드 호환성 유지)
    
    비즈니스 로직:
    - 기존 GeminiService의 모든 public 인터페이스를 동일하게 유지
    - 내부적으로는 리팩토링된 전용 서비스들에 작업 위임 (Facade 패턴)
    - 복잡한 서비스 간 조합 로직을 캡슐화하여 클라이언트 코드 단순화
    - 의존성 주입을 통한 느슨한 결합으로 테스트 용이성 확보
    """
    
    def __init__(self):
        """Gemini 서비스 Facade 초기화
        
        비즈니스 로직:
        - 모든 전용 서비스들을 초기화하고 의존성 주입
        - 공통 API 클라이언트를 통해 일관된 API 접근
        - 각 서비스는 단일 책임만 가지도록 분리된 상태
        - Facade가 서비스 간 조합 및 협력 로직 담당
        """
        try:
            # 공통 API 클라이언트 초기화
            self.api_client = GeminiApiClient()
            
            # 전용 서비스들 초기화 (의존성 주입)
            self.intent_service = IntentAnalysisService(self.api_client)
            self.question_service = QuestionGenerationService(self.api_client)
            self.search_service = SearchService(self.api_client)
            
            logger.info("GeminiService Facade initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize GeminiService Facade: {str(e)}")
            raise
    
    # ===========================================
    # 기존 인터페이스 유지 (Intent Analysis)
    # ===========================================
    
    async def analyze_intent(
        self, 
        goal: str, 
        country_info: str = "", 
        language_info: str = "", 
        country_option: bool = True
    ) -> List[IntentOption]:
        """사용자 목표 분석 및 의도 옵션 생성
        
        기존 인터페이스 그대로 유지하면서 IntentAnalysisService에 위임
        """
        logger.debug(f"Facade: Delegating intent analysis for goal: '{goal[:50]}...'")
        
        return await self.intent_service.analyze_intent(
            goal=goal,
            country_info=country_info,
            language_info=language_info,
            country_option=country_option
        )
    
    # ===========================================
    # 기존 인터페이스 유지 (Question Generation)
    # ===========================================
    
    async def generate_questions(
        self, 
        goal: str, 
        intent_title: str, 
        user_country: Optional[str] = None,
        user_language: Optional[str] = None,
        country_option: bool = True
    ) -> List[Question]:
        """선택된 의도를 기반으로 맞춤형 질문 생성
        
        기존 인터페이스 그대로 유지하면서 QuestionGenerationService에 위임
        """
        logger.debug(f"Facade: Delegating question generation for intent: '{intent_title}'")
        
        return await self.question_service.generate_questions(
            goal=goal,
            intent_title=intent_title,
            user_country=user_country,
            user_language=user_language,
            country_option=country_option
        )
    
    async def generate_questions_stream(
        self, 
        goal: str, 
        intent_title: str, 
        user_country: Optional[str] = None,
        user_language: Optional[str] = None,
        country_option: bool = True
    ) -> AsyncGenerator[str, None]:
        """실시간 스트리밍으로 맞춤형 질문 생성
        
        기존 인터페이스 그대로 유지하면서 QuestionGenerationService에 위임
        """
        logger.debug(f"Facade: Delegating streaming question generation for intent: '{intent_title}'")
        
        async for chunk in self.question_service.generate_questions_stream(
            goal=goal,
            intent_title=intent_title,
            user_country=user_country,
            user_language=user_language,
            country_option=country_option
        ):
            yield chunk
    
    # ===========================================
    # 기존 인터페이스 유지 (Search Functionality)
    # ===========================================
    
    async def parallel_search(self, queries: List[str]) -> List[SearchResult]:
        """다중 검색 쿼리 병렬 실행
        
        기존 인터페이스 그대로 유지하면서 SearchService에 위임
        """
        logger.debug(f"Facade: Delegating parallel search for {len(queries)} queries")
        
        return await self.search_service.parallel_search(queries)
    
    def generate_search_queries_from_checklist(
        self,
        checklist_items: List[str],
        goal: str,
        answers: List[Dict[str, Any]]
    ) -> List[str]:
        """체크리스트 아이템 기반 검색 쿼리 생성
        
        기존 인터페이스 그대로 유지하면서 SearchService에 위임
        """
        logger.debug(f"Facade: Delegating search query generation for {len(checklist_items)} items")
        
        return self.search_service.generate_search_queries_from_checklist(
            checklist_items=checklist_items,
            goal=goal,
            answers=answers
        )
    
    # ===========================================
    # 추가 편의 메소드 (기존 코드에서 필요한 경우)
    # ===========================================
    
    def get_service_status(self) -> Dict[str, str]:
        """각 서비스의 상태 정보 반환 (디버깅/모니터링용)
        
        비즈니스 로직:
        - 각 전용 서비스의 초기화 및 작동 상태 확인
        - 문제가 있는 서비스 식별을 통한 빠른 장애 진단
        - 운영 모니터링 및 헬스 체크에 활용
        """
        status = {
            "facade": "initialized",
            "api_client": "initialized" if hasattr(self, 'api_client') else "not_initialized",
            "intent_service": "initialized" if hasattr(self, 'intent_service') else "not_initialized",
            "question_service": "initialized" if hasattr(self, 'question_service') else "not_initialized", 
            "search_service": "initialized" if hasattr(self, 'search_service') else "not_initialized"
        }
        
        logger.debug(f"Service status check: {status}")
        return status
    
    # ===========================================
    # 기존 코드에서 사용될 수 있는 내부 메소드들
    # (private 메소드들은 각 서비스에서 처리하므로 제거)
    # ===========================================
    
    def _get_default_template(self) -> List[IntentOption]:
        """기본 의도 템플릿 제공 (하위 호환성)
        
        기존 코드에서 이 메소드를 직접 호출하는 경우를 위한 래퍼
        """
        logger.debug("Facade: Providing default template via IntentAnalysisService")
        return self.intent_service._get_default_template()
    
    def _get_cached_questions_template(self, intent_title: str) -> List[Question]:
        """캐시된 질문 템플릿 제공 (하위 호환성)
        
        기존 코드에서 이 메소드를 직접 호출하는 경우를 위한 래퍼
        """
        logger.debug(f"Facade: Providing cached questions template for intent: '{intent_title}'")
        return self.question_service._get_cached_template(intent_title)
    
    # ===========================================
    # 범용 API 호출 메서드 (하위 호환성)
    # ===========================================
    
    async def _call_gemini_api(self, prompt: str) -> str:
        """범용 Gemini API 호출 (하위 호환성)
        
        기존 코드에서 직접 API 호출이 필요한 경우를 위한 래퍼
        checklist_orchestrator.py 등에서 사용
        """
        logger.debug("Facade: Delegating generic API call to ApiClient")
        return await self.api_client.call_api(prompt)
    
    async def _call_gemini_api_with_search(self, prompt: str) -> str:
        """검색 기능이 포함된 Gemini API 호출 (하위 호환성)"""
        logger.debug("Facade: Delegating search-enabled API call to ApiClient")
        return await self.api_client.call_api_with_search(prompt)
    
    async def _call_gemini_api_for_checklist(self, prompt: str) -> str:
        """체크리스트 생성 전용 Gemini API 호출 (Structured Output)
        
        비즈니스 로직:
        - 체크리스트 전용 JSON 스키마를 사용한 구조화된 응답
        - 마크다운 블록 없이 깨끗한 JSON만 반환
        - checklist_orchestrator.py에서 사용하기 위한 전용 메서드
        """
        logger.debug("Facade: Delegating checklist generation to ApiClient with schema")
        return await self.api_client.call_api_for_checklist(prompt)


# 기존 코드와의 완전한 호환성을 위한 인스턴스 생성
# 기존 코드에서 `from app.services.gemini_service import gemini_service` 형태로 import하는 경우
gemini_service = GeminiService()