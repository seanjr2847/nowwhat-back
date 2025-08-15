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
    steps: List[str]  # tips를 steps로 변경 - 실행 가능한 단계별 가이드
    contacts: List[ContactInfo]
    links: List[LinkInfo]
    price: Optional[str] = None
    location: Optional[str] = None

def get_search_prompt(checklist_item: str, user_country: str = None, user_language: str = None) -> str:
    """체크리스트 아이템 기반 웹 검색용 한국어 프롬프트 생성 (responseSchema 전용)"""
    current_year = datetime.now().year
    
    return f""""{checklist_item}"을 완료하기 위한 구체적인 실행 단계를 제공하세요.

작업 지침:
1. "{checklist_item}"이 무엇인지 파악하기
2. 실제로 완료하기 위해 필요한 순차적 행동 단계 3-5개 작성
3. 각 단계는 "1단계:", "2단계:" 형식으로 시작
4. 구체적이고 실행 가능한 행동으로 작성

예시 1:
항목: "여행 보험 가입하기"
응답: {{
  "steps": [
    "1단계: 여행 일정과 목적지를 확인하고 필요한 보장 항목(의료비, 휴대품 손실 등)을 목록화하세요",
    "2단계: 2-3개 보험사 웹사이트를 방문하여 여행자 보험 상품을 비교하세요",
    "3단계: 보험료와 보장 한도를 비교하여 가장 적합한 상품을 선택하세요",
    "4단계: 온라인으로 가입 신청서를 작성하고 결제를 완료하세요",
    "5단계: 보험증서를 이메일로 받아 여행 시 휴대폰에 저장하세요"
  ],
  "contacts": [],
  "links": [{{"title": "여행자보험 비교사이트", "url": "https://example.com"}}],
  "price": "일일 3,000원부터",
  "location": null
}}

예시 2:
항목: "운동 루틴 만들기"
응답: {{
  "steps": [
    "1단계: 자신의 현재 체력 수준과 운동 가능한 시간대를 파악하세요",
    "2단계: 주 3-4회 운동할 요일과 시간을 정하고 캘린더에 반복 일정으로 등록하세요",
    "3단계: 각 운동일에 할 운동 종류(월-상체, 수-하체, 금-전신 등)를 구체적으로 계획하세요",
    "4단계: 첫 주는 가벼운 강도로 시작하여 매주 10%씩 운동량을 늘리세요",
    "5단계: 운동 일지 앱을 다운받아 매일 운동 내용과 느낀점을 기록하세요"
  ],
  "contacts": [],
  "links": [],
  "price": null,
  "location": null
}}

예시 3:
항목: "이력서 작성하기"
응답: {{
  "steps": [
    "1단계: 지원하려는 회사의 채용공고를 읽고 요구사항과 우대사항을 정리하세요",
    "2단계: 최근 3년간의 경력과 프로젝트를 시간순으로 목록화하세요",
    "3단계: 각 경력별로 구체적인 성과와 수치(매출 증가율, 처리 건수 등)를 추가하세요",
    "4단계: 이력서 템플릿을 선택하고 개인정보, 경력, 학력, 자격증 순으로 작성하세요",
    "5단계: 완성된 이력서를 PDF로 저장하고 파일명을 '이름_직무_이력서'로 정하세요"
  ],
  "contacts": [],
  "links": [{{"title": "이력서 템플릿", "url": "https://example.com"}}],
  "price": null,
  "location": null
}}

"{checklist_item}"에 대한 실행 단계:
- 각 단계는 "N단계:"로 시작
- 구체적인 행동 동사 사용 (방문하세요, 작성하세요, 다운로드하세요 등)
- 순서대로 따라하면 완료할 수 있는 단계별 가이드

상황: {user_country or '한국'}, {current_year}년

중요 규칙:
- steps 배열에는 실행 가능한 단계만 포함
- 각 단계는 "N단계:"로 시작하는 완전한 문장
- JSON 구조나 특수문자 사용 금지
- 마크다운 코드 블록 사용 금지"""