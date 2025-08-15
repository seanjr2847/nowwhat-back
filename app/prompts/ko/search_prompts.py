"""한국어 검색 기능을 위한 Gemini 프롬프트와 응답 형식"""
import json
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel

# 응답 스키마 정의
class ContactInfo(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None

class LinkInfo(BaseModel):
    title: str
    url: str

class SearchResponse(BaseModel):
    tips: List[str]
    contacts: List[ContactInfo]
    links: List[LinkInfo]
    price: Optional[str] = None
    location: Optional[str] = None

def get_search_prompt(checklist_item: str, user_country: str = None, user_language: str = None) -> str:
    """체크리스트 아이템 기반 웹 검색용 한국어 프롬프트 생성 (responseSchema 전용)"""
    current_year = datetime.now().year
    
    return f"""다음 단계를 따라 "{checklist_item}"에 대한 정보를 제공하세요.

단계 1: 먼저 "{checklist_item}"이 무엇인지 이해하기
단계 2: 사용자가 실제로 실행할 수 있는 구체적인 행동 3-5개 생각하기
단계 3: 각 행동을 독립적인 완전한 문장으로 작성하기
단계 4: 아래 예시 형식대로 JSON 구성하기

예시 1:
검색: "여행 보험 가입하기"
생각 과정: 여행 보험은 여행 중 발생할 수 있는 위험을 보장한다. 사용자는 적절한 상품 선택, 보장 범위 확인, 가입 절차가 필요하다.
응답: {{
  "tips": [
    "여행 기간과 목적지를 고려하여 적절한 보장 한도를 선택하세요",
    "의료비와 휴대품 손실 보장이 포함되어 있는지 확인하세요",
    "카드사 제공 여행자 보험과 중복 보장 여부를 체크하세요",
    "보험 가입 전 기존 질환 고지 의무사항을 확인하세요"
  ],
  "contacts": [],
  "links": [{{"title": "여행자보험 비교사이트", "url": "https://example.com"}}],
  "price": "일일 3,000원부터",
  "location": null
}}

예시 2:
검색: "운동 루틴 만들기"
생각 과정: 운동 루틴은 규칙적인 운동 계획이다. 사용자는 시간 설정, 운동 종류 선택, 강도 조절, 기록 관리가 필요하다.
응답: {{
  "tips": [
    "주 3-4회 규칙적인 운동 시간을 정하고 캘린더에 표시하세요",
    "근력운동과 유산소운동을 균형있게 배분하여 계획하세요",
    "본인의 체력 수준에 맞는 강도로 시작하여 점진적으로 높이세요",
    "운동 전후 충분한 스트레칭으로 부상을 예방하세요",
    "매주 운동 기록을 작성하여 진전 상황을 추적하세요"
  ],
  "contacts": [],
  "links": [],
  "price": null,
  "location": null
}}

예시 3:
검색: "이력서 작성하기"
생각 과정: 이력서는 구직 활동의 필수 문서다. 사용자는 구성 방법, 내용 강조, 형식 준수가 필요하다.
응답: {{
  "tips": [
    "최근 경력부터 역순으로 작성하여 가독성을 높이세요",
    "구체적인 성과와 수치를 포함하여 신뢰성을 높이세요",
    "지원하는 직무와 관련된 핵심 역량을 강조하세요",
    "간결하고 명확한 문장으로 2페이지 이내로 작성하세요"
  ],
  "contacts": [],
  "links": [{{"title": "이력서 템플릿", "url": "https://example.com"}}],
  "price": null,
  "location": null
}}

이제 "{checklist_item}"에 대해:
1. 먼저 이것이 무엇인지 이해하고
2. 실행 가능한 구체적 행동들을 생각하고
3. 위 예시와 똑같은 JSON 형식으로 응답하세요

상황: {user_country or '한국'}, {current_year}년

중요한 규칙:
- 생각 과정은 포함하지 말고 최종 JSON 응답만 제공하세요
- tips 배열 안에는 절대 JSON 구조를 포함하지 마세요
- tips 안에 "tips:", "[", "]", "{", "}" 같은 문자는 절대 사용 금지
- ```json 같은 마크다운 코드 블록도 사용 금지
- 각 tip은 완전한 한국어 문장이어야 합니다

반드시 이런 형태여야 합니다:
"tips": [
  "첫 번째 실용적인 조언입니다",
  "두 번째 실용적인 조언입니다",
  "세 번째 실용적인 조언입니다"
]"""