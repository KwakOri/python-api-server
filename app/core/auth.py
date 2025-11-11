"""
API 키 기반 인증 모듈
"""
import os
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 환경 변수에서 API 키 가져오기
API_KEY = os.getenv("API_KEY")

if not API_KEY:
    raise ValueError("API_KEY 환경 변수가 설정되지 않았습니다. .env 파일을 확인하세요.")


# 인증이 필요 없는 공개 엔드포인트 목록
PUBLIC_PATHS = [
    "/",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/align/",  # GET 헬스체크
    "/api/grade/",  # GET 헬스체크
]


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    API 키 검증 미들웨어
    모든 요청에 대해 API 키를 검증하며, 공개 엔드포인트는 제외합니다.
    """

    async def dispatch(self, request: Request, call_next):
        """
        요청 처리 전 API 키 검증

        Args:
            request: FastAPI Request 객체
            call_next: 다음 미들웨어 또는 엔드포인트 호출 함수

        Returns:
            Response: 응답 객체
        """
        # 공개 엔드포인트는 인증 생략
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        # GET 요청은 인증 생략 (헬스체크 등)
        if request.method == "GET":
            return await call_next(request)

        # API 키 헤더 확인
        api_key = request.headers.get("X-API-Key")

        if not api_key:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "success": False,
                    "error": "API 키가 제공되지 않았습니다",
                    "detail": "X-API-Key 헤더를 포함해주세요"
                },
                headers={"WWW-Authenticate": "ApiKey"},
            )

        # API 키 검증
        if api_key != API_KEY:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "success": False,
                    "error": "유효하지 않은 API 키입니다",
                    "detail": "올바른 API 키를 제공해주세요"
                },
                headers={"WWW-Authenticate": "ApiKey"},
            )

        # 검증 통과 시 다음 단계로 진행
        response = await call_next(request)
        return response
