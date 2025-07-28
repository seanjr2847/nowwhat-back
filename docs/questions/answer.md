### POST /questions/answer

모든 답변을 한번에 제출하여 체크리스트 생성

**Request**

| key | 설명 | value 타입 | 옵션 | Nullable | 예시 |
| --- | --- | --- | --- | --- | --- |
| **Body** |  |  |  |  |  |
| goal | 초기 입력한 목표 | string | 필수 | No | "일본여행 가고싶어" |
| selectedIntent | 선택한 의도 | object | 필수 | No | - |
| selectedIntent.index | 의도 인덱스 | number | 필수 | No | 0 |
| selectedIntent.title | 의도 제목 | string | 필수 | No | "여행 계획" |
| answers | 질문별 답변 목록 | array | 필수 | No | - |
| answers[].questionIndex | 질문 인덱스 | number | 필수 | No | 0 |
| answers[].questionText | 질문 내용 | string | 필수 | No | "여행 기간은 얼마나 되나요?" |
| answers[].answer | 답변 | string | array[string] | 필수 | No | "3days" |

**Response**

| key | 설명 | value 타입 | 옵션 | Nullable | 예시 |
| --- | --- | --- | --- | --- | --- |
| checklistId | 생성된 체크리스트 ID | string | - | No | "cl_abc123" |
| redirectUrl | 결과 페이지 URL | string | - | No | "/result/cl_abc123" |

**Example Request**

```json
{
  "goal": "일본여행 가고싶어",
  "selectedIntent": {
    "index": 0,
    "title": "여행 계획"
  },
  "answers": [
    {
      "questionIndex": 0,
      "questionText": "여행 기간은 얼마나 되나요?",
      "answer": "3days"
    },
    {
      "questionIndex": 1,
      "questionText": "예산은 얼마나 되나요?",
      "answer": "1million"
    }
  ]
}

```

**Example Response**

```json
{
  "checklistId": "cl_abc123",
  "redirectUrl": "/result/cl_abc123"
}

```

**Status**

| status | response content |
| --- | --- |
| 200 | 체크리스트 생성 성공 |
| 400 | 필수 답변 누락 |
| 401 | 인증 필요 |
| 429 | 요청 한도 초과 |

```mermaid
flowchart TD
    A["{USER_QUERY}"] --> B["오케스트레이터<br/>의도: {INTENT_TYPE}<br/>답변: {USER_ANSWERS}"]

    B --> AA["사용자 답변 제출<br/>sessionId + answers"]

    AA --> BB{"입력 검증<br/>필수 답변 확인"}

    BB -->|검증 실패| CC["400 Bad Request<br/>누락된 필수 답변 안내"]

    BB -->|검증 성공| DD["📍 DB 조회<br/>세션 정보 확인"]

    DD --> EE{"세션 유효?"}
    EE -->|무효| FF["401 Unauthorized<br/>세션 만료 또는 없음"]

    EE -->|유효| GG["📍 DB 저장<br/>사용자 답변 저장"]

    GG --> HH["광고 표시 시작<br/>{AD_DURATION}초 카운트다운"]

    HH --> C1

    subgraph "체크리스트 생성 에이전트 (Gemini)"
        C1["프롬프트:<br/>사용자가 '{USER_CONTEXT}'을 계획한다.<br/>체계적인 준비를 위한 카테고리별<br/>체크리스트 구조를 생성하라."]
        C1 --> C2["카테고리 생성:<br/>1. {CATEGORY_1}<br/>2. {CATEGORY_2}<br/>3. {CATEGORY_3}<br/>4. {CATEGORY_4}<br/>5. {CATEGORY_5}"]
        C2 --> C3["{CHECKLIST_COUNT}개 핵심 체크 항목 생성:<br/>1. {ITEM_1}<br/>2. {ITEM_2}<br/>3. {ITEM_3}<br/>...<br/>N. {ITEM_N}"]
    end

    C3 --> JJ{"Gemini 성공?"}
    JJ -->|실패| KK["캐시된 템플릿 사용<br/>의도별 기본 체크리스트"]

    JJ -->|성공| LL["체크리스트 {MIN_ITEMS}-{MAX_ITEMS}개<br/>생성 완료"]

    KK --> MM
    LL --> MM["검색 쿼리 생성<br/>서버에서 자동 조합"]

    MM --> P1

    subgraph "병렬 검색 처리 (Perplexity API)"
        P1["Perplexity API<br/>병렬 호출 (Promise.all)"]
        P1 -->|병렬 처리| S1["🔍 {SEARCH_QUERY_1}<br/>{SEARCH_FILTER_1}<br/>{SEARCH_DATE_RANGE_1}"]
        P1 -->|병렬 처리| S2["🔍 {SEARCH_QUERY_2}<br/>{SEARCH_FILTER_2}<br/>{SEARCH_DATE_RANGE_2}"]
        P1 -->|병렬 처리| S3["🔍 {SEARCH_QUERY_3}<br/>{SEARCH_FILTER_3}<br/>{SEARCH_DATE_RANGE_3}"]
        P1 -->|병렬 처리| S4["🔍 {SEARCH_QUERY_4}<br/>{SEARCH_FILTER_4}<br/>{SEARCH_DATE_RANGE_4}"]
        P1 -->|병렬 처리| S5["🔍 {SEARCH_QUERY_5}<br/>{SEARCH_FILTER_5}<br/>{SEARCH_DATE_RANGE_5}"]
        P1 -->|병렬 처리| S6["🔍 {SEARCH_QUERY_6}<br/>{SEARCH_FILTER_6}<br/>{SEARCH_DATE_RANGE_6}"]
        P1 -->|병렬 처리| S7["🔍 {SEARCH_QUERY_7}<br/>{SEARCH_FILTER_7}<br/>{SEARCH_DATE_RANGE_7}"]
        P1 -->|병렬 처리| S8["🔍 {SEARCH_QUERY_8}<br/>{SEARCH_FILTER_8}<br/>{SEARCH_DATE_RANGE_8}"]
        P1 -->|병렬 처리| S9["🔍 {SEARCH_QUERY_9}<br/>{SEARCH_FILTER_9}<br/>{SEARCH_DATE_RANGE_9}"]
        P1 -->|병렬 처리| S10["🔍 {SEARCH_QUERY_10}<br/>{SEARCH_FILTER_10}<br/>{SEARCH_DATE_RANGE_10}"]

        S1 --> R1["✅ {RESULT_1_TITLE}<br/>{RESULT_1_VALUE}"]
        S2 --> R2["✅ {RESULT_2_TITLE}<br/>{RESULT_2_VALUE}"]
        S3 --> R3["✅ {RESULT_3_TITLE}<br/>{RESULT_3_VALUE}"]
        S4 --> R4["✅ {RESULT_4_TITLE}<br/>{RESULT_4_VALUE}"]
        S5 --> R5["✅ {RESULT_5_TITLE}<br/>{RESULT_5_VALUE}"]
        S6 --> R6["✅ {RESULT_6_TITLE}<br/>{RESULT_6_VALUE}"]
        S7 --> R7["✅ {RESULT_7_TITLE}<br/>{RESULT_7_VALUE}"]
        S8 --> R8["✅ {RESULT_8_TITLE}<br/>{RESULT_8_VALUE}"]
        S9 --> R9["✅ {RESULT_9_TITLE}<br/>{RESULT_9_VALUE}"]
        S10 --> R10["✅ {RESULT_10_TITLE}<br/>{RESULT_10_VALUE}"]
    end

    R1 --> PP["정보 병합<br/>Gemini + Perplexity"]
    R2 --> PP
    R3 --> PP
    R4 --> PP
    R5 --> PP
    R6 --> PP
    R7 --> PP
    R8 --> PP
    R9 --> PP
    R10 --> PP

    subgraph "정보 통합 및 최종화"
        PP --> G1["{CHECKLIST_COUNT}개 검색 결과 수합"]
        G1 --> G2["정보 검증 및 보강:<br/>- {VALIDATION_CRITERIA_1}<br/>- {VALIDATION_CRITERIA_2}<br/>- {VALIDATION_CRITERIA_3}"]
        G2 --> G3["시간순 재정렬:<br/>{TIMELINE_ITEM_1}: {TIMELINE_DESC_1}<br/>{TIMELINE_ITEM_2}: {TIMELINE_DESC_2}<br/>{TIMELINE_ITEM_3}: {TIMELINE_DESC_3}<br/>{TIMELINE_ITEM_4}: {TIMELINE_DESC_4}<br/>{TIMELINE_ITEM_5}: {TIMELINE_DESC_5}"]
        G3 --> G4["최종 체크리스트 포맷팅:<br/>□ {FORMAT_RULE_1}<br/>□ {FORMAT_RULE_2}<br/>□ {FORMAT_RULE_3}<br/>□ {FORMAT_RULE_4}"]
    end

    G4 --> QQ["📍 DB 저장<br/>체크리스트 전체 저장"]

    QQ --> RR["체크리스트 ID 생성<br/>cl_{timestamp}_{random}"]

    RR --> SS["200 OK<br/>redirectUrl 반환"]

    SS --> F["✅ /result/{CHECKLIST_ID}<br/>맞춤 체크리스트 완성<br/>총 {TOTAL_ITEMS}개 핵심 항목<br/>병렬 처리 시간: {PROCESSING_TIME}초"]

    style A fill:#FFE4E1
    style F fill:#90EE90
    style P1 fill:#87CEEB
    style CC fill:#FFB6C1
    style FF fill:#FFB6C1
    style KK fill:#FFA500
    style S1 fill:#FFF8DC
    style S2 fill:#FFF8DC
    style S3 fill:#FFF8DC
    style S4 fill:#FFF8DC
    style S5 fill:#FFF8DC
    style S6 fill:#FFF8DC
    style S7 fill:#FFF8DC
    style S8 fill:#FFF8DC
    style S9 fill:#FFF8DC
    style S10 fill:#FFF8DC

```