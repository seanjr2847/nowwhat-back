"""
Gemini 서비스 패키지

SOLID 원칙을 적용한 Gemini AI 서비스들의 모듈화된 구조
- 각 서비스는 단일 책임을 가짐 (SRP)
- 인터페이스 기반 의존성 주입 (DIP)
- 확장 가능한 구조 (OCP)
"""

# Facade 패턴으로 기존 코드와의 호환성 유지
from .facade import GeminiService

# 개별 서비스들도 직접 import 가능
from .intent_analysis_service import IntentAnalysisService
from .question_generation_service import QuestionGenerationService
from .search_service import SearchService
from .streaming_service import StreamingService
from .api_client import GeminiApiClient
from .config import GeminiConfig, GeminiServiceError, GeminiAPIError, GeminiResponseError

__all__ = [
    'GeminiService',  # 메인 Facade
    'IntentAnalysisService',
    'QuestionGenerationService', 
    'SearchService',
    'StreamingService',
    'GeminiApiClient',
    'GeminiConfig',
    'GeminiServiceError',
    'GeminiAPIError', 
    'GeminiResponseError'
]