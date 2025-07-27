import json
import asyncio
from typing import List, Dict, Optional
import google.generativeai as genai
from app.core.config import settings
from app.schemas.nowwhat import IntentOption
import logging

logger = logging.getLogger(__name__)

# Gemini API 설정
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)

class GeminiService:
    def __init__(self):
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
        
    async def analyze_intent(self, goal: str, user_country: Optional[str] = None) -> List[IntentOption]:
        """사용자 목표를 분석하여 4가지 의도 옵션 생성"""
        try:
            prompt = self._create_prompt(goal, user_country)
            
            # 3회 재시도 로직
            for attempt in range(3):
                try:
                    response = await self._call_gemini_api(prompt)
                    intents = self._parse_response(response)
                    
                    if len(intents) == 4:
                        return intents
                    else:
                        logger.warning(f"Gemini returned {len(intents)} intents instead of 4 (attempt {attempt + 1})")
                        
                except Exception as e:
                    logger.error(f"Gemini API call failed (attempt {attempt + 1}): {str(e)}")
                    if attempt < 2:  # 마지막 시도가 아니면 지연 후 재시도
                        await asyncio.sleep(2 ** attempt)  # exponential backoff
                    
            # 모든 재시도 실패시 기본 템플릿 반환
            logger.warning("All Gemini API attempts failed, using default template")
            return self._get_default_template()
            
        except Exception as e:
            logger.error(f"Intent analysis failed: {str(e)}")
            return self._get_default_template()
    
    def _create_prompt(self, goal: str, user_country: Optional[str] = None) -> str:
        """Gemini API용 프롬프트 생성"""
        country_info = f"거주 국가: {user_country}" if user_country else ""
        
        return f"""당신은 사용자의 막연한 목표를 명확한 의도로 분류하는 전문가입니다.

사용자 입력: "{goal}"
{country_info}

이 목표를 달성하기 위해 사용자가 원할 수 있는 4가지 의도를 생성하세요.
각 의도는 서로 다른 관점에서 접근해야 합니다:
1. 계획/일정 관련
2. 준비/체크리스트 관련
3. 정보/조사 관련
4. 실행/예약 관련

응답 형식 (JSON):
[
  {{
    "title": "짧고 명확한 제목",
    "description": "어떤 도움을 원하는지 구체적 설명 (~하고 싶으신가요?)",
    "icon": "관련 이모지"
  }}
]

중요: 정확히 4개만 생성하고, 유효한 JSON 형식으로 응답하세요."""

    async def _call_gemini_api(self, prompt: str) -> str:
        """Gemini API 호출"""
        try:
            response = await asyncio.to_thread(
                self.model.generate_content, 
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=1000,
                    temperature=0.7,
                )
            )
            return response.text
        except Exception as e:
            raise Exception(f"Gemini API call failed: {str(e)}")
    
    def _parse_response(self, response: str) -> List[IntentOption]:
        """Gemini 응답 파싱"""
        try:
            # JSON 부분만 추출 (마크다운 코드 블록 제거)
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            intents_data = json.loads(response)
            
            if not isinstance(intents_data, list):
                raise ValueError("Response is not a list")
                
            intents = []
            for item in intents_data:
                if not all(key in item for key in ["title", "description", "icon"]):
                    raise ValueError("Missing required fields in intent")
                    
                intents.append(IntentOption(
                    title=item["title"],
                    description=item["description"],
                    icon=item["icon"]
                ))
                
            return intents
            
        except Exception as e:
            raise Exception(f"Failed to parse Gemini response: {str(e)}")
    
    def _get_default_template(self) -> List[IntentOption]:
        """기본 의도 템플릿"""
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

# 서비스 인스턴스
gemini_service = GeminiService() 