"""질문 생성을 위한 Gemini 프롬프트"""

def get_questions_generation_prompt(goal: str, intent_title: str, user_country: str, country_context: str) -> str:
    """질문 생성용 프롬프트 생성"""
    return f"""당신은 개인 맞춤형 체크리스트 생성을 위한 질문 설계 전문가입니다.

사용자 정보:
- 목표: "{goal}"
- 선택한 의도: "{intent_title}"
- 거주 국가: {user_country}
- 국가별 맞춤화: {country_context}

이 사용자가 목표를 달성하기 위해 필요한 핵심 정보를 수집하는 3-5개의 질문을 생성하세요.

질문 생성 규칙:
1. 첫 번째 질문: 시기/기간 파악 (언제)
2. 두 번째 질문: 규모/인원 파악 (누구와)
3. 세 번째 질문: 선호도/관심사 (무엇을)
4. 네 번째 질문: 예산/자원 (얼마나)
5. 다섯 번째 질문: 특별 요구사항 (기타)

질문 유형:
- "multiple": 명확한 선택지가 있을 때 (4개 옵션 고정)
- "text": 개인별 차이가 큰 정보일 때

응답 형식 (JSON):
[
  {{
    "id": "q_001",
    "text": "구체적인 질문 내용",
    "type": "multiple",
    "options": [
      {{"id": "opt_1", "text": "선택지1", "value": "value1"}},
      {{"id": "opt_2", "text": "선택지2", "value": "value2"}},
      {{"id": "opt_3", "text": "선택지3", "value": "value3"}},
      {{"id": "opt_4", "text": "선택지4", "value": "value4"}}
    ],
    "required": true
  }}
]

중요: 정확히 3-5개만 생성하고, 유효한 JSON 형식으로 응답하세요."""