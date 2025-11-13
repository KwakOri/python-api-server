"""
로깅 설정 및 헬스체크 필터
"""
import logging
import time
import functools
from typing import Callable
from fastapi import Request

logger = logging.getLogger(__name__)


class HealthCheckFilter(logging.Filter):
    """
    헬스체크 엔드포인트 로그를 필터링하는 클래스
    """
    def filter(self, record: logging.LogRecord) -> bool:
        """
        헬스체크 요청 로그를 제외

        Args:
            record: 로그 레코드

        Returns:
            bool: True면 로그 출력, False면 로그 제외
        """
        # /health 엔드포인트 로그 제외
        return "GET /health" not in record.getMessage()


def log_api_call(endpoint_name: str):
    """
    API 호출을 로깅하는 데코레이터

    Args:
        endpoint_name: API 엔드포인트 이름
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()

            # 요청 정보 추출
            request_info = {}
            for arg in args:
                if isinstance(arg, Request):
                    request_info = {
                        "client": arg.client.host if arg.client else "unknown",
                        "method": arg.method,
                        "url": str(arg.url)
                    }
                    break

            # 파라미터 정보 (파일 제외)
            params = {}
            for key, value in kwargs.items():
                if not hasattr(value, 'file'):  # UploadFile 제외
                    if key == 'answer_key' and isinstance(value, str) and len(value) > 50:
                        params[key] = value[:50] + "..."  # 긴 정답 키는 축약
                    else:
                        params[key] = value

            logger.info(
                f"[{endpoint_name}] 요청 시작 | "
                f"Client: {request_info.get('client', 'unknown')} | "
                f"Params: {params}"
            )

            try:
                result = await func(*args, **kwargs)

                elapsed_time = time.time() - start_time
                logger.info(
                    f"[{endpoint_name}] 요청 완료 | "
                    f"소요 시간: {elapsed_time:.2f}초 | "
                    f"성공: True"
                )

                return result

            except Exception as e:
                elapsed_time = time.time() - start_time
                logger.error(
                    f"[{endpoint_name}] 요청 실패 | "
                    f"소요 시간: {elapsed_time:.2f}초 | "
                    f"에러: {str(e)}"
                )
                raise

        return wrapper
    return decorator
