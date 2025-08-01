"""검색 기능을 위한 Gemini 프롬프트와 응답 형식"""
import json
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

def get_search_prompt(query: str) -> str:
    """웹 검색용 프롬프트 생성"""
    return f"""다음 주제에 대해 최신 정보를 웹에서 검색하여 한국어로 구체적이고 실용적인 정보를 제공해주세요: "{query}"

웹 검색을 통해 다음 정보들을 찾아서 제공해주세요:

1. **실용적인 팁들**: 이 주제와 관련된 구체적이고 실행 가능한 조언들
2. **연락처 정보**: 관련 서비스나 기관의 실제 연락처 (이름, 전화번호, 이메일)
3. **유용한 링크**: 참고할 만한 웹사이트나 리소스 (제목과 URL)
4. **가격 정보**: 관련 비용이나 예산 범위
5. **위치 정보**: 관련 장소나 지역 정보

중요 요구사항:
- 반드시 "{query}" 주제와 직접 관련된 최신 정보만 제공하세요
- 실제 존재하는 웹사이트 URL과 연락처를 우선적으로 제공하세요
- 2024년 기준의 최신 동향과 정보를 반영하세요
- 한국 시장과 환경에 맞는 정보를 우선하세요
- 정보가 없는 항목은 비워두세요"""