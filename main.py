"""
시험지 정렬 및 채점 API 서버
FastAPI 애플리케이션 진입점
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import sys

from app.routers import align

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="시험지 정렬 및 채점 API",
    description="""
    스캔된 시험지 이미지를 정렬하고 채점하기 위한 API 서버입니다.

    ## 주요 기능

    * **이미지 정렬**: SIFT 또는 Contour 방식으로 시험지 이미지 정렬
    * **배치 처리**: 여러 이미지를 한 번에 처리
    * **이미지 품질 개선**: CLAHE 및 노이즈 제거
    * **OMR 채점**: (추후 구현 예정)

    ## 정렬 방식

    ### SIFT (Scale-Invariant Feature Transform)
    - 높은 정확도
    - 템플릿 이미지 필요
    - 특징점 매칭 기반
    - 회전, 크기, 왜곡에 강함

    ### Contour (외곽선 검출)
    - 빠른 처리 속도
    - 템플릿 선택사항
    - 외곽선 기반
    - 깔끔한 배경의 스캔본에 적합
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(align.router)


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
            "align_batch": "/api/align/batch"
        },
        "methods": {
            "sift": "SIFT + Homography (고정확도, 템플릿 필요)",
            "contour": "Contour Detection (고속, 템플릿 선택)"
        }
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


# 애플리케이션 시작 이벤트
@app.on_event("startup")
async def startup_event():
    """
    서버 시작 시 실행
    """
    logger.info("=" * 50)
    logger.info("시험지 정렬 및 채점 API 서버 시작")
    logger.info("=" * 50)
    logger.info("API 문서: http://localhost:8080/docs")
    logger.info("=" * 50)


# 애플리케이션 종료 이벤트
@app.on_event("shutdown")
async def shutdown_event():
    """
    서버 종료 시 실행
    """
    logger.info("서버 종료 중...")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )
