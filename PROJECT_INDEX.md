# NowWhat API 프로젝트 인덱스

## 📋 프로젝트 개요
- **이름**: NowWhat API Server
- **버전**: 1.0.0
- **설명**: Google Gemini AI를 활용한 의도 분석 및 체크리스트 생성 서비스
- **기술 스택**: FastAPI, PostgreSQL(Neon), Google OAuth, Gemini AI, SQLAlchemy

## 🏗️ 프로젝트 구조

### 핵심 디렉토리
```
app/
├── api/v1/           # API 엔드포인트 (REST API)
├── core/             # 핵심 시스템 (인증, DB, 설정)
├── services/         # 비즈니스 로직 (AI, 외부 API)
├── models/           # 데이터베이스 모델
├── schemas/          # Pydantic 스키마
├── crud/             # 데이터 액세스 레이어
├── prompts/          # AI 프롬프트 시스템
└── utils/            # 유틸리티 함수
```

## 🌐 API 엔드포인트 맵

### 인증 API (`/api/v1/auth`)
| 메서드 | 엔드포인트 | 설명 | 인증 |
|--------|------------|------|------|
| POST | `/google` | 구글 OAuth 로그인 | ❌ |
| GET | `/me` | 현재 사용자 정보 | ✅ |
| POST | `/logout` | 로그아웃 | ✅ |
| POST | `/refresh` | 토큰 갱신 | ❌ |

### 사용자 API (`/api/v1/users`)
| 메서드 | 엔드포인트 | 설명 | 인증 |
|--------|------------|------|------|
| GET | `/profile` | 프로필 조회 | ✅ |
| PUT | `/profile` | 프로필 수정 | ✅ |
| GET | `/statistics` | 사용자 통계 | ✅ |
| DELETE | `/account` | 계정 삭제 | ✅ |
| GET | `/activity` | 활동 내역 | ✅ |

### 의도 분석 API (`/api/v1/intents`)
| 메서드 | 엔드포인트 | 설명 | 인증 |
|--------|------------|------|------|
| POST | `/analyze` | 의도 분석 (메인) | ❌ |
| POST | `/test-simple` | 간단 테스트 | ❌ |
| POST | `/test-body` | 요청 본문 테스트 | ❌ |
| POST | `/debug-analyze` | 디버깅용 분석 | ❌ |
| POST | `/test-dependencies` | 의존성 테스트 | ❌ |

### 질문 생성 API (`/api/v1/questions`)
| 메서드 | 엔드포인트 | 설명 | 인증 |
|--------|------------|------|------|
| POST | `/generate` | 질문 생성 | ❌ |
| POST | `/answer` | 답변 처리 & 체크리스트 생성 | ❌ |
| POST | `/generate/stream` | 스트리밍 질문 생성 | ❌ |
| GET | `/generate/{intent_id}` | 의도별 질문 생성 | ❌ |

### 체크리스트 API (`/api/v1/checklists`)
| 메서드 | 엔드포인트 | 설명 | 인증 |
|--------|------------|------|------|
| GET | `/` | 체크리스트 목록 | ✅ |
| GET | `/{checklist_id}` | 체크리스트 상세 | ✅ |
| POST | `/` | 체크리스트 생성 | ✅ |

### 피드백 API (`/api/v1/feedback`)
| 메서드 | 엔드포인트 | 설명 | 인증 |
|--------|------------|------|------|
| POST | `/` | 피드백 제출 | ✅ |
| GET | `/my` | 내 피드백 목록 | ✅ |
| GET | `/checklist/{checklist_id}` | 체크리스트 피드백 | ✅ |
| PUT | `/{feedback_id}` | 피드백 수정 | ✅ |
| DELETE | `/{feedback_id}` | 피드백 삭제 | ✅ |
| GET | `/statistics` | 피드백 통계 | ✅ |

## 🗄️ 데이터베이스 스키마

### 주요 모델
- **User**: 사용자 정보 (Google OAuth)
- **IntentSession**: 의도 분석 세션
- **Intent**: 분석된 의도
- **Question**: 생성된 질문
- **Checklist**: 체크리스트
- **ChecklistItem**: 체크리스트 아이템
- **Feedback**: 사용자 피드백

### 관계도
```
User 1:N Checklist 1:N ChecklistItem
User 1:N Feedback N:1 Checklist
IntentSession 1:N Intent
Intent 1:N Question
```

## 🤖 AI 시스템 아키텍처

### Gemini 통합 서비스
- **모델**: `gemini-2.5-flash`
- **주요 기능**: 의도 분석, 질문 생성, 체크리스트 생성, 웹 검색 통합

### 프롬프트 시스템
```
prompts/
├── ko/               # 한국어 프롬프트
│   ├── intent_analysis.py
│   ├── questions_generation.py
│   └── checklist_prompts.py
├── en/               # 영어 프롬프트
│   ├── intent_analysis.py
│   ├── questions_generation.py
│   └── checklist_prompts.py
├── enhanced_prompts.py  # 고급 프롬프트
├── search_prompts.py    # 검색 프롬프트
└── prompt_selector.py   # 언어별 선택기
```

## 🔧 핵심 서비스

### 1. GeminiService (`app/services/gemini_service.py`)
- Gemini AI API 통합
- 스트리밍 응답 지원
- 구조화된 출력 (Structured Output)
- 웹 검색 통합 (Google Search Retrieval)
- 토큰 최적화

### 2. ChecklistOrchestrator (`app/services/checklist_orchestrator.py`)
- 질문-답변 기반 체크리스트 생성
- 병렬 처리 및 비동기 워크플로
- 실시간 웹 검색을 통한 정보 보강
- 포괄적 오류 처리

### 3. GoogleAuth (`app/services/google_auth.py`)
- Google OAuth 2.0 통합
- JWT 토큰 관리
- 사용자 프로필 검증

## 📚 문서 및 가이드

### 기술 문서
- [`CLAUDE.md`](./CLAUDE.md) - Claude Code 작업 가이드
- [`README.md`](./README.md) - 프로젝트 설정 및 사용법
- [`README_DEPLOYMENT.md`](./README_DEPLOYMENT.md) - 배포 가이드

### 상세 문서
- [`docs/testing-guide.md`](./docs/testing-guide.md) - 테스트 프레임워크
- [`docs/questions-answer-api.md`](./docs/questions-answer-api.md) - Q&A API 명세
- [`docs/database-migration-guide.md`](./docs/database-migration-guide.md) - DB 마이그레이션

## 🚀 배포 및 운영

### 환경 변수
```env
# 필수 환경 변수
GEMINI_API_KEY=your_gemini_key
DATABASE_URL=postgresql://...
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
SECRET_KEY=your_jwt_secret

# 선택적 환경 변수
PORT=8000
ENV=production
LOG_LEVEL=INFO
MAX_CONCURRENT_SEARCHES=15
```

### 배포 플랫폼
- **Backend**: Vercel (Serverless)
- **Database**: Neon PostgreSQL
- **Frontend**: Vercel (별도 저장소)

### 명령어 참조
```bash
# 개발 서버 실행
python run.py

# 마이그레이션
alembic upgrade head

# 테스트 실행
pytest

# 배포
vercel --prod
```

## 🔒 보안 및 인증

### 인증 시스템
- **OAuth 2.0**: Google 소셜 로그인
- **JWT**: Access Token (30분) + Refresh Token (저장소 기반)
- **CORS**: 허용된 도메인만 접근 가능

### 보안 기능
- 요청 검증 (Pydantic)
- SQL 인젝션 방지 (SQLAlchemy ORM)
- 레이트 리미팅
- 환경 변수 기반 설정

## 📊 모니터링 및 로깅

### 로깅 시스템
- 구조화된 로깅
- 요청/응답 추적
- 오류 상세 기록
- 성능 메트릭

### 주요 메트릭
- API 응답 시간
- Gemini API 사용량
- 사용자 활동 패턴
- 오류율 및 성공률

## 🧪 테스트 및 품질 보증

### 테스트 구조
```
tests/
├── unit/             # 단위 테스트
├── integration/      # 통합 테스트
├── api/              # API 테스트
└── fixtures/         # 테스트 데이터
```

### 품질 도구
- **pytest**: 테스트 프레임워크
- **pytest-asyncio**: 비동기 테스트
- **httpx**: HTTP 클라이언트 테스트
- **pytest-cov**: 코드 커버리지

## 🔄 개발 워크플로

### Git 브랜치 전략
- `main`: 프로덕션 브랜치
- `develop`: 개발 브랜치
- `feature/*`: 기능 개발 브랜치

### 코드 스타일
- **FastAPI**: 비동기 웹 프레임워크
- **Pydantic**: 데이터 검증 및 직렬화
- **SQLAlchemy**: ORM 및 데이터베이스 추상화
- **타입 힌트**: Python 3.8+ 타입 어노테이션

---

*이 문서는 프로젝트 전체 구조를 파악하기 위한 인덱스입니다. 각 섹션의 상세 내용은 해당 문서나 소스 코드를 참조하세요.*