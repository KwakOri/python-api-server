"""
시험지 정렬 및 채점 API 서버
FastAPI 애플리케이션 진입점
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from fastapi.openapi.docs import get_swagger_ui_html
from contextlib import asynccontextmanager
import logging
import sys

from app.routers import align, grade, alimtok
from app.core.auth import APIKeyMiddleware
from app.core.processing_limiter import limiter

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# 헬스체크 로그 필터 추가
from app.core.logging_config import HealthCheckFilter

# uvicorn.access 로거에 필터 추가 (헬스체크 로그 제외)
logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())

logger = logging.getLogger(__name__)


# Lifespan 이벤트 핸들러
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    애플리케이션 라이프사이클 관리
    시작 시 초기화, 종료 시 정리 작업 수행
    """
    # 시작 시 실행
    logger.info("=" * 50)
    logger.info("시험지 정렬 및 채점 API 서버 시작")
    logger.info("=" * 50)
    logger.info("API 문서: http://localhost:8080/docs")
    logger.info("=" * 50)

    yield  # 애플리케이션 실행

    # 종료 시 실행
    logger.info("서버 종료 중...")


# API 키 헤더 정의 (Swagger UI용)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# FastAPI 앱 생성
app = FastAPI(
    lifespan=lifespan,
    title="시험지 정렬 및 채점 API",
    description="""
    스캔된 시험지 이미지를 정렬하고 채점하기 위한 API 서버입니다.

    ## 인증 방법

    POST 요청은 API 키 인증이 필요합니다. Swagger UI 우측 상단의 **Authorize** 버튼을 클릭하여 API 키를 입력하세요.

    - 헤더명: `X-API-Key`
    - 값: `.env` 파일의 `API_KEY` 값

    ## 주요 기능

    * **이미지 정렬**: SIFT 또는 Contour 방식으로 시험지 이미지 정렬
    * **배치 처리**: 여러 이미지를 한 번에 처리
    * **이미지 품질 개선**: CLAHE 및 노이즈 제거
    * **OMR 마킹 검출**: 45문항 5지선다형 답안 자동 검출
    * **자동 채점**: 정답과 비교하여 자동 채점 및 통계 제공
    * **알림톡 발송**: 센드온 API를 통한 카카오 알림톡 메시지 발송

    ## 정렬 방식

    ### SIFT (Scale-Invariant Feature Transform)
    - 높은 정확도
    - 템플릿 이미지 자동 사용 (omr_card.jpg)
    - 특징점 매칭 기반
    - 회전, 크기, 왜곡에 강함

    ### Contour (외곽선 검출)
    - 빠른 처리 속도
    - 템플릿 불필요
    - 외곽선 기반
    - 깔끔한 배경의 스캔본에 적합

    ## OMR 채점

    ### 지원 형식
    - 총 45문항 (1열: 1-20, 2열: 21-34, 3열: 35-45)
    - 문항당 5개 선택지
    - 퍼센트 기반 ROI 좌표 시스템

    ### 기능
    - 마킹 자동 검출 (픽셀 밀도 분석)
    - 중복 마킹 처리
    - 무응답 검출
    - 정답률 통계 제공

    ## 알림톡 발송

    ### 사전 준비사항
    - 카카오 비즈니스 채널 생성 및 연동
    - 알림톡 템플릿 등록 및 승인 완료
    - 센드온 API 키 설정 (환경 변수 `SENDON_API_KEY`)

    ### 기능
    - 최대 1,000명 동시 발송
    - 템플릿 변수 치환
    - 예약 발송
    - 대체문자 설정 (SMS/LMS/MMS)
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    swagger_ui_parameters={
        "persistAuthorization": True  # API 키를 브라우저에 저장
    }
)

# OpenAPI 스키마에 보안 설정 추가
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # API Key 보안 스키마 추가
    openapi_schema["components"]["securitySchemes"] = {
        "APIKeyHeader": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API 키를 입력하세요. POST 요청에 필요합니다."
        }
    }

    # 기본 보안 설정 (모든 엔드포인트에 적용)
    # 실제 인증은 미들웨어에서 처리하므로 UI에만 표시
    openapi_schema["security"] = [{"APIKeyHeader": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 미들웨어 등록
app.add_middleware(APIKeyMiddleware)

# 라우터 등록
app.include_router(align.router)
app.include_router(grade.router)
app.include_router(alimtok.router)


@app.get("/")
async def root():
    """
    루트 엔드포인트 - API 정보 반환
    """
    return {
        "service": "시험지 정렬 및 채점 API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/health",
            "align": "/api/align",
            "align_batch": "/api/align/batch",
            "grade_detect": "/api/grade/detect",
            "grade": "/api/grade",
            "grade_batch": "/api/grade/batch",
            "alimtok_send": "/api/alimtok/send",
            "alimtok_health": "/api/alimtok/health"
        },
        "features": "OMR 기반 마킹 추출 및 분석, 알림톡 메시지 발송"
    }


@app.get("/health")
async def health_check():
    """
    헬스 체크 엔드포인트
    """
    return {
        "status": "healthy",
        "service": "exam-alignment-api"
    }


@app.get("/queue/status")
async def queue_status():
    """
    대기열 상태 확인 엔드포인트
    """
    status = limiter.get_status()
    return {
        "status": "ok",
        "processing": status["processing"],
        "waiting": status["waiting"],
        "max_queue_size": status["max_queue_size"],
        "available": status["waiting"] < status["max_queue_size"]
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    전역 예외 핸들러
    """
    logger.error(f"처리되지 않은 예외 발생: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "서버 내부 오류가 발생했습니다",
            "detail": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )
