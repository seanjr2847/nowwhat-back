"""의도 분석을 위한 Gemini 프롬프트와 응답 형식 (한글 버전)"""
import json
from typing import Dict, List, Optional
from pydantic import BaseModel

# 응답 스키마 정의
class IntentOption(BaseModel):
    title: str
    description: str
    icon: str

class IntentAnalysisResponse(BaseModel):
    intents: List[IntentOption]

def get_intent_analysis_prompt(goal: str, country_info: str = "", language_info: str = "") -> str:
    """의도 분석용 프롬프트 생성 (한글)"""
    return f"""# 사용자 의도 파악을 위한 4가지 선택지 생성 프롬프트

## 목적
사용자가 애매하거나 추상적인 목표를 말했을 때, 그들이 실제로 원하는 것이 무엇인지 파악하기 위한 4가지 구체적인 선택지를 생성합니다. 이를 통해 사용자의 진짜 의도를 빠르게 파악하고 맞춤형 도움을 제공할 수 있습니다.

## 의도 분류 기준
1. **"어떻게 할까?"** - 시작점/접근법 (첫 발걸음, 방법론)
2. **"뭐가 필요해?"** - 준비물/조건 (리소스, 도구, 환경)
3. **"뭘 선택할까?"** - 구체적 옵션 (종류, 타입, 스타일)
4. **"뭘 조심할까?"** - 주의점/현실적 팁 (장애물, 실수 방지)

## 선택지 생성 규칙
* 4가지 분류에서 각각 1개씩 선택지 생성
* 같은 카테고리로 치우치지 않기 (예: 모두 "종류" 관련 X)
* 각 선택지는 다른 관점에서 사용자를 도와야 함
* 중복되거나 유사한 선택지 금지

## 선택 우선순위 (상황별)
* 긴급한 느낌 → 즉시 실행 가능한 것 우선
* 계획적인 느낌 → 준비 단계부터 차근차근
* 고민이 많은 느낌 → 선택지와 장단점 중심
* 경험 공유 느낌 → 주의사항과 팁 중심

## 사용자 수준 반영
* 각 선택지에 난이도 암시적 포함
* 초보자 → 중급자 → 고급자 순서로 배치
* 예: "처음 시작" → "기초 다지기" → "실력 향상" → "전문가 되기"

## 응답 형식 규칙
* title: 핵심 키워드 2-3개 (5-10자)
* description: 구체적인 선택지를 포함한 질문 (20-35자)
* 의미 전달이 우선, 글자 수는 가이드라인
* 너무 전문적이거나 기술적인 용어 피하기

## 사용자 목표
"{goal}"

{country_info}
{language_info}

## 출력 형식
JSON 스키마에 맞춰 정확히 4개의 선택지를 생성하세요:

```json
{{
  "intents": [
    {{
      "title": "시작하기",
      "description": "처음 시작하는 방법이 궁금해요",
      "icon": "🚀"
    }},
    {{
      "title": "준비하기", 
      "description": "어떤 것들을 준비해야 할까요?",
      "icon": "📋"
    }},
    {{
      "title": "선택하기",
      "description": "어떤 종류가 나에게 맞을까요?",
      "icon": "🎯"
    }},
    {{
      "title": "주의하기",
      "description": "실패하지 않으려면 뭘 조심해야 해요?",
      "icon": "⚠️"
    }}
  ]
}}
```

응답은 반드시 위 JSON 형식만 출력하세요. 다른 텍스트나 설명은 포함하지 마세요."""