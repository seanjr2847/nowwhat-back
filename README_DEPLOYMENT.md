# 프로덕션 배포 및 데이터베이스 마이그레이션 가이드

## 📋 프로덕션 환경에서의 데이터베이스 마이그레이션 전략

### 1. 권장 방법: 수동 마이그레이션 (안전함)

```bash
# 1. 프로덕션 데이터베이스에 직접 연결하여 마이그레이션 실행
export DATABASE_URL="your_production_database_url"
python scripts/migrate.py
```

### 2. Vercel 배포 시 자동 마이그레이션 (주의 필요)

#### 방법 A: GitHub Actions 사용 (권장)

`.github/workflows/deploy.yml` 생성:

```yaml
name: Deploy to Vercel
on:
  push:
    branches: [main]

jobs:
  migrate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run migrations
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: python scripts/migrate.py
  
  deploy:
    needs: migrate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.ORG_ID }}
          vercel-project-id: ${{ secrets.PROJECT_ID }}
```

#### 방법 B: 애플리케이션 시작 시 마이그레이션

`app/main.py`에 추가:

```python
@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 마이그레이션 자동 실행 (개발/테스트 환경에서만 권장)"""
    if settings.ENV == "development":
        try:
            from scripts.migrate import run_migrations
            run_migrations()
        except Exception as e:
            logger.warning(f"Migration failed: {e}")
```

### 3. 데이터베이스 백업 및 복원

#### 백업 생성
```bash
# Neon PostgreSQL 백업
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql
```

#### 복원
```bash
# 백업 복원
psql $DATABASE_URL < backup_file.sql
```

### 4. 마이그레이션 롤백

```bash
# 이전 버전으로 롤백
python -m alembic downgrade -1

# 특정 리비전으로 롤백
python -m alembic downgrade 1a77684abf7d
```

## 🚨 프로덕션 배포 체크리스트

### 배포 전 확인사항
- [ ] 로컬에서 마이그레이션 테스트 완료
- [ ] 데이터베이스 백업 생성
- [ ] 환경변수 설정 확인 (`GEMINI_API_KEY`, `DATABASE_URL` 등)
- [ ] 의존성 패키지 설치 확인 (`google-generativeai`)

### 배포 후 확인사항
- [ ] 데이터베이스 테이블 생성 확인
- [ ] API 엔드포인트 동작 확인
- [ ] 로그 모니터링

## 🔧 환경변수 설정

### Vercel 환경변수
```bash
# Vercel CLI로 환경변수 설정
vercel env add GEMINI_API_KEY
vercel env add DATABASE_URL
vercel env add SECRET_KEY
vercel env add GOOGLE_CLIENT_ID
vercel env add GOOGLE_CLIENT_SECRET
```

### 필수 환경변수
- `GEMINI_API_KEY`: Google Gemini API 키
- `DATABASE_URL`: PostgreSQL 연결 URL
- `SECRET_KEY`: JWT 시크릿 키
- `GOOGLE_CLIENT_ID`: 구글 OAuth 클라이언트 ID
- `GOOGLE_CLIENT_SECRET`: 구글 OAuth 클라이언트 시크릿

## 🧪 테스트

### API 테스트
```bash
# 의도 분석 API 테스트
curl -X POST "https://your-api-domain.vercel.app/api/v1/intents/analyze" \
  -H "Content-Type: application/json" \
  -d '{"goal": "일본여행 가고싶어"}'
```

### 기대 응답
```json
{
  "sessionId": "sess_1705737600_abc123",
  "intents": [
    {
      "title": "여행 일정 짜기",
      "description": "며칠 동안 어디를 방문할지 구체적인 일정을 계획하고 싶으신가요?",
      "icon": "📅"
    }
  ]
}
```

## 📊 모니터링

### 로그 확인
```bash
# Vercel 로그 확인
vercel logs

# 특정 함수 로그
vercel logs --follow
```

### 성능 모니터링
- 응답 시간: 목표 < 3초
- 에러율: < 1%
- Gemini API 호출 성공률: > 95%

## 🔄 CI/CD 파이프라인

권장 배포 플로우:
1. **개발** → 로컬 테스트
2. **스테이징** → 마이그레이션 테스트 + API 테스트
3. **프로덕션** → 백업 + 마이그레이션 + 배포 + 검증 