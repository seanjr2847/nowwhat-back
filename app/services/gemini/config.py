"""
Gemini 서비스 공통 설정 및 예외 클래스

비즈니스 로직:
- 모든 Gemini 서비스에서 사용하는 공통 상수 및 설정값 중앙화
- 일관된 예외 처리를 위한 계층적 예외 클래스 구조
- 환경별 설정 변경 시 한 곳에서 관리 가능
- 타입 안전성과 IDE 자동완성을 위한 클래스 기반 상수 정의
"""

from dataclasses import dataclass
from typing import Any, Dict


class GeminiConfig:
    """Gemini 서비스 공통 설정 상수
    
    비즈니스 로직:
    - API 호출 안정성을 위한 재시도 및 타임아웃 설정
    - 스트리밍 성능 최적화를 위한 청크 크기 및 지연 시간
    - 응답 품질 제어를 위한 생성 파라미터 (temperature, top_p, top_k)
    - 검색 성능과 비용 효율성을 위한 동시 검색 제한
    """
    
    # API 호출 안정성 설정
    RETRY_ATTEMPTS = 3
    TIMEOUT_SECONDS = 30
    
    # 응답 기대값 및 검증 기준
    EXPECTED_INTENTS_COUNT = 4
    MIN_CONTENT_LENGTH = 50
    
    # 스트리밍 성능 설정  
    CHUNK_SIZE = 100
    STREAM_DELAY = 0.01  # 10ms
    
    # Gemini API 생성 파라미터
    MAX_OUTPUT_TOKENS = 20480
    TEMPERATURE = 0.7
    TOP_P = 0.8
    TOP_K = 40
    
    # 검색 성능 설정
    CONCURRENT_SEARCH_LIMIT = 15


@dataclass
class SearchResult:
    """Gemini API 검색 결과 데이터 클래스
    
    비즈니스 로직:
    - 웹 검색 결과의 구조화된 데이터 표현
    - success 플래그로 성공/실패 구분하여 오류 처리 단순화
    - sources 배열로 정보 출처 추적 및 신뢰성 확보
    - error_message로 실패 시 상세 원인 제공
    """
    query: str
    content: str
    sources: list[str]
    success: bool
    error_message: str = None


class GeminiServiceError(Exception):
    """Gemini 서비스 기본 예외 클래스
    
    비즈니스 로직:
    - 모든 Gemini 관련 예외의 상위 클래스로 일관된 예외 처리
    - 특정 서비스 예외를 포착할 때 이 클래스로 통합 처리 가능
    - 로깅 및 모니터링 시스템에서 Gemini 관련 오류 그룹화 지원
    """
    pass


class GeminiAPIError(GeminiServiceError):
    """Gemini API 호출 실패 예외
    
    비즈니스 로직:
    - API 연결, 인증, 요청 형식 오류 등 API 수준의 문제
    - 네트워크 이슈, 서버 오류, 할당량 초과 등 외부 요인
    - 재시도 로직의 판단 기준으로 활용
    """
    pass


class GeminiResponseError(GeminiServiceError):
    """Gemini 응답 파싱 실패 예외
    
    비즈니스 로직:
    - API는 성공했지만 응답 데이터가 예상 형식과 다른 경우
    - JSON 파싱 오류, 필수 필드 누락, 데이터 타입 불일치 등
    - 폴백 데이터 생성 로직의 트리거 역할
    """
    pass