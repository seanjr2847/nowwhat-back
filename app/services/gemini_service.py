"""
Gemini 서비스 - 리팩토링된 모듈화 구조

이 파일은 기존 코드와의 호환성을 위해 유지되며, 
실제 구현은 app.services.gemini 패키지의 모듈화된 서비스들에서 처리됩니다.

SOLID 원칙 적용:
- SRP: 각 서비스는 단일 책임만 담당
- OCP: 새로운 기능 추가 시 기존 코드 수정 없이 확장 가능
- LSP: 인터페이스 기반으로 대체 가능한 구조
- ISP: 각 클라이언트는 필요한 기능만 의존
- DIP: 구체적 구현이 아닌 추상화에 의존
"""

# 기존 코드와의 완전한 호환성을 위해 동일한 import 경로 유지
from app.services.gemini.facade import GeminiService, gemini_service

# 개별 서비스들도 import 가능하도록 노출 (선택적 사용)
from app.services.gemini import (
    IntentAnalysisService,
    QuestionGenerationService,
    SearchService,
    StreamingService,
    GeminiApiClient,
    GeminiConfig,
    GeminiServiceError,
    GeminiAPIError,
    GeminiResponseError
)

# 하위 호환성을 위한 기존 import 패턴 지원
from app.services.gemini.config import SearchResult

# 기존 코드에서 직접 import하는 클래스들
__all__ = [
    'GeminiService',
    'gemini_service',  # 기존 코드에서 사용하는 인스턴스
    'IntentAnalysisService',
    'QuestionGenerationService',
    'SearchService', 
    'StreamingService',
    'GeminiApiClient',
    'GeminiConfig',
    'GeminiServiceError',
    'GeminiAPIError',
    'GeminiResponseError',
    'SearchResult'
]
