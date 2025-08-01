"""체크리스트 생성을 위한 Gemini 프롬프트와 응답 형식"""
from typing import List
from pydantic import BaseModel
from app.core.config import settings

# 응답 스키마 정의
class ChecklistResponse(BaseModel):
    items: List[str]

def get_checklist_generation_prompt(goal: str, intent_title: str, answer_context: str, min_items: int = None, max_items: int = None) -> str:
    """체크리스트 생성용 프롬프트 생성"""
    return f"""당신은 개인 맞춤형 체크리스트 생성 전문가입니다.

사용자 정보:
- 목표: "{goal}"
- 선택한 의도: "{intent_title}"
- 답변 내용: {answer_context}

위 정보를 바탕으로 사용자가 목표를 달성하기 위한 체계적인 체크리스트를 생성하세요.

체크리스트 생성 규칙:
1. **구체적 키워드 포함**: 각 항목에 검색 가능한 구체적 키워드를 포함하세요
   - 나쁜 예: "준비하기" → 좋은 예: "교재 구매하고 학습 계획 세우기"
   - 나쁜 예: "확인하기" → 좋은 예: "온라인 강의 플랫폼 비교 및 선택하기"

2. **실행 가능한 액션**: 사용자가 즉시 행동할 수 있는 구체적 단계
   - 구매, 예약, 신청, 다운로드, 연락, 방문, 등록 등 명확한 동사 사용
   - 브랜드명, 서비스명, 가격, 기간 등 구체적 정보 포함

3. **검색 친화적 표현**: 온라인에서 찾을 수 있는 정보와 연결되는 표현
   - "무료 언어 학습 앱 추천" → "듀오링고 앱 다운로드 및 학습 목표 설정"
   - "예산 계획" → "언어 학습 예산 월 5-10만원 범위에서 계획 수립"

4. **시간적 순서**: {min_items or settings.MIN_CHECKLIST_ITEMS}개 이상 {max_items or settings.MAX_CHECKLIST_ITEMS}개 이하로 시간 순서대로 배열

5. **답변 반영**: 사용자의 구체적 답변(예산, 기간, 방식, 파트너 등)을 각 항목에 자연스럽게 반영

예시:
- "학습할 언어와 목표 수준을 구체적으로 결정하고 3개월 학습 계획 수립하기"
- "파트너와 함께 사용할 언어 학습 앱 또는 온라인 강의 플랫폼 선택하기"
- "월 예산 범위 내에서 교재 구매 및 필요한 학습 도구 준비하기"

중요: 실제 온라인에서 검색했을 때 관련 정보, 팁, 추천사항을 쉽게 찾을 수 있도록 검색 키워드가 풍부한 체크리스트를 만드세요."""