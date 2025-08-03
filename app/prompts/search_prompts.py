"""검색 기능을 위한 Gemini 프롬프트와 응답 형식"""
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

def get_search_prompt(checklist_item: str) -> str:
    """체크리스트 아이템 기반 웹 검색용 프롬프트 생성"""
    current_year = datetime.now().year
    return f"""'{checklist_item}'에 대한 실용적인 정보를 웹에서 검색해서 제공해주세요.

## 요청사항
이 체크리스트 항목을 실행하는 데 도움이 되는 다음 정보들을 찾아주세요:

### 1. 실용적인 팁 (최소 3개 이상)
- "{checklist_item}"를 효과적으로 실행하는 구체적인 방법
- 실제로 도움이 되는 실행 가능한 조언
- 주의사항이나 꿀팁이 있다면 포함
- 각 팁은 명확하고 구체적으로 작성

### 2. 유용한 링크 (최소 3개 이상)
- "{checklist_item}"와 직접 관련된 웹사이트
- 공식 사이트, 가이드, 도구, 플랫폼 등
- 실제 접속 가능한 URL만 제공
- 각 링크의 용도와 특징을 제목에 명시

### 3. 연락처 정보 (있다면)
- 관련 서비스나 기관의 실제 연락처
- 상담이나 문의가 가능한 곳
- 전화번호, 이메일 등 정확한 정보만

### 4. 예상 비용 (해당되는 경우)
- "{checklist_item}" 실행에 필요한 대략적인 비용
- 무료/유료 옵션이 있다면 구분해서 안내

### 5. 장소/위치 정보 (해당되는 경우)
- 오프라인에서 방문해야 할 장소가 있다면
- 지역별 차이가 있다면 주요 지역 정보

## 검색 및 응답 지침
- 한국 시장 기준의 최신 정보 ({current_year}년)
- 실제 존재하고 접속 가능한 링크만 제공
- 구체적이고 실행 가능한 정보 우선
- 광고성 내용보다는 실용적 가치 우선
- 정보가 없는 항목은 빈 배열([])로 제공

검색 대상: "{checklist_item}"에 대한 실행 방법, 도구, 서비스, 가이드"""