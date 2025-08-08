"""
Gemini 서비스 공통 유틸리티 함수

비즈니스 로직:
- 여러 서비스에서 공통으로 사용하는 헬퍼 함수들 중앙화
- 지역/언어 컨텍스트 생성, JSON 처리 등 반복되는 로직 모듈화
- 코드 중복 제거 및 일관된 처리 방식 보장
"""

import json
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def get_country_context(user_country: Optional[str]) -> str:
    """국가별 문화적 맥락 생성
    
    비즈니스 로직:
    - 사용자의 국가 코드를 기반으로 해당 국가의 문화적 특성 제공
    - 질문 생성 시 각 국가의 문화와 환경을 고려한 맞춤형 컨텐츠 제공
    - 지원되지 않는 국가의 경우 범용적인 글로벌 기준 제공
    - 캐시된 매핑 데이터로 빠른 컨텍스트 생성
    """
    contexts: Dict[str, str] = {
        "KR": "한국 거주자 기준, 한국 문화와 환경 고려",
        "US": "미국 거주자 기준, 미국 문화와 환경 고려", 
        "JP": "일본 거주자 기준, 일본 문화와 환경 고려",
        "CN": "중국 거주자 기준, 중국 문화와 환경 고려"
    }
    return contexts.get(user_country, "글로벌 기준")


def get_language_context(user_language: Optional[str]) -> str:
    """언어별 문화적 맥락 생성
    
    비즈니스 로직:
    - 사용자의 언어 코드를 기반으로 해당 언어권의 문화적 맥락 제공
    - 다양한 언어권의 문화적 특성을 고려한 질문 생성
    - 다국어 지원을 위한 다양한 언어화 컨텍스트 매핑
    - 지원되지 않는 언어의 경우 다국어 지원 기본값 제공
    """
    contexts: Dict[str, str] = {
        "ko": "한국어 기준, 한국 문화적 맥락 고려",
        "en": "English, Western cultural context",
        "ja": "日本語、日本の文化的文脈を考慮",
        "zh": "中文，中国文化背景考虑",
        "es": "Español, contexto cultural hispano",
        "fr": "Français, contexte culturel français"
    }
    return contexts.get(user_language, "다국어 지원")


def extract_json_from_markdown(content: str) -> str:
    """마크다운 코드 블록에서 순수 JSON 추출
    
    비즈니스 로직:
    - Gemini API에서 반환하는 ```json...``` 형태의 마크다운 래핑 제거
    - JSON 코드 블록이 있으면 내부 JSON만 추출
    - 코드 블록이 없으면 첫번째 {부터 마지막 }까지 추출
    - 추출 실패 시 원본 컨텐츠 그대로 반환하여 안정성 보장
    """
    try:
        content = content.strip()
        
        # ```json...``` 패턴 찾기
        if '```json' in content:
            start = content.find('```json') + 7
            end = content.rfind('```')
            if end > start:
                json_content = content[start:end].strip()
                return json_content
        
        # JSON 패턴이 없으면 전체 내용 반환 (첫 { 부터 마지막 } 까지)
        first_brace = content.find('{')
        last_brace = content.rfind('}')
        
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            return content[first_brace:last_brace + 1]
        
        return content
        
    except Exception as e:
        logger.error(f"JSON extraction error: {str(e)}")
        return content


def validate_json_structure(content: str, expected_fields: list[str]) -> tuple[bool, dict]:
    """JSON 구조 유효성 검증
    
    비즈니스 로직:
    - 파싱된 JSON이 예상한 필드들을 모두 포함하는지 검증
    - 구조적 완전성을 보장하여 downstream 처리 안정성 확보
    - 검증 성공 시 파싱된 데이터 반환으로 중복 파싱 방지
    - 실패 시 상세한 오류 정보 로깅으로 디버깅 지원
    """
    try:
        # 마크다운에서 JSON 추출
        clean_content = extract_json_from_markdown(content)
        
        # JSON 파싱 시도
        parsed_data = json.loads(clean_content)
        
        # 필수 필드 검증
        missing_fields = []
        for field in expected_fields:
            if field not in parsed_data:
                missing_fields.append(field)
        
        if missing_fields:
            logger.warning(f"Missing required fields: {missing_fields}")
            return False, {}
        
        return True, parsed_data
        
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parsing failed: {str(e)}")
        return False, {}
    except Exception as e:
        logger.error(f"JSON validation error: {str(e)}")
        return False, {}


def create_error_result(query: str, error_message: str):
    """검색 오류 시 기본 SearchResult 객체 생성
    
    비즈니스 로직:
    - 검색 실패 시에도 일관된 SearchResult 구조로 결과 반환
    - success=False로 설정하여 상위 레이어에서 실패 처리 가능
    - error_message에 상세 오류 정보 저장
    - 빈 content와 sources로 오류 상황 명시
    """
    from .config import SearchResult
    
    return SearchResult(
        query=query,
        content="",
        sources=[],
        success=False,
        error_message=error_message
    )