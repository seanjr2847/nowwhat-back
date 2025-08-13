"""언어별 프롬프트 선택 및 로드 유틸리티"""
from typing import Optional
import importlib

# 지원 언어 목록
SUPPORTED_LANGUAGES = ["ko", "en"]
DEFAULT_LANGUAGE = "ko"

def get_language_code(user_language: Optional[str]) -> str:
    """사용자 언어를 기반으로 프롬프트 언어 코드 반환"""
    if not user_language:
        return DEFAULT_LANGUAGE
    
    # 언어 코드 정규화
    lang_code = user_language.lower()[:2]
    
    # 영어 계열 언어들
    if lang_code in ["en", "us", "gb", "au", "ca"]:
        return "en"
    
    # 한국어
    if lang_code in ["ko", "kr"]:
        return "ko"
    
    # 지원하지 않는 언어는 기본값 (한국어) 사용
    return DEFAULT_LANGUAGE

def load_prompt_module(module_name: str, language: Optional[str] = None):
    """언어별 프롬프트 모듈 동적 로드"""
    lang_code = get_language_code(language)
    
    try:
        # 해당 언어 프롬프트 모듈 시도
        module_path = f"app.prompts.{lang_code}.{module_name}"
        return importlib.import_module(module_path)
    except ImportError:
        try:
            # 기본 언어 프롬프트 모듈로 폴백
            fallback_path = f"app.prompts.{DEFAULT_LANGUAGE}.{module_name}"
            return importlib.import_module(fallback_path)
        except ImportError:
            # 최후 수단: 기존 프롬프트 모듈 (하위 호환성)
            fallback_path = f"app.prompts.{module_name}"
            return importlib.import_module(fallback_path)

def get_intent_analysis_prompt(goal: str, country_info: str = "", language_info: str = "", user_language: Optional[str] = None, country_option: bool = True) -> str:
    """언어별 의도 분석 프롬프트 반환"""
    module = load_prompt_module("intent_analysis", user_language)
    
    # countryOption이 False면 지역정보 제거
    if not country_option:
        country_info = ""
        language_info = ""
    
    return module.get_intent_analysis_prompt(goal, country_info, language_info)

def get_questions_generation_prompt(
    goal: str, intent_title: str, user_country: str, user_language: str, 
    country_context: str, language_context: str, country_option: bool = True
) -> str:
    """언어별 질문 생성 프롬프트 반환"""
    module = load_prompt_module("questions_generation", user_language)
    
    # countryOption이 False면 지역정보 제거
    if not country_option:
        user_country = "정보 없음"
        country_context = ""
        language_context = ""
    
    return module.get_questions_generation_prompt(
        goal, intent_title, user_country, user_language, country_context, language_context
    )

def get_checklist_generation_prompt(
    goal: str, intent_title: str, answer_context: str, 
    user_country: str = None, user_language: str = None, 
    min_items: int = None, max_items: int = None, country_option: bool = True
) -> str:
    """언어별 체크리스트 생성 프롬프트 반환"""
    module = load_prompt_module("checklist_prompts", user_language)
    
    # countryOption이 False면 지역정보 제거
    if not country_option:
        user_country = None
    
    return module.get_checklist_generation_prompt(
        goal, intent_title, answer_context, user_country, user_language, min_items, max_items
    )

# 응답 스키마들을 위한 유틸리티 함수들
def get_intent_analysis_response_class(user_language: Optional[str] = None):
    """언어별 의도 분석 응답 클래스 반환"""
    module = load_prompt_module("intent_analysis", user_language)
    return module.IntentAnalysisResponse

def get_questions_list_response_class(user_language: Optional[str] = None):
    """언어별 질문 목록 응답 클래스 반환"""
    module = load_prompt_module("questions_generation", user_language)
    return module.QuestionsListResponse

def get_checklist_response_class(user_language: Optional[str] = None):
    """언어별 체크리스트 응답 클래스 반환"""
    module = load_prompt_module("checklist_prompts", user_language)
    return module.ChecklistResponse

def get_search_prompt(checklist_item: str, user_country: str = None, user_language: str = None) -> str:
    """언어별 검색 프롬프트 반환"""
    module = load_prompt_module("search_prompts", user_language)
    return module.get_search_prompt(checklist_item, user_country, user_language)

def get_search_response_class(user_language: Optional[str] = None):
    """언어별 검색 응답 클래스 반환"""
    module = load_prompt_module("search_prompts", user_language)
    return module.SearchResponse