# NowWhat API Server 🚀

인텐트 분석 및 체크리스트 생성을 위한 FastAPI 백엔드 서버입니다.

## ✨ 주요 기능

- 🔐 **구글 OAuth 2.0** 인증 시스템
- 🗄️ **PostgreSQL (Neon DB)** 데이터베이스
- 🛡️ **JWT 토큰** 기반 보안
- 📊 **인텐트 분석** API
- ✅ **체크리스트 생성** 및 관리
- 📝 **피드백 시스템**
- 🌐 **Vercel 배포** 지원

## 🛠️ 기술 스택

- **FastAPI** - 고성능 Python 웹 프레임워크
- **SQLAlchemy** - ORM 및 데이터베이스 관리
- **Alembic** - 데이터베이스 마이그레이션
- **Pydantic** - 데이터 검증 및 시리얼라이제이션
- **PyJWT** - JWT 토큰 관리
- **Google Auth** - OAuth 2.0 인증
- **PostgreSQL** - 메인 데이터베이스 (Neon 호스팅)

## 📦 로컬 설치 및 실행

### 1. 프로젝트 클론
```bash
git clone <repository-url>
cd nowwhat-back
```

### 2. 가상환경 설정
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. 의존성 설치
```bash
pip install -r requirements.txt
```

### 4. 데이터베이스 마이그레이션
```bash
python -m alembic upgrade head
```

### 5. 서버 실행
```bash
python run.py
```

서버가 실행되면 다음 URL에서 접근 가능합니다:
- **API 문서**: http://localhost:8000/docs
- **헬스체크**: http://localhost:8000/health

## 🌐 Vercel 배포

### 1. Vercel 계정 생성 및 CLI 설치
```bash
npm install -g vercel
vercel login
```

### 2. 프로젝트 배포
```bash
vercel --prod
```

### 3. 환경변수 설정 (Vercel 대시보드에서)
- `DATABASE_URL`: PostgreSQL 연결 문자열
- `SECRET_KEY`: JWT 시크릿 키 (프로덕션용으로 변경)
- `ENV`: production

## 📋 API 엔드포인트

### 인증 (Authentication)
- `POST /api/v1/auth/google` - 구글 OAuth 로그인
- `POST /api/v1/auth/logout` - 로그아웃
- `POST /api/v1/auth/refresh` - 액세스 토큰 갱신

### 사용자 (Users)
- `GET /api/v1/users/profile` - 현재 사용자 프로필 조회

### 인텐트 분석 (Intents)
- `POST /api/v1/intents/analyze` - 사용자 인텐트 분석

### 질문 (Questions)
- `POST /api/v1/questions/generate` - 맞춤형 질문 생성
- `POST /api/v1/questions/submit` - 답변 제출

### 체크리스트 (Checklists)
- `GET /api/v1/checklists` - 사용자 체크리스트 목록
- `POST /api/v1/checklists` - 새 체크리스트 생성
- `PUT /api/v1/checklists/{id}/progress` - 진행상황 업데이트

### 피드백 (Feedback)
- `POST /api/v1/feedback/submit` - 피드백 제출

## 🗄️ 데이터베이스 스키마

주요 테이블:
- `users` - 사용자 정보
- `user_sessions` - 사용자 세션 (리프레시 토큰)
- `intents` - 인텐트 분석 결과
- `questions` - 질문 및 답변
- `checklists` - 체크리스트 정보
- `checklist_items` - 체크리스트 아이템
- `feedbacks` - 사용자 피드백

## 🔧 개발 도구

### 새 마이그레이션 생성
```bash
python -m alembic revision --autogenerate -m "설명"
```

### 마이그레이션 적용
```bash
python -m alembic upgrade head
```

### 마이그레이션 롤백
```bash
python -m alembic downgrade -1
```

## 📝 환경변수

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `DATABASE_URL` | PostgreSQL 연결 문자열 | Neon DB URL |
| `SECRET_KEY` | JWT 시크릿 키 | 개발용 키 |
| `PORT` | 서버 포트 | 8000 |
| `ENV` | 환경 (development/production) | development |
| `LOG_LEVEL` | 로그 레벨 | INFO |

## 🤝 기여하기

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 라이센스

이 프로젝트는 MIT 라이센스 하에 배포됩니다.

## 🔗 관련 링크

- [FastAPI 문서](https://fastapi.tiangolo.com/)
- [Vercel 배포 가이드](https://vercel.com/docs)
- [Neon PostgreSQL](https://neon.tech/)
- [Google OAuth 2.0](https://developers.google.com/identity/protocols/oauth2) 