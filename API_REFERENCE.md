# API 레퍼런스 가이드

## 🌐 Base URL
```
Development: http://localhost:8000/api/v1
Production: https://nowwhat-back.vercel.app/api/v1
```

## 🔐 인증 시스템

### 인증 헤더
```http
Authorization: Bearer <access_token>
```

### 토큰 생명주기
- **Access Token**: 30분
- **Refresh Token**: 7일 (데이터베이스 저장)

---

## 📍 인증 API (`/auth`)

### 🔑 Google OAuth 로그인
```http
POST /auth/google
Content-Type: application/json

{
  "googleToken": "string",
  "deviceInfo": "string (optional)",
  "timezone": "string (optional)"
}
```

**응답**
```json
{
  "accessToken": "string",
  "refreshToken": "string", 
  "user": {
    "id": "string",
    "email": "string",
    "name": "string",
    "profileImage": "string"
  }
}
```

### 👤 현재 사용자 정보
```http
GET /auth/me
Authorization: Bearer <token>
```

**응답**
```json
{
  "user": {
    "id": "string",
    "email": "string", 
    "name": "string",
    "profileImage": "string",
    "createdAt": "datetime",
    "lastLoginAt": "datetime"
  }
}
```

### 🚪 로그아웃
```http
POST /auth/logout
Authorization: Bearer <token>

{
  "refreshToken": "string"
}
```

### 🔄 토큰 갱신
```http
POST /auth/refresh

{
  "refreshToken": "string"
}
```

---

## 👥 사용자 API (`/users`)

### 📋 프로필 조회
```http
GET /users/profile
Authorization: Bearer <token>
```

**응답**
```json
{
  "id": "string",
  "email": "string",
  "name": "string", 
  "profileImage": "string",
  "createdAt": "datetime",
  "lastLoginAt": "datetime"
}
```

### ✏️ 프로필 수정
```http
PUT /users/profile
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "string (optional)",
  "profile_image": "string (optional)"
}
```

### 📊 사용자 통계
```http
GET /users/statistics
Authorization: Bearer <token>
```

**응답**
```json
{
  "success": true,
  "data": {
    "userId": "string",
    "statistics": {
      "checklists": {
        "total": 0,
        "completed": 0,
        "completion_rate": 0.0
      },
      "feedbacks": {
        "total": 0,
        "positive": 0,
        "positive_rate": 0.0,
        "average_rating": 0.0
      },
      "activity": {
        "latest_checklist_date": "datetime",
        "latest_feedback_date": "datetime",
        "has_recent_activity": false
      }
    }
  }
}
```

### 🗑️ 계정 삭제
```http
DELETE /users/account
Authorization: Bearer <token>
```

### 📈 활동 내역
```http
GET /users/activity?limit=10
Authorization: Bearer <token>
```

---

## 🎯 의도 분석 API (`/intents`)

### 🧠 의도 분석 (메인)
```http
POST /intents/analyze
Content-Type: application/json

{
  "goal": "string",
  "userCountry": "string (optional)",
  "userLanguage": "string (optional)",
  "countryOption": true
}
```

**응답**
```json
{
  "sessionId": "string",
  "intents": [
    {
      "title": "string",
      "description": "string",
      "icon": "string"
    }
  ]
}
```

### 🧪 테스트 엔드포인트들
```http
# 간단 테스트
POST /intents/test-simple
{
  "goal": "string"
}

# 요청 본문 테스트
POST /intents/test-body
{
  "goal": "string"
}

# 디버깅용 분석
POST /intents/debug-analyze
{
  "goal": "string",
  "userCountry": "string (optional)",
  "userLanguage": "string (optional)",
  "countryOption": true
}
```

---

## ❓ 질문 생성 API (`/questions`)

### 📝 질문 생성
```http
POST /questions/generate
Content-Type: application/json

{
  "sessionId": "string",
  "intentTitle": "string",
  "goal": "string",
  "countryOption": true
}
```

**응답**
```json
{
  "success": true,
  "data": [
    {
      "id": "string",
      "text": "string",
      "type": "single|multiple",
      "options": ["string"],
      "category": "string"
    }
  ]
}
```

### 🌊 스트리밍 질문 생성
```http
POST /questions/generate/stream
Content-Type: application/json
Accept: text/event-stream

{
  "sessionId": "string",
  "intentTitle": "string", 
  "goal": "string",
  "countryOption": true
}
```

**스트림 응답 형식**
```
data: {"type": "question", "data": {...}}
data: {"type": "complete", "data": {"total": 5}}
data: [DONE]
```

### ✅ 답변 처리 & 체크리스트 생성
```http
POST /questions/answer
Content-Type: application/json

{
  "sessionId": "string",
  "intentTitle": "string",
  "goal": "string", 
  "answers": [
    {
      "questionId": "string",
      "answer": "string",
      "answeredAt": "datetime"
    }
  ],
  "countryOption": true
}
```

**응답**
```json
{
  "success": true,
  "data": {
    "checklist": {
      "id": "string",
      "title": "string",
      "category": "string",
      "description": "string",
      "items": [
        {
          "id": "string",
          "text": "string",
          "order": 0,
          "isCompleted": false,
          "details": {
            "tips": ["string"],
            "contacts": [{"name": "string", "phone": "string"}],
            "links": [{"title": "string", "url": "string"}],
            "price": "string",
            "location": "string"
          }
        }
      ],
      "createdAt": "datetime"
    }
  }
}
```

---

## ✅ 체크리스트 API (`/checklists`)

### 📑 체크리스트 목록
```http
GET /checklists?page=1&limit=20&category=string&status=all&sortBy=createdAt&sortOrder=desc
Authorization: Bearer <token>
```

**응답**
```json
[
  {
    "id": "string",
    "title": "string",
    "category": "string", 
    "description": "string",
    "totalItems": 0,
    "completedItems": 0,
    "progressPercentage": 0.0,
    "isCompleted": false,
    "items": [...],
    "createdAt": "string",
    "updatedAt": "string",
    "completedAt": "string"
  }
]
```

### 📄 체크리스트 상세
```http
GET /checklists/{checklist_id}
Authorization: Bearer <token>
```

### ➕ 체크리스트 생성
```http
POST /checklists
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "string",
  "category": "string",
  "description": "string",
  "items": [
    {
      "title": "string", 
      "description": "string"
    }
  ]
}
```

---

## 💬 피드백 API (`/feedback`)

### 📤 피드백 제출
```http
POST /feedback
Authorization: Bearer <token>
Content-Type: application/json

{
  "checklistId": "string",
  "isPositive": true,
  "rating": 5,
  "comment": "string",
  "categories": ["string"],
  "timestamp": "datetime"
}
```

### 📋 내 피드백 목록
```http
GET /feedback/my?limit=50
Authorization: Bearer <token>
```

### 📊 체크리스트별 피드백
```http
GET /feedback/checklist/{checklist_id}
Authorization: Bearer <token>
```

### ✏️ 피드백 수정
```http
PUT /feedback/{feedback_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "isPositive": true,
  "rating": 4,
  "comment": "string",
  "categories": ["string"]
}
```

### 🗑️ 피드백 삭제
```http
DELETE /feedback/{feedback_id}
Authorization: Bearer <token>
```

### 📈 피드백 통계
```http
GET /feedback/statistics
Authorization: Bearer <token>
```

**응답**
```json
{
  "success": true,
  "data": {
    "total_count": 0,
    "positive_count": 0,
    "negative_count": 0,
    "positive_rate": 0.0,
    "average_rating": 0.0,
    "rating_distribution": {
      "1": 0,
      "2": 0,
      "3": 0,
      "4": 0,
      "5": 0
    },
    "has_comments": 0
  }
}
```

---

## 🚨 오류 응답 형식

### 표준 오류 응답
```json
{
  "success": false,
  "error": "string",
  "message": "string", 
  "code": "string (optional)"
}
```

### 일반적인 HTTP 상태 코드
- **200**: 성공
- **201**: 생성됨
- **400**: 잘못된 요청
- **401**: 인증 필요
- **403**: 권한 없음
- **404**: 찾을 수 없음  
- **422**: 검증 오류
- **500**: 서버 오류

---

## 🔧 개발자 도구

### API 문서 접속
- **Swagger UI**: `/docs`
- **ReDoc**: `/redoc`

### 헬스 체크
```http
GET /health
```

**응답**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

### 루트 정보
```http
GET /
```

**응답**  
```json
{
  "service": "NowWhat API Server",
  "version": "1.0.0",
  "description": "인텐트 분석 및 체크리스트 생성을 위한 API 서버",
  "docs": "/docs",
  "health": "/health"
}
```

---

## 📝 요청/응답 예제

### 완전한 워크플로 예제

1. **의도 분석**
```http
POST /intents/analyze
{
  "goal": "운동을 시작하고 싶어",
  "countryOption": true
}
```

2. **질문 생성**
```http
POST /questions/generate
{
  "sessionId": "session_123",
  "intentTitle": "운동 시작하기",
  "goal": "운동을 시작하고 싶어",
  "countryOption": true
}
```

3. **답변 제출 & 체크리스트 생성**
```http
POST /questions/answer
{
  "sessionId": "session_123",
  "intentTitle": "운동 시작하기",
  "goal": "운동을 시작하고 싶어",
  "answers": [
    {
      "questionId": "q1",
      "answer": "헬스장",
      "answeredAt": "2024-01-20T10:00:00Z"
    }
  ],
  "countryOption": true
}
```

4. **생성된 체크리스트 확인**
```http
GET /checklists/{generated_checklist_id}
Authorization: Bearer <token>
```

---

*이 API 레퍼런스는 실제 구현을 기반으로 작성되었습니다. 최신 정보는 `/docs` 엔드포인트에서 확인하세요.*