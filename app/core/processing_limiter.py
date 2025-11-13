"""
이미지 처리 동시 실행 제한 (1GB RAM 최적화)
"""
import asyncio
import time
import logging
from typing import Callable, Any
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# 동시에 1개만 처리하도록 제한 (1GB RAM 최적화)
processing_semaphore = asyncio.Semaphore(1)

# 최대 대기 시간 (초)
MAX_WAIT_TIME = 120  # 2분

# 대기열 크기 제한
MAX_QUEUE_SIZE = 10


class ProcessingLimiter:
    """
    이미지 처리 요청을 순차적으로 처리하는 제한자
    """

    def __init__(self):
        self.current_processing = 0
        self.queue_size = 0

    async def process_with_limit(
        self,
        func: Callable,
        *args,
        timeout: int = MAX_WAIT_TIME,
        **kwargs
    ) -> Any:
        """
        동시 처리 제한을 적용하여 함수 실행

        Args:
            func: 실행할 함수
            *args: 함수 인자
            timeout: 최대 대기 시간 (초)
            **kwargs: 함수 키워드 인자

        Returns:
            함수 실행 결과

        Raises:
            HTTPException: 대기 시간 초과 또는 대기열 초과
        """
        # 대기열 크기 확인
        if self.queue_size >= MAX_QUEUE_SIZE:
            logger.warning(f"대기열 초과 (현재: {self.queue_size}개)")
            raise HTTPException(
                status_code=503,
                detail=f"서버가 혼잡합니다. 잠시 후 다시 시도해주세요. (대기 중: {self.queue_size}개)"
            )

        self.queue_size += 1
        start_wait = time.time()

        try:
            # 타임아웃 적용
            async with asyncio.timeout(timeout):
                # 세마포어 획득 대기
                async with processing_semaphore:
                    wait_time = time.time() - start_wait

                    if wait_time > 1.0:  # 1초 이상 대기한 경우 로그
                        logger.info(f"처리 시작 (대기 시간: {wait_time:.2f}초)")

                    self.current_processing += 1
                    self.queue_size -= 1

                    start_process = time.time()

                    try:
                        # 함수가 코루틴인지 확인
                        if asyncio.iscoroutinefunction(func):
                            result = await func(*args, **kwargs)
                        else:
                            # 동기 함수는 쓰레드에서 실행
                            result = await asyncio.to_thread(func, *args, **kwargs)

                        process_time = time.time() - start_process
                        logger.info(f"처리 완료 (처리 시간: {process_time:.2f}초)")

                        return result
                    finally:
                        self.current_processing -= 1

        except asyncio.TimeoutError:
            self.queue_size -= 1
            logger.error(f"처리 대기 시간 초과 ({timeout}초)")
            raise HTTPException(
                status_code=503,
                detail=f"대기 시간 초과 ({timeout}초). 서버가 혼잡합니다."
            )
        except HTTPException:
            raise
        except Exception as e:
            self.queue_size -= 1
            logger.error(f"처리 중 오류: {str(e)}")
            raise

    def get_status(self) -> dict:
        """
        현재 처리 상태 반환

        Returns:
            dict: 처리 상태 정보
        """
        return {
            "processing": self.current_processing,
            "waiting": self.queue_size,
            "max_queue_size": MAX_QUEUE_SIZE
        }


# 전역 인스턴스
limiter = ProcessingLimiter()
