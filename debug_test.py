#!/usr/bin/env python3
"""
단계별 디버깅 스크립트
"""

import asyncio
import traceback

def test_database():
    """데이터베이스 연결 테스트"""
    try:
        print("🔍 데이터베이스 연결 테스트...")
        from app.core.database import test_connection
        result = test_connection()
        print(f"✅ 데이터베이스 연결: {'성공' if result else '실패'}")
        return result
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {e}")
        traceback.print_exc()
        return False

def test_session_crud():
    """세션 CRUD 테스트"""
    try:
        print("🔍 세션 CRUD 테스트...")
        from app.core.database import SessionLocal
        from app.crud.session import create_intent_session
        
        db = SessionLocal()
        session = create_intent_session(
            db=db,
            goal="테스트 목표",
            user_ip="127.0.0.1",
            user_country="KR"
        )
        db.close()
        
        print(f"✅ 세션 생성 성공: {session.session_id}")
        return True
    except Exception as e:
        print(f"❌ 세션 CRUD 실패: {e}")
        traceback.print_exc()
        return False

def test_geo_utils():
    """지역 감지 유틸리티 테스트"""
    try:
        print("🔍 지역 감지 테스트...")
        from app.utils.geo_utils import get_client_ip
        
        # 더미 요청 객체 생성
        class DummyRequest:
            def __init__(self):
                self.headers = {}
                self.client = type('obj', (object,), {'host': '127.0.0.1'})()
        
        request = DummyRequest()
        ip = get_client_ip(request)
        print(f"✅ IP 추출 성공: {ip}")
        return True
    except Exception as e:
        print(f"❌ 지역 감지 실패: {e}")
        traceback.print_exc()
        return False

async def test_geo_utils_async():
    """비동기 지역 감지 테스트"""
    try:
        print("🔍 비동기 지역 감지 테스트...")
        from app.utils.geo_utils import detect_country_from_ip
        
        country = await detect_country_from_ip("127.0.0.1")
        print(f"✅ 국가 감지 성공: {country}")
        return True
    except Exception as e:
        print(f"❌ 비동기 지역 감지 실패: {e}")
        traceback.print_exc()
        return False

async def test_gemini_service():
    """Gemini 서비스 테스트"""
    try:
        print("🔍 Gemini 서비스 테스트...")
        from app.services.gemini_service import gemini_service
        
        intents = await gemini_service.analyze_intent("일본여행 가고싶어", "KR")
        print(f"✅ Gemini 분석 성공: {len(intents)}개 의도")
        for i, intent in enumerate(intents):
            print(f"  {i+1}. {intent.icon} {intent.title}")
        return True
    except Exception as e:
        print(f"❌ Gemini 서비스 실패: {e}")
        traceback.print_exc()
        return False

async def main():
    """메인 테스트 함수"""
    print("🧪 단계별 디버깅 시작")
    print("=" * 50)
    
    # 1. 데이터베이스 테스트
    if not test_database():
        print("❌ 데이터베이스 문제로 중단")
        return
    
    # 2. 세션 CRUD 테스트
    if not test_session_crud():
        print("❌ 세션 CRUD 문제로 중단")
        return
    
    # 3. 지역 감지 테스트
    if not test_geo_utils():
        print("❌ 지역 감지 문제로 중단")
        return
    
    # 4. 비동기 지역 감지 테스트
    if not await test_geo_utils_async():
        print("❌ 비동기 지역 감지 문제")
    
    # 5. Gemini 서비스 테스트
    if not await test_gemini_service():
        print("❌ Gemini 서비스 문제")
    
    print("\n🏁 디버깅 완료!")

if __name__ == "__main__":
    asyncio.run(main()) 