# NowWhat API Server 🚀

사용자 목표를 분석하고 실행 가능한 체크리스트를 생성하는 AI 기반 FastAPI 백엔드 서버입니다.

## ✨ 주요 기능

- 🤖 **Google Gemini AI** 기반 인텐트 분석 및 체크리스트 생성
- 🔐 **구글 OAuth 2.0** 인증 시스템
- 🗄️ **PostgreSQL (Neon DB)** 클라우드 데이터베이스
- 🛡️ **JWT 토큰** 기반 보안
- 🌐 **실시간 웹 검색** 기반 정보 보강
- 📊 **스트리밍 응답** (Server-Sent Events)
- 🌏 **다국어 지원** (한국어/영어 프롬프트)
- 📍 **지역별 맞춤 정보** 제공
- ✅ **체크리스트 관리** 및 진행률 추적
- 📝 **사용자 피드백 시스템**
- 🌐 **Vercel 서버리스 배포** 최적화

## 🏗️ 시스템 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   API Server    │    │   Gemini AI     │
│   (React)       │◄──►│   (FastAPI)     │◄──►│   (Google)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Database      │    │   OAuth         │
                       │   (PostgreSQL)  │    │   (Google)      │
                       └─────────────────┘    └─────────────────┘
```

### 핵심 워크플로우

1. **인텐트 분석**: 사용자 목표를 AI가 분석하여 4가지 실행 가능한 의도 제안
2. **맞춤형 질문**: 선택된 의도에 따라 개인화된 질문 생성 (스트리밍 지원)
3. **체크리스트 생성**: 답변 기반으로 실행 가능한 체크리스트 자동 생성
4. **정보 보강**: 실시간 웹 검색으로 최신 정보 추가
5. **진행 관리**: 체크리스트 항목별 완료 상태 추적

## 🛠️ 기술 스택

### 백엔드
- **FastAPI** 0.116+ - 고성능 비동기 웹 프레임워크
- **SQLAlchemy** 2.0+ - 현대적 ORM 및 데이터베이스 관리
- **Alembic** - 데이터베이스 스키마 마이그레이션
- **Pydantic** 2.11+ - 데이터 검증 및 시리얼라이제이션
- **PyJWT** - JWT 토큰 관리

### AI & 검색
- **Google Gemini 2.5 Flash** - 최신 생성형 AI 모델
- **Google Search Grounding** - 실시간 웹 검색 통합
- **Structured Output** - 보장된 JSON 응답 형식

### 인증 & 보안
- **Google OAuth 2.0** - 소셜 로그인
- **JWT (Access + Refresh Token)** - 세션 관리
- **CORS** 설정 - 안전한 크로스 오리진 요청

### 데이터베이스 & 배포
- **PostgreSQL** (Neon 호스팅) - 클라우드 데이터베이스
- **Vercel** - 서버리스 배포 플랫폼

## 📦 로컬 개발 환경 설정

### 1. 프로젝트 클론 및 의존성 설치

```bash
git clone <repository-url>
cd nowwhat-back

# 가상환경 생성 및 활성화
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux  
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 환경변수 설정

`.env` 파일을 생성하고 다음 변수들을 설정하세요:

```bash
# 필수 환경변수
DATABASE_URL=postgresql://username:password@localhost:5432/nowwhat_db
GEMINI_API_KEY=your_gemini_api_key_here
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
SECRET_KEY=your_secret_key_for_jwt

# 선택적 환경변수
PORT=8000
ENV=development
LOG_LEVEL=INFO
GEMINI_MODEL=gemini-2.5-flash
MAX_CONCURRENT_SEARCHES=15
MIN_CHECKLIST_ITEMS=8
MAX_CHECKLIST_ITEMS=15
```

### 3. 데이터베이스 설정

```bash
# 데이터베이스 마이그레이션 실행
python -m alembic upgrade head

# 새 마이그레이션 생성 (필요시)
python -m alembic revision --autogenerate -m "마이그레이션 설명"
```

### 4. 서버 실행

```bash
# 개발 서버 실행 (핫 리로드 포함)
python run.py

# 또는 직접 uvicorn 실행
uvicorn app.main:app --reload --port 8000
```

서버가 실행되면 다음 URL에서 접근 가능합니다:
- **API 문서**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc  
- **헬스체크**: http://localhost:8000/health
- **루트**: http://localhost:8000/

## 🧪 테스트

```bash
# 테스트 의존성 설치
pip install pytest pytest-asyncio pytest-mock httpx pytest-cov

# 전체 테스트 실행
pytest

# 카테고리별 테스트 실행
pytest -m unit              # 단위 테스트
pytest -m integration       # 통합 테스트
pytest -m performance       # 성능 테스트

# 커버리지 보고서 생성
pytest --cov=app --cov-report=html

# 특정 파일 테스트
pytest tests/unit/api/test_questions_endpoint.py

# 병렬 테스트 실행
pytest -n auto
```

자세한 테스트 가이드는 `docs/testing-guide.md`를 참조하세요.

## 📋 API 엔드포인트

모든 엔드포인트는 `/api/v1/` 접두사를 사용합니다.

### 🔐 인증 (Authentication)
- `POST /auth/google` - 구글 OAuth 로그인
- `POST /auth/logout` - 로그아웃  
- `POST /auth/refresh` - 액세스 토큰 갱신

### 👤 사용자 (Users)
- `GET /users/profile` - 현재 사용자 프로필 조회

### 🎯 인텐트 분석 (Intents)
- `POST /intents/analyze` - 사용자 목표 인텐트 분석 (4가지 옵션 반환)

### ❓ 질문 (Questions)
- `POST /questions/generate` - 선택된 인텐트 기반 맞춤형 질문 생성
- `POST /questions/generate/stream` - 스트리밍 질문 생성 (SSE)
- `POST /questions/answer` - 답변 제출 및 체크리스트 생성

### ✅ 체크리스트 (Checklists)
- `GET /checklists` - 사용자 체크리스트 목록 조회
- `GET /checklists/{id}` - 특정 체크리스트 상세 조회
- `POST /checklists` - 새 체크리스트 생성
- `PUT /checklists/{id}/progress` - 진행상황 업데이트
- `DELETE /checklists/{id}` - 체크리스트 삭제

### 📝 피드백 (Feedback)
- `POST /feedback/submit` - 사용자 피드백 제출

## 🗄️ 데이터베이스 스키마

주요 테이블 및 관계:

```sql
users                    -- 사용자 정보
├── user_sessions        -- JWT 리프레시 토큰
├── intent_sessions      -- 임시 인텐트 분석 세션
├── checklists          -- 체크리스트
│   ├── checklist_items  -- 체크리스트 항목
│   │   └── checklist_item_details  -- 검색 기반 상세 정보
│   └── feedbacks       -- 체크리스트 피드백
└── questions           -- 생성된 질문 (임시 저장)
```

### 핵심 모델
- **User**: 구글 OAuth 인증 사용자
- **UserSession**: JWT 리프레시 토큰 저장
- **IntentSession**: 비로그인 사용자의 임시 세션
- **Checklist**: 사용자별 체크리스트 (제목, 설명, 진행률)
- **ChecklistItem**: 개별 체크리스트 항목
- **ChecklistItemDetails**: AI 검색으로 보강된 상세 정보 (팁, 연락처, 링크, 가격, 위치)
- **Feedback**: 사용자 피드백

## 🤖 AI 기능 상세

### Gemini AI 통합
- **모델**: Gemini 2.5 Flash (최신 버전)
- **토큰 한도**: 16,384 토큰 (긴 응답 지원)
- **구조화된 출력**: Pydantic 스키마 기반 JSON 보장
- **재시도 로직**: 지수 백오프를 통한 안정성 확보

### 실시간 웹 검색
- **Google Search Grounding**: 공식 구글 검색 API 통합
- **병렬 처리**: 최대 15개 동시 검색 쿼리
- **타임아웃**: 15초 검색 제한시간
- **폴백**: 검색 실패 시 지식 기반 응답

### 다국어 프롬프트 시스템
- **지원 언어**: 한국어(기본), 영어
- **동적 로딩**: `app/prompts/{언어}/` 구조
- **지역 맞춤화**: `countryOption=true` 시 국가별 정보 우선

### 스트리밍 응답
- **Server-Sent Events**: 실시간 질문 생성 진행상황
- **고유 스트림 ID**: 각 요청 추적 가능
- **에러 처리**: 스트림 중단 시 자동 복구

## 🌐 Vercel 배포

### 1. Vercel 설정

```bash
# Vercel CLI 설치
npm install -g vercel

# 로그인
vercel login

# 프로젝트 배포
vercel --prod
```

### 2. 환경변수 설정

Vercel 대시보드 또는 CLI로 다음 환경변수들을 설정:

```bash
# 필수 환경변수
vercel env add GEMINI_API_KEY
vercel env add DATABASE_URL
vercel env add SECRET_KEY  
vercel env add GOOGLE_CLIENT_ID
vercel env add GOOGLE_CLIENT_SECRET

# 선택적 환경변수
vercel env add GEMINI_MODEL
vercel env add MAX_CONCURRENT_SEARCHES
vercel env add MIN_CHECKLIST_ITEMS
vercel env add MAX_CHECKLIST_ITEMS
vercel env add ENV production
```

### 3. 배포 최적화

- **서버리스 함수**: Vercel의 서버리스 환경에 최적화
- **자동 테이블 생성**: 시작 시 자동으로 데이터베이스 테이블 생성
- **동기 SQLAlchemy**: psycopg2-binary 사용으로 서버리스 호환성 보장

## 🔧 개발 도구 및 팁

### 마이그레이션 관리

```bash
# 새 마이그레이션 생성
python -m alembic revision --autogenerate -m "테이블 추가"

# 마이그레이션 적용
python -m alembic upgrade head

# 마이그레이션 롤백  
python -m alembic downgrade -1

# 프로덕션 마이그레이션 (수동)
python scripts/migrate.py
```

### 로깅 및 디버깅

```bash
# 디버그 모드 실행
LOG_LEVEL=DEBUG python run.py

# 특정 서비스 로깅
import logging
logging.getLogger('app.services.gemini_service').setLevel(logging.DEBUG)
```

### 성능 모니터링

- Gemini API 응답 시간 추적
- 병렬 검색 성공률 모니터링  
- 데이터베이스 쿼리 최적화
- 메모리 사용량 추적

## 📊 환경변수 전체 목록

| 변수명 | 설명 | 기본값 | 필수 |
|--------|------|--------|------|
| `DATABASE_URL` | PostgreSQL 연결 문자열 | - | ✅ |
| `GEMINI_API_KEY` | Google Gemini API 키 | - | ✅ |
| `GOOGLE_CLIENT_ID` | 구글 OAuth 클라이언트 ID | - | ✅ |
| `GOOGLE_CLIENT_SECRET` | 구글 OAuth 클라이언트 시크릿 | - | ✅ |
| `SECRET_KEY` | JWT 시크릿 키 | 개발용 키 | ✅ |
| `PORT` | 서버 포트 | 8000 | ❌ |
| `HOST` | 서버 호스트 | 0.0.0.0 | ❌ |
| `ENV` | 실행 환경 | development | ❌ |
| `LOG_LEVEL` | 로그 레벨 | INFO | ❌ |
| `GEMINI_MODEL` | Gemini 모델 버전 | gemini-2.5-flash | ❌ |
| `MAX_CONCURRENT_SEARCHES` | 최대 병렬 검색 수 | 15 | ❌ |
| `SEARCH_TIMEOUT_SECONDS` | 검색 타임아웃 (초) | 15 | ❌ |
| `MIN_CHECKLIST_ITEMS` | 최소 체크리스트 항목 | 8 | ❌ |
| `MAX_CHECKLIST_ITEMS` | 최대 체크리스트 항목 | 15 | ❌ |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 액세스 토큰 만료 시간 | 30 | ❌ |
| `RATE_LIMIT_CALLS` | 레이트 리미트 호출 수 | 100 | ❌ |
| `RATE_LIMIT_PERIOD` | 레이트 리미트 기간 (초) | 60 | ❌ |

## 🚀 성능 및 확장성

- **비동기 처리**: 모든 외부 API 호출은 async/await 패턴
- **병렬 처리**: 최대 15개 동시 검색으로 응답 시간 단축
- **캐싱**: 자주 사용되는 프롬프트 및 템플릿 캐싱
- **에러 복구**: 다층 폴백 메커니즘으로 안정성 보장
- **토큰 최적화**: 긴 응답을 위한 16K 토큰 한도

## 🔍 문제 해결

### 일반적인 문제들

**1. Gemini API 키 오류**
```bash
# API 키 확인
echo $GEMINI_API_KEY
# 또는 .env 파일 확인
```

**2. 데이터베이스 연결 오류**
```bash
# 연결 문자열 확인
python -c "from app.core.config import settings; print(settings.DATABASE_URL)"

# 마이그레이션 실행
python -m alembic upgrade head
```

**3. 스트리밍 응답 문제**
- 브라우저에서 EventSource 지원 확인
- CORS 설정 확인
- 네트워크 프록시/방화벽 확인

**4. 검색 기능 오류**
- Gemini API 키 권한 확인
- 검색 쿼리 형식 확인
- 타임아웃 설정 조정

### 로그 확인

```bash
# 서비스별 로그 확인
grep "GeminiService" logs/app.log
grep "ChecklistOrchestrator" logs/app.log
grep "ERROR" logs/app.log
```

## 🤝 기여하기

1. 레포지토리 Fork
2. 기능 브랜치 생성 (`git checkout -b feature/amazing-feature`)
3. 변경사항 커밋 (`git commit -m 'Add some amazing feature'`)
4. 브랜치 푸시 (`git push origin feature/amazing-feature`)
5. Pull Request 생성

### 개발 가이드라인

- 모든 새 기능은 테스트 작성 필수
- 코드 스타일: Black 포맷터 사용 권장
- 커밋 메시지: 명확하고 설명적으로 작성
- API 변경 시 문서 업데이트 필수

## 📚 추가 문서

- [API 테스팅 가이드](docs/testing-guide.md)
- [질문-답변 API 문서](docs/questions/answer.md)
- [데이터베이스 마이그레이션 가이드](docs/database-migration-guide.md)
- [배포 가이드](README_DEPLOYMENT.md)

## 📄 라이센스

이 프로젝트는 MIT 라이센스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 🔗 관련 링크

- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [Google Gemini API](https://ai.google.dev/)
- [Vercel 배포 가이드](https://vercel.com/docs)
- [Neon PostgreSQL](https://neon.tech/)
- [Google OAuth 2.0](https://developers.google.com/identity/protocols/oauth2)
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/)

## ⭐ 주요 특징

- 🎯 **사용자 목표 중심**: 모든 기능이 사용자의 실제 목표 달성에 최적화
- 🤖 **AI 네이티브**: 최신 Gemini 2.5 Flash로 정확하고 실용적인 제안
- 🔍 **실시간 정보**: 웹 검색 통합으로 항상 최신 정보 제공
- 🌏 **글로벌 지원**: 다국어 및 지역별 맞춤 정보
- ⚡ **고성능**: 비동기 처리와 병렬 검색으로 빠른 응답
- 🛡️ **안전함**: 포괄적인 에러 처리와 폴백 메커니즘

---

**NowWhat API Server**는 사용자의 목표를 실현 가능한 실행 계획으로 변환하는 혁신적인 AI 서비스입니다. 🚀