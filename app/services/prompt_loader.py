from typing import Optional
import logging

logger = logging.getLogger(__name__)

class PromptLoader:
    """프롬프트를 로드하고 관리하는 서비스"""
    
    def get_intent_analysis_prompt(self, goal: str, user_country: Optional[str] = None) -> str:
        """의도 분석 프롬프트를 가져옵니다."""
        try:
            from app.prompts.intent_analysis import get_intent_analysis_prompt
            country_info = f"거주 국가: {user_country}" if user_country else ""
            return get_intent_analysis_prompt(goal, country_info)
        except ImportError as e:
            logger.error(f"Failed to import intent analysis prompt: {e}")
            raise
    
    def get_questions_generation_prompt(
        self, 
        goal: str, 
        intent_title: str, 
        user_country: Optional[str] = None,
        country_context: str = "글로벌 기준"
    ) -> str:
        """질문 생성 프롬프트를 가져옵니다."""
        try:
            from app.prompts.questions_generation import get_questions_generation_prompt
            return get_questions_generation_prompt(
                goal=goal,
                intent_title=intent_title,
                user_country=user_country or "알 수 없음",
                country_context=country_context
            )
        except ImportError as e:
            logger.error(f"Failed to import questions generation prompt: {e}")
            raise

# 전역 인스턴스
prompt_loader = PromptLoader()