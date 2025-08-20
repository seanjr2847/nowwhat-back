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

class StepInfo(BaseModel):
    order: int
    title: str
    description: str
    estimatedTime: Optional[str] = None
    difficulty: Optional[str] = None

class SearchResponse(BaseModel):
    steps: List[StepInfo]  # 구조화된 단계별 가이드
    contacts: List[ContactInfo]
    links: List[LinkInfo]
    price: Optional[str] = None

def get_search_prompt(checklist_item: str, user_country: str = None, user_language: str = None) -> str:
    """체크리스트 아이템 기반 웹 검색용 한국어 프롬프트 생성 (responseSchema 전용)"""
    current_year = datetime.now().year
    
    return f"""당신은 체크리스트 항목을 구체적인 실행 단계로 분해하는 전문가입니다. 사용자가 실제로 행동할 수 있는 명확하고 순차적인 가이드를 제공합니다.

## 주어진 정보
- 체크리스트 항목: "{checklist_item}"
- 사용자 국가: "{user_country or '한국'}"
- 현재 연도: "{current_year}"

## 작업 프로세스

### 1단계: 사고 과정 명시 (JSON 출력 전 필수)
다음 사고 과정을 반드시 보여주세요:

1. **항목 분석**: "{checklist_item}"의 정확한 의미와 완료 조건 파악
2. **복잡도 평가**: 객관적 기준으로 단계 수 결정
   - **준비물 개수**: 필요한 도구/자료/조건의 수량 계산
   - **관련 주체 수**: 혼자 vs 타인과의 협력 필요 여부
   - **소요 시간**: 즉시 완료 vs 며칠 걸리는 작업
   
   **객관적 판단 기준**:
   - **단순** (3단계): 준비물 1개 이하 + 혼자 가능 + 당일 완료
   - **보통** (4단계): 준비물 2-3개 OR 타인 협력 필요 OR 며칠 소요
   - **복합** (5단계): 준비물 4개 이상 OR 다단계 협력 OR 장기간 소요
3. **필수 단계 식별**: 완료를 위해 반드시 거쳐야 하는 핵심 단계들
4. **순서 결정**: 논리적이고 효율적인 실행 순서 배치
5. **국가별 특성**: 한국/해외 상황에 맞는 구체적 방법 반영
6. **완성도 검증**: 모든 단계 수행 시 항목이 완전히 완료되는지 확인

### 2단계: 실행 단계 작성 가이드

**단계 수 결정**:
- **단순 항목** (즉시 실행 가능): 3단계
- **보통 항목** (준비+실행): 4단계  
- **복합 항목** (준비+실행+검증): 5단계

**각 단계 작성 원칙**:
- order: 순서 번호 (1, 2, 3...)
- title: 간단한 단계 제목 (15자 이내)
- description: 구체적인 실행 방법 설명
- estimatedTime: 예상 소요시간 ("10분", "1시간", "지속적" 등)
- difficulty: 난이도 ("쉬움", "보통", "어려움")

### 3단계: 예외 상황 처리
- **항목이 모호한 경우**: 가장 일반적이고 합리적인 해석 적용
- **실행 불가능한 경우**: 대안적 접근 방법 제시
- **법적/윤리적 문제**: 합법적 대안 제안 또는 불가 사유 명시
- **국가별 차이가 있는 경우**: 해당 국가 상황에 맞게 조정

## 입출력 예제

### 예제 1: 단순 항목 (3단계)
**입력**: "카페 예약하기"
**사고 과정**:
- 항목 분석: 특정 카페에 특정 시간 예약하는 작업
- 복잡도 평가: 준비물 1개(전화번호) + 혼자 가능 + 당일 완료 → 단순 (3단계)
- 필수 단계: 카페 선택 → 연락 → 예약 확정

**출력**:
{{
  "steps": [
    {{
      "order": 1,
      "title": "카페 검색하기",
      "description": "원하는 지역과 분위기를 고려하여 예약 가능한 카페를 2-3곳 검색하세요",
      "estimatedTime": "10분",
      "difficulty": "쉬움"
    }},
    {{
      "order": 2,
      "title": "예약 문의하기",
      "description": "선택한 카페에 전화하여 원하는 날짜와 시간에 예약이 가능한지 문의하세요",
      "estimatedTime": "5분",
      "difficulty": "쉬움"
    }},
    {{
      "order": 3,
      "title": "예약 확정하기",
      "description": "예약을 확정하고 예약자 이름과 연락처를 알려드린 후 예약 확인 문자나 이메일을 받으세요",
      "estimatedTime": "5분",
      "difficulty": "쉬움"
    }}
  ],
  "contacts": ["카페 전화번호 확인 필요"],
  "links": [{{"title": "네이버 플레이스", "url": "https://place.naver.com"}}],
  "price": "음료값 별도"
}}

### 예제 2: 보통 항목 (4단계) 
**입력**: "온라인 강의 수강하기"
**사고 과정**:
- 항목 분석: 학습 목적의 온라인 강의 찾기부터 완주까지
- 복잡도 평가: 준비물 2-3개(결제수단, 학습계획) + 혼자 가능 + 며칠 소요 → 보통 (4단계)
- 필수 단계: 강의 선택 → 등록 → 학습 → 완료

**출력**:
{{
  "steps": [
    {{
      "order": 1,
      "title": "학습 주제 정하기",
      "description": "학습하고 싶은 주제를 명확히 정하고 인프런, 유데미, 코세라 등에서 관련 강의를 검색하세요",
      "estimatedTime": "30분",
      "difficulty": "쉬움"
    }},
    {{
      "order": 2,
      "title": "강의 선택하기",
      "description": "강의 커리큘럼과 수강평을 비교하여 자신의 수준에 맞는 강의를 선택하세요",
      "estimatedTime": "1시간",
      "difficulty": "보통"
    }},
    {{
      "order": 3,
      "title": "결제 및 계획 세우기",
      "description": "결제를 완료하고 강의 수강 계획(주 몇 시간, 어떤 요일)을 세워 캘린더에 등록하세요",
      "estimatedTime": "20분",
      "difficulty": "쉬움"
    }},
    {{
      "order": 4,
      "title": "꾸준히 학습하기",
      "description": "매주 계획에 따라 강의를 시청하고 실습을 진행하며 완주까지 꾸준히 학습하세요",
      "estimatedTime": "지속적",
      "difficulty": "어려움"
    }}
  ],
  "contacts": [],
  "links": [
    {{"title": "인프런", "url": "https://www.inflearn.com"}},
    {{"title": "유데미", "url": "https://www.udemy.com"}}
  ],
  "price": "강의별 3만원~15만원"
}}

### 예제 3: 복합 항목 (5단계)
**입력**: "블로그 시작하기"
**사고 과정**:
- 항목 분석: 블로그 개설부터 첫 포스팅까지의 전체 과정
- 복잡도 평가: 준비물 4개 이상(계정, 디자인소재, 콘텐츠, 홍보방법) + 혼자 가능 + 장기간 소요 → 복합 (5단계)
- 필수 단계: 플랫폼 선택 → 개설 → 설정 → 콘텐츠 작성 → 발행

**출력**:
{{
  "steps": [
    {{
      "order": 1,
      "title": "주제와 플랫폼 선택",
      "description": "블로그 주제와 목적을 정하고 네이버, 티스토리, 브런치 중 적합한 플랫폼을 선택하세요",
      "estimatedTime": "1시간",
      "difficulty": "보통"
    }},
    {{
      "order": 2,
      "title": "계정 생성 및 기본 설정",
      "description": "선택한 플랫폼에서 계정을 생성하고 블로그 이름과 주소를 설정하세요",
      "estimatedTime": "30분",
      "difficulty": "쉬움"
    }},
    {{
      "order": 3,
      "title": "블로그 꾸미기",
      "description": "블로그 디자인을 꾸미고 카테고리를 만들며 프로필과 소개글을 작성하세요",
      "estimatedTime": "2시간",
      "difficulty": "보통"
    }},
    {{
      "order": 4,
      "title": "첫 포스팅 작성",
      "description": "첫 번째 포스팅할 주제를 정하고 제목, 본문, 이미지를 포함한 글을 작성하세요",
      "estimatedTime": "1-2시간",
      "difficulty": "보통"
    }},
    {{
      "order": 5,
      "title": "발행 및 홍보",
      "description": "작성한 글을 검토한 후 발행하고 SNS나 지인들에게 블로그 개설 소식을 알리세요",
      "estimatedTime": "30분",
      "difficulty": "쉬움"
    }}
  ],
  "contacts": [],
  "links": [
    {{"title": "네이버 블로그", "url": "https://blog.naver.com"}},
    {{"title": "티스토리", "url": "https://www.tistory.com"}}
  ],
  "price": "무료"
}}

### 예제 4: 업무 관련 (4단계)
**입력**: "프레젠테이션 자료 준비하기"
**사고 과정**:
- 항목 분석: 발표용 자료 기획부터 완성까지
- 복잡도 평가: 준비물 2-3개(자료, 소프트웨어) + 혼자 가능 + 며칠 소요 → 보통 (4단계)
- 필수 단계: 기획 → 자료 수집 → 제작 → 점검

**출력**:
{{
  "steps": [
    {{
      "order": 1,
      "title": "메시지 정리하기",
      "description": "발표 목적과 청중을 파악하여 전달하고자 하는 핵심 메시지 3가지를 정리하세요",
      "estimatedTime": "1시간",
      "difficulty": "보통"
    }},
    {{
      "order": 2,
      "title": "자료 수집 및 구성",
      "description": "각 메시지를 뒷받침할 데이터, 이미지, 사례를 수집하고 슬라이드 구성안을 작성하세요",
      "estimatedTime": "2-3시간",
      "difficulty": "보통"
    }},
    {{
      "order": 3,
      "title": "슬라이드 제작",
      "description": "파워포인트나 구글 슬라이드를 사용하여 제목, 목차, 본문, 결론 순으로 슬라이드를 제작하세요",
      "estimatedTime": "3-4시간",
      "difficulty": "보통"
    }},
    {{
      "order": 4,
      "title": "검토 및 연습",
      "description": "완성된 자료를 처음부터 끝까지 검토하고 발표 연습을 2-3회 진행하세요",
      "estimatedTime": "1-2시간",
      "difficulty": "보통"
    }}
  ],
  "contacts": [],
  "links": [{{"title": "구글 슬라이드", "url": "https://slides.google.com"}}],
  "price": "무료 (소프트웨어 사용)"
}}

### 예제 5: 창작 활동 (5단계)
**입력**: "YouTube 채널 개설하기" 
**사고 과정**:
- 항목 분석: 채널 개설부터 첫 영상 업로드까지의 전 과정
- 복잡도 평가: 준비물 4개 이상(촬영장비, 편집툴, 썸네일, 콘텐츠기획) + 혼자 가능 + 장기간 소요 → 복합 (5단계)
- 필수 단계: 기획 → 개설 → 설정 → 제작 → 업로드

**출력**:
{{
  "steps": [
    {{
      "order": 1,
      "title": "채널 기획하기",
      "description": "채널 주제와 타겟 시청자를 정하고 경쟁 채널 3-5개를 분석하여 차별화 포인트를 찾으세요",
      "estimatedTime": "2-3시간",
      "difficulty": "보통"
    }},
    {{
      "order": 2,
      "title": "채널 생성하기",
      "description": "구글 계정으로 YouTube에 로그인하여 채널을 생성하고 채널명을 설정하세요",
      "estimatedTime": "30분",
      "difficulty": "쉬움"
    }},
    {{
      "order": 3,
      "title": "채널 꾸미기",
      "description": "채널 아트, 프로필 사진을 제작하고 채널 소개를 작성하여 채널을 꾸미세요",
      "estimatedTime": "2-3시간",
      "difficulty": "보통"
    }},
    {{
      "order": 4,
      "title": "첫 영상 제작",
      "description": "첫 번째 영상의 주제를 정하고 스마트폰이나 카메라로 촬영한 후 기본 편집을 진행하세요",
      "estimatedTime": "4-6시간",
      "difficulty": "어려움"
    }},
    {{
      "order": 5,
      "title": "영상 업로드",
      "description": "영상 제목과 설명을 작성하고 썸네일을 만든 후 YouTube에 업로드하여 첫 영상을 발행하세요",
      "estimatedTime": "1시간",
      "difficulty": "쉬움"
    }}
  ],
  "contacts": [],
  "links": [
    {{"title": "YouTube 크리에이터 아카데미", "url": "https://creatoracademy.youtube.com"}},
    {{"title": "Canva 썸네일 제작", "url": "https://www.canva.com"}}
  ],
  "price": "무료 (기본 도구 사용 시)"
}}

## 품질 기준

### 필수 조건
- 사고 과정을 JSON 출력 전에 반드시 명시
- 각 단계는 "N단계:"로 시작하는 완전한 문장
- 순서대로 따라하면 항목이 완전히 완료되도록 구성
- 한국 상황에 맞는 구체적 정보 포함

### 검증 항목
1. 모든 단계를 수행하면 정말로 "{checklist_item}"이 완료되는가?
2. 각 단계가 구체적이고 즉시 실행 가능한가?
3. 단계 간 논리적 순서가 올바른가?
4. 국가별/상황별 특성이 반영되었는가?

## 출력 형식

1. **먼저 사고 과정을 텍스트로 보여주세요**:
   - 항목 분석 결과
   - 복잡도 판단 근거  
   - 필수 단계 식별 과정
   - 완성도 검증 결과

2. **그 다음 JSON 형식으로 최종 결과 출력**:
{{
  "steps": [
    {{
      "order": 1,
      "title": "간단한 제목",
      "description": "구체적인 실행 방법 설명",
      "estimatedTime": "예상 소요시간",
      "difficulty": "쉬움|보통|어려움"
    }},
    {{
      "order": 2,
      "title": "다음 단계 제목",
      "description": "구체적인 실행 방법 설명",
      "estimatedTime": "예상 소요시간",
      "difficulty": "쉬움|보통|어려움"
    }}
  ],
  "contacts": ["필요한 연락처 정보"],
  "links": [{{"title": "참고 사이트명", "url": "실제 URL"}}],
  "price": "예상 비용 정보"
}}

반드시 위 형식을 정확히 따라 JSON만 출력하세요. 추가 텍스트나 마크다운 코드 블록은 사용하지 마세요."""