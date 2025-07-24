from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import time
import uuid

class NotionAPIMiddleware(BaseHTTPMiddleware):
    """노션 API 스타일의 미들웨어"""
    
    async def dispatch(self, request: Request, call_next):
        # 요청 ID 생성 (노션 API는 각 요청에 고유 ID 부여)
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # 시작 시간 기록
        start_time = time.time()
        
        # 노션 버전 헤더 확인
        notion_version = request.headers.get("Notion-Version")
        if not notion_version:
            return JSONResponse(
                status_code=400,
                content={
                    "object": "error",
                    "status": 400,
                    "code": "missing_version",
                    "message": "Notion-Version 헤더가 필요합니다.",
                    "request_id": request_id
                }
            )
        
        # 응답 처리
        try:
            response = await call_next(request)
            
            # 처리 시간 계산
            process_time = time.time() - start_time
            
            # 노션 API 스타일 헤더 추가
            response.headers["Notion-Version"] = notion_version
            response.headers["Request-Id"] = request_id
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "object": "error",
                    "status": 500,
                    "code": "internal_server_error",
                    "message": "내부 서버 오류가 발생했습니다.",
                    "request_id": request_id
                }
            )

class RateLimitMiddleware(BaseHTTPMiddleware):
    """요청 제한 미들웨어 (노션 API는 초당 3회 제한)"""
    
    def __init__(self, app, calls: int = 3, period: int = 1):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.requests = {}
    
    async def dispatch(self, request: Request, call_next):
        # TODO: 실제 레이트 리미팅 로직 구현
        # 1. 클라이언트 IP 또는 API 키 기반으로 요청 추적
        # 2. 시간 윈도우 내 요청 수 확인
        # 3. 제한 초과 시 429 에러 반환
        
        response = await call_next(request)
        return response 