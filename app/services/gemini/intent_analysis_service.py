"""
의도 분석 전용 서비스

비즈니스 로직:
- 사용자 목표를 분석하여 4가지 구체적인 실행 의도로 분류하는 단일 책임
- 지역정보와 언어정보를 활용한 맞춤형 의도 생성
- 3회 재시도 메커니즘으로 API 실패 시 안정성 보장
- API 실패 시 기본 템플릿으로 폴백하여 서비스 중단 방지
"""

import asyncio
import json
import logging
from typing import List, Optional

from app.schemas.nowwhat import IntentOption
from app.prompts.prompt_selector import get_intent_analysis_prompt
from .api_client import GeminiApiClient
from .config import GeminiConfig, GeminiResponseError
from .utils import validate_json_structure

logger = logging.getLogger(__name__)


class IntentAnalysisService:
    """사용자 목표 의도 분석 전용 서비스 (SRP)
    
    비즈니스 로직:
    - 사용자가 입력한 목표를 분석하여 4가지 구체적인 실행 의도 옵션 생성
    - 지역정보(country_info)와 언어정보(language_info)를 활용한 본화형 의도 생성
    - 3회 재시도 메커니즘으로 일시적 API 실패 극복
    - 모든 시도 실패 시 범용 기본 템플릿으로 폴백하여 서비스 연속성 보장
    """
    
    def __init__(self, api_client: GeminiApiClient):
        """의도 분석 서비스 초기화
        
        Args:
            api_client: Gemini API 클라이언트 (DIP - 의존성 주입)
        """
        self.api_client = api_client
        logger.info("IntentAnalysisService initialized")
    
    async def analyze_intent(
        self, 
        goal: str, 
        country_info: str = "", 
        language_info: str = "", 
        country_option: bool = True
    ) -> List[IntentOption]:
        """사용자 목표 분석 및 의도 옵션 생성
        
        비즈니스 로직:
        - 사용자 입력 목표를 Gemini AI로 분석하여 4가지 구체적인 실행 의도 도출
        - 지역정보(country_info)와 언어정보(language_info)를 활용한 맞춤형 의도 생성
        - 3회 재시도 메커니즘으로 API 실패 시 안정성 보장
        - API 실패 시 기본 템플릿으로 폴백하여 서비스 중단 방지
        
        Args:
            goal: 사용자가 달성하고자 하는 목표
            country_info: 사용자 국가/지역 정보 (선택적)
            language_info: 사용자 언어 정보 (선택적) 
            country_option: 지역정보 포함 여부 플래그
            
        Returns:
            List[IntentOption]: 4가지 의도 옵션 리스트
        """
        try:
            # 사용자 언어 추출 및 프롬프트 생성
            user_language = self._extract_user_language(language_info)
            prompt = self._create_intent_prompt(
                goal, country_info, language_info, user_language, country_option
            )
            
            # 재시도 로직을 통한 의도 분석
            intents = await self._analyze_with_retry(prompt)
            
            return intents if intents else self._get_default_template()
            
        except Exception as e:
            logger.error(f"Intent analysis failed: {str(e)}")
            return self._get_default_template()
    
    async def _analyze_with_retry(self, prompt: str) -> Optional[List[IntentOption]]:
        """재시도 메커니즘을 통한 안정적인 의도 분석
        
        비즈니스 로직:
        - Gemini API 호출 실패 시 최대 3회 재시도하여 일시적 네트워크 오류 극복
        - 각 재시도 간 지수백오프 적용으로 서버 부하 최소화
        - 구조화된 출력 형식으로 일관된 응답 데이터 보장
        - 파싱 실패 시에도 재시도하여 데이터 무결성 확보
        """
        for attempt in range(GeminiConfig.RETRY_ATTEMPTS):
            try:
                # API 호출 및 응답 파싱
                response = await self.api_client.call_api(prompt)
                intents = self._parse_intent_response(response)
                
                # 응답 검증 (4개의 의도가 생성되었는지)
                if len(intents) == GeminiConfig.EXPECTED_INTENTS_COUNT:
                    logger.info(f"✅ Intent analysis successful: {len(intents)} intents generated")
                    return intents
                else:
                    logger.warning(f"⚠️ Expected {GeminiConfig.EXPECTED_INTENTS_COUNT} intents, got {len(intents)} (attempt {attempt + 1})")
                    
            except Exception as e:
                logger.error(f"❌ Intent analysis attempt {attempt + 1} failed: {str(e)}")
                if attempt < GeminiConfig.RETRY_ATTEMPTS - 1:
                    wait_time = 2 ** attempt  # 지수백오프: 1s, 2s, 4s
                    logger.info(f"⏳ Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                
        logger.warning("🚨 All intent analysis attempts failed, using default template")
        return None
    
    def _create_intent_prompt(
        self, 
        goal: str, 
        country_info: str, 
        language_info: str, 
        user_language: str, 
        country_option: bool
    ) -> str:
        """의도 분석용 프롬프트 생성
        
        비즈니스 로직:
        - 사용자 목표와 지역/언어 정보를 통합한 맞춤형 프롬프트 생성
        - 지역별 문화적 맥락과 언어별 표현 방식을 고려한 프롬프트 최적화
        - country_option 설정에 따른 상세 지역 정보 포함 여부 결정
        - 프롬프트 생성기에 전달할 구조화된 매개변수 준비
        """
        return get_intent_analysis_prompt(
            goal=goal,
            country_info=country_info or "정보 없음",
            language_info=language_info or "정보 없음",
            user_language=user_language,
            country_option=country_option
        )
    
    def _extract_user_language(self, language_info: str) -> str:
        """언어 정보에서 사용자 언어 코드 추출
        
        비즈니스 로직:
        - 다양한 형태의 언어 정보에서 표준 언어 코드 추출
        - 'ko-KR' 형태에서 'ko' 추출, 'Korean' 등의 언어명 처리
        - 지원되지 않는 언어의 경우 'ko' (한국어)를 기본값으로 설정
        - 추출된 언어 코드를 프롬프트 생성에 활용
        """
        if not language_info:
            return "ko"
        
        # 'ko-KR' 형태에서 'ko' 추출
        if '-' in language_info:
            return language_info.split('-')[0].lower()
        
        # 언어명을 코드로 변환
        language_map = {
            'korean': 'ko', 'english': 'en', 'japanese': 'ja', 
            'chinese': 'zh', 'spanish': 'es', 'french': 'fr'
        }
        
        lang_lower = language_info.lower()
        for lang_name, lang_code in language_map.items():
            if lang_name in lang_lower:
                return lang_code
        
        # 기본값
        return "ko"
    
    def _parse_intent_response(self, response: str) -> List[IntentOption]:
        """Gemini API 의도 분석 응답 파싱
        
        비즈니스 로직:
        - Gemini에서 수신한 JSON 형태의 의도 데이터를 IntentOption 객체로 변환
        - 마크다운 코드 블록 내에서 JSON 데이터 추출
        - 의도 구조 및 필수 필드 유효성 검증
        - 파싱 실패 시 예외 발생으로 상위 레이어에 오류 전파
        """
        try:
            # JSON 구조 검증 및 파싱
            is_valid, parsed_data = validate_json_structure(response, ['intents'])
            if not is_valid:
                raise GeminiResponseError("Invalid JSON structure or missing 'intents' field")
            
            # intents 배열 추출
            intents_data = parsed_data.get('intents', [])
            if not isinstance(intents_data, list):
                # 직접 리스트인 경우도 처리
                intents_data = parsed_data if isinstance(parsed_data, list) else []
            
            logger.debug(f"Found {len(intents_data)} intent items")
            
            # IntentOption 객체로 변환
            intents = []
            for item in intents_data:
                # 필수 필드 검증
                required_fields = ["title", "description", "icon"]
                if not all(field in item for field in required_fields):
                    missing = [f for f in required_fields if f not in item]
                    raise GeminiResponseError(f"Missing required fields in intent: {missing}")
                    
                intents.append(IntentOption(
                    title=item["title"],
                    description=item["description"],
                    icon=item["icon"]
                ))
            
            logger.info(f"✅ Successfully parsed {len(intents)} intent options")
            return intents
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            raise GeminiResponseError(f"Failed to parse intent response: Invalid JSON - {str(e)}")
        except Exception as e:
            logger.error(f"Intent parsing error: {str(e)}")
            raise GeminiResponseError(f"Failed to parse intent response: {str(e)}")
    
    def _get_default_template(self) -> List[IntentOption]:
        """API 실패 시 기본 의도 템플릿 제공
        
        비즈니스 로직:
        - Gemini API 전체 실패 시 서비스 연속성을 위한 기본 의도 옵션 제공
        - 일반적인 사용자 목표에 적용 가능한 4가지 보편적 의도 타입
        - 각 의도는 아이콘, 제목, 설명을 포함한 완전한 구조
        - 사용자가 똑같이 4가지 옵션을 받을 수 있도록 보장
        """
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