"""
메모리 사용량 로깅 미들웨어
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time
import logging

from app.core.memory_monitor import get_memory_usage

logger = logging.getLogger(__name__)


class MemoryLoggingMiddleware(BaseHTTPMiddleware):
    """
    각 요청 전후의 메모리 사용량을 로깅하는 미들웨어
    """

    async def dispatch(self, request: Request, call_next):
        # 헬스체크는 로깅 스킵
        if request.url.path == "/health":
            return await call_next(request)

        # 요청 전 메모리 측정
        memory_before = get_memory_usage()
        start_time = time.time()

        # 요청 처리
        response: Response = await call_next(request)

        # 요청 후 메모리 측정
        memory_after = get_memory_usage()
        process_time = time.time() - start_time

        # 메모리 변화량 계산
        memory_delta = memory_after["rss_mb"] - memory_before["rss_mb"]

        # 로그 출력
        logger.info(
            f"[{request.method} {request.url.path}] "
            f"처리시간: {process_time:.2f}s | "
            f"메모리: {memory_before['rss_mb']}MB → {memory_after['rss_mb']}MB "
            f"({'+' if memory_delta >= 0 else ''}{memory_delta:.2f}MB) | "
            f"사용률: {memory_after['percent']}%"
        )

        # 메모리 사용률이 80% 이상이면 경고
        if memory_after["percent"] > 80:
            logger.warning(
                f"⚠️ 높은 메모리 사용률 감지: {memory_after['percent']}% "
                f"({memory_after['rss_mb']}MB)"
            )

        return response
