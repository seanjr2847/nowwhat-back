from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.schemas.nowwhat import GoogleLoginRequest, LoginResponse, LogoutRequest, APIResponse, UserProfile
from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token, verify_token
from app.services.google_auth import google_auth_service
from app.crud.user import user
from app.models.database import UserSession
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/google", response_model=LoginResponse)
async def google_login(
    login_data: GoogleLoginRequest,
    db: Session = Depends(get_db)
):
    """구글 OAuth 로그인"""
    try:
        # 1. 구글 토큰 검증
        google_user_info = await google_auth_service.verify_google_token(login_data.googleToken)
        
        if not google_user_info:
            # 대안 방법으로 재시도
            google_user_info = await google_auth_service.verify_google_token_alternative(login_data.googleToken)
            
        if not google_user_info:
            raise HTTPException(
                status_code=400, 
                detail="유효하지 않은 구글 토큰입니다."
            )
        
        logger.info(f"Google login attempt for email: {google_user_info['email']}")
        
        # 2. 사용자 조회 또는 생성
        db_user = user.get_by_google_id(db, google_id=google_user_info['google_id'])
        
        if not db_user:
            # 이메일로 기존 계정 확인
            db_user = user.get_by_email(db, email=google_user_info['email'])
            
            if db_user:
                # 기존 계정에 구글 ID 연결
                db_user.google_id = google_user_info['google_id']
                db_user.profile_image = google_user_info.get('profile_image')
                db_user.last_login_at = datetime.utcnow()
                db.add(db_user)
                db.commit()
                db.refresh(db_user)
                logger.info(f"Linked Google account to existing user: {db_user.email}")
            else:
                # 새 사용자 생성
                user_data = {
                    "email": google_user_info['email'],
                    "name": google_user_info['name'],
                    "profile_image": google_user_info.get('profile_image'),
                    "google_id": google_user_info['google_id'],
                    "last_login_at": datetime.utcnow()
                }
                db_user = user.create_user(db, user_data=user_data)
                logger.info(f"Created new user: {db_user.email}")
        else:
            # 기존 사용자 정보 업데이트
            db_user.name = google_user_info['name']
            db_user.profile_image = google_user_info.get('profile_image')
            db_user.last_login_at = datetime.utcnow()
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            logger.info(f"Updated existing user: {db_user.email}")
        
        # 3. JWT 토큰 생성
        access_token = create_access_token(subject=db_user.id)
        refresh_token = create_refresh_token(subject=db_user.id)
        
        # 4. 리프레시 토큰 저장 (DB에 저장)
        user_session = UserSession(
            user_id=db_user.id,
            refresh_token=refresh_token,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        db.add(user_session)
        db.commit()
        
        # 5. 응답 반환
        return LoginResponse(
            accessToken=access_token,
            refreshToken=refresh_token,
            user={
                "id": db_user.id,
                "email": db_user.email,
                "name": db_user.name,
                "profileImage": db_user.profile_image,
                "googleId": db_user.google_id,
                "createdAt": db_user.created_at.isoformat(),
                "lastLoginAt": db_user.last_login_at.isoformat() if db_user.last_login_at else None
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google login error: {e}")
        raise HTTPException(
            status_code=500, 
            detail="로그인 처리 중 오류가 발생했습니다."
        )

@router.get("/me")
async def get_current_user_info(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """현재 로그인한 사용자 정보 조회"""
    try:
        # get_current_user에서 이미 사용자 정보를 조회했지만, 
        # 최신 정보를 위해 다시 조회
        db_user = user.get(db, id=current_user.id)
        
        if not db_user:
            raise HTTPException(
                status_code=404, 
                detail="사용자를 찾을 수 없습니다."
            )
        
        return {
            "id": db_user.id,
            "email": db_user.email,
            "name": db_user.name,
            "profileImage": db_user.profile_image,
            "googleId": db_user.google_id,
            "createdAt": db_user.created_at.isoformat(),
            "lastLoginAt": db_user.last_login_at.isoformat() if db_user.last_login_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get current user error: {e}")
        raise HTTPException(
            status_code=500, 
            detail="사용자 정보 조회 중 오류가 발생했습니다."
        )

@router.post("/logout", response_model=APIResponse)
async def logout(
    logout_data: LogoutRequest, 
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """로그아웃"""
    try:
        # 리프레시 토큰 검증
        user_id = verify_token(logout_data.refreshToken, token_type="refresh")
        
        if not user_id or user_id != current_user.id:
            raise HTTPException(
                status_code=400, 
                detail="유효하지 않은 리프레시 토큰입니다."
            )
        
        # 데이터베이스에서 해당 세션 삭제
        session = db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.refresh_token == logout_data.refreshToken
        ).first()
        
        if session:
            db.delete(session)
            db.commit()
            logger.info(f"User {user_id} logged out successfully")
        
        return APIResponse(
            success=True,
            message="로그아웃되었습니다."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=500, 
            detail="로그아웃 처리 중 오류가 발생했습니다."
        )

@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(
    refresh_data: LogoutRequest,  # 같은 스키마 재사용 (refreshToken 필드)
    db: Session = Depends(get_db)
):
    """액세스 토큰 갱신"""
    try:
        # 리프레시 토큰 검증
        user_id = verify_token(refresh_data.refreshToken, token_type="refresh")
        
        if not user_id:
            raise HTTPException(
                status_code=401, 
                detail="유효하지 않은 리프레시 토큰입니다."
            )
        
        # 데이터베이스에서 세션 확인
        session = db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.refresh_token == refresh_data.refreshToken,
            UserSession.expires_at > datetime.utcnow()
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=401, 
                detail="만료되거나 유효하지 않은 세션입니다."
            )
        
        # 사용자 정보 조회
        db_user = user.get(db, id=user_id)
        if not db_user:
            raise HTTPException(
                status_code=404, 
                detail="사용자를 찾을 수 없습니다."
            )
        
        # 새로운 액세스 토큰 생성
        new_access_token = create_access_token(subject=db_user.id)
        
        return LoginResponse(
            accessToken=new_access_token,
            refreshToken=refresh_data.refreshToken,  # 기존 리프레시 토큰 유지
            user={
                "id": db_user.id,
                "email": db_user.email,
                "name": db_user.name,
                "profileImage": db_user.profile_image,
                "googleId": db_user.google_id,
                "createdAt": db_user.created_at.isoformat(),
                "lastLoginAt": db_user.last_login_at.isoformat() if db_user.last_login_at else None
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=500, 
            detail="토큰 갱신 중 오류가 발생했습니다."
        ) 