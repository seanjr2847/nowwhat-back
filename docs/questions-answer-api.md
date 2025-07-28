# POST /questions/answer API Documentation

## Overview

The POST `/api/v1/questions/answer` endpoint processes user answers and generates AI-powered personalized checklists using Google Gemini AI and Perplexity API for real-time information enhancement.

## Authentication

- **Required**: JWT Bearer token
- **Scope**: Authenticated users only
- **Header**: `Authorization: Bearer <jwt_token>`

## Request Schema

### QuestionAnswersRequest

```json
{
  "goal": "string (required, 1-500 chars)",
  "selectedIntent": {
    "index": "integer (required, >= 0)",
    "title": "string (required, min 1 char)"
  },
  "answers": [
    {
      "questionIndex": "integer (required, >= 0)",
      "questionText": "string (required, min 1 char)",
      "answer": "string | array[string] (required)"
    }
  ]
}
```

### Example Request

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
    },
    {
      "questionIndex": 2,
      "questionText": "선호하는 활동은?",
      "answer": ["sightseeing", "food", "shopping"]
    }
  ]
}
```

## Response Schema

### QuestionAnswersResponse

```json
{
  "checklistId": "string (format: cl_{timestamp}_{random})",
  "redirectUrl": "string (format: /result/{checklistId})"
}
```

### Example Response

```json
{
  "checklistId": "cl_1705737600_abc123",
  "redirectUrl": "/result/cl_1705737600_abc123"
}
```

## Status Codes

| Code | Description | Response Body |
|------|-------------|---------------|
| 200 | 체크리스트 생성 성공 | QuestionAnswersResponse |
| 400 | 필수 답변 누락 또는 잘못된 형식 | ErrorResponse |
| 401 | 인증 필요 (JWT 토큰 없음/만료) | ErrorResponse |
| 500 | 서버 내부 오류 | ErrorResponse |

### Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "error_code",
    "message": "사용자 친화적인 오류 메시지"
  }
}
```

## Business Logic Flow

### 1. Request Validation
- Goal 필드 검증 (1-500자)
- SelectedIntent 구조 검증
- Answers 배열 검증 (최소 1개)
- 각 답변의 questionText, answer 필드 검증

### 2. Answer Storage
- 사용자 답변을 `answers` 테이블에 저장
- Array 타입 답변은 쉼표로 구분하여 문자열로 저장
- 임시 question_id 생성 (향후 questions 테이블 연동 필요)

### 3. AI Checklist Generation
- Gemini AI에 사용자 goal, intent, answers 전달
- 8-15개 체크리스트 항목 생성
- 시간순 정렬 및 실행 가능한 액션 아이템 포커스
- 실패 시 의도별 기본 템플릿 사용

### 4. Parallel Search Enhancement
- Perplexity API를 통한 10개 병렬 검색 실행
- 검색 쿼리는 goal + intent + answer context 기반 자동 생성
- 15초 타임아웃, 성공한 결과만 활용
- 검색 결과를 체크리스트에 실용적인 팁으로 통합

### 5. Checklist Finalization
- AI 생성 + 검색 보강 결과 병합
- 중복 제거 및 품질 검증
- 8-15개 범위로 항목 수 조정
- 체크리스트 및 체크리스트 아이템 DB 저장

### 6. Response Generation
- 고유 체크리스트 ID 생성 (cl_{timestamp}_{random})
- 결과 페이지 리다이렉트 URL 생성

## Performance Characteristics

### Response Time Targets
- **Total Processing**: < 30 seconds (including parallel searches)
- **Database Operations**: < 2 seconds
- **AI Generation**: < 10 seconds with fallback
- **Search Integration**: < 15 seconds for 10 concurrent queries

### Concurrent Processing
- 10 parallel Perplexity API calls using asyncio.gather()
- Gemini AI generation runs concurrently with search queries
- Database operations use connection pooling for efficiency

### Error Resilience
- Graceful degradation when external APIs fail
- Cached template fallbacks for AI generation failures
- Partial success handling for search operations
- Comprehensive logging for debugging and monitoring

## External Dependencies

### Google Gemini AI
- **Purpose**: Primary checklist generation
- **Model**: gemini-1.5-flash
- **Fallback**: Intent-based cached templates
- **Rate Limits**: Managed by existing retry logic

### Perplexity API
- **Purpose**: Real-time information search and enhancement
- **Model**: llama-3.1-sonar-small-128k-online
- **Concurrency**: Up to 10 parallel requests
- **Timeout**: 15 seconds per request
- **Fallback**: Continue without search enhancement

## Configuration

### Environment Variables

```bash
# Required for AI functionality
GEMINI_API_KEY=your_gemini_api_key

# Required for search enhancement
PERPLEXITY_API_KEY=your_perplexity_api_key

# Optional performance tuning
MAX_CONCURRENT_SEARCHES=10
SEARCH_TIMEOUT_SECONDS=15
```

### Database Requirements

The endpoint requires the following tables:
- `users` - User authentication
- `answers` - User answer storage
- `checklists` - Generated checklist metadata
- `checklist_items` - Individual checklist items

## Security Considerations

### Input Validation
- All user inputs are validated using Pydantic schemas
- String length limits prevent excessive resource usage
- Answer arrays are properly sanitized

### Authentication & Authorization
- JWT token validation ensures user authentication
- User context is maintained throughout the process
- Database operations are tied to authenticated user

### Data Protection
- User answers may contain PII - handle securely
- API keys are stored in environment variables
- Error messages don't expose internal system details

## Testing Strategy

### Unit Tests
```python
# Test schema validation
def test_question_answers_request_validation()
def test_selected_intent_schema_validation()

# Test service components
async def test_perplexity_parallel_search()
async def test_checklist_orchestrator_workflow()

# Test database operations
def test_save_user_answers()
def test_save_final_checklist()
```

### Integration Tests
```python
# Test complete workflow
async def test_submit_answers_success_flow()
async def test_submit_answers_with_ai_failure()
async def test_concurrent_answer_submissions()
```

### Performance Tests
```python
# Test response time requirements
async def test_endpoint_response_under_30_seconds()
async def test_concurrent_user_handling()
async def test_external_api_timeout_handling()
```

## Monitoring & Observability

### Key Metrics
- Response time percentiles (50th, 95th, 99th)
- External API success rates (Gemini, Perplexity)
- Checklist generation success rate
- Database operation performance
- Error rates by category

### Logging
- Request/response logging with user context
- External API call success/failure
- Performance timing for each workflow stage
- Error details for debugging (without PII)

## Rate Limiting

Currently not implemented. Recommended implementation:
- 5 requests per minute per user
- 50 requests per hour per user
- Use Redis for distributed rate limiting
- Return 429 status when limits exceeded

## Known Limitations

1. **Session Validation**: Currently bypassed, should validate sessionId in future
2. **Question Integration**: Temporary question_id generation, needs questions table integration
3. **Rate Limiting**: Not implemented, recommended for production
4. **Caching**: No result caching, could improve performance for similar requests
5. **Metrics**: Basic logging only, needs comprehensive monitoring

## Migration Notes

### From Existing System
- Maintains backward compatibility with existing question generation
- Uses established authentication and database patterns
- Follows existing error response formats

### Future Improvements
- Add Redis caching for improved performance
- Implement proper session validation
- Add comprehensive monitoring dashboard
- Optimize database queries with proper indexing
- Add A/B testing for different AI prompt strategies

## Example Usage

### cURL Example
```bash
curl -X POST "http://localhost:8000/api/v1/questions/answer" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_jwt_token" \
  -d '{
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
  }'
```

### JavaScript Example
```javascript
const response = await fetch('/api/v1/questions/answer', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${accessToken}`
  },
  body: JSON.stringify({
    goal: "일본여행 가고싶어",
    selectedIntent: {
      index: 0,
      title: "여행 계획"
    },
    answers: [
      {
        questionIndex: 0,
        questionText: "여행 기간은 얼마나 되나요?",
        answer: "3days"
      },
      {
        questionIndex: 1,
        questionText: "예산은 얼마나 되나요?",
        answer: "1million"
      }
    ]
  })
});

const result = await response.json();
if (response.ok) {
  // Redirect to result page
  window.location.href = result.redirectUrl;
} else {
  // Handle error
  console.error('Error:', result.error.message);
}
```