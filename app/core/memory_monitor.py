"""
메모리 사용량 모니터링 유틸리티
"""
import logging
from typing import Dict

logger = logging.getLogger(__name__)

# psutil을 선택적으로 import (서버 환경에서 없을 수 있음)
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil을 사용할 수 없습니다. 메모리 모니터링이 비활성화됩니다.")


def get_memory_usage() -> Dict[str, float]:
    """
    현재 프로세스의 메모리 사용량 반환

    Returns:
        메모리 사용량 정보 딕셔너리
        {
            "rss_mb": RSS 메모리 (MB),
            "vms_mb": 가상 메모리 (MB),
            "percent": 시스템 메모리 사용률 (%)
        }
    """
    if not PSUTIL_AVAILABLE:
        return {"rss_mb": 0.0, "vms_mb": 0.0, "percent": 0.0}

    process = psutil.Process()
    memory_info = process.memory_info()

    return {
        "rss_mb": round(memory_info.rss / 1024 / 1024, 2),  # Resident Set Size (실제 물리 메모리)
        "vms_mb": round(memory_info.vms / 1024 / 1024, 2),  # Virtual Memory Size
        "percent": round(process.memory_percent(), 2)
    }


def log_memory_usage(prefix: str = ""):
    """
    현재 메모리 사용량을 로그에 출력

    Args:
        prefix: 로그 메시지 접두사
    """
    if not PSUTIL_AVAILABLE:
        logger.debug(f"{prefix}메모리 모니터링 비활성화 (psutil 없음)")
        return {"rss_mb": 0.0, "vms_mb": 0.0, "percent": 0.0}

    memory = get_memory_usage()
    message = f"{prefix}메모리 사용량 - RSS: {memory['rss_mb']}MB, VMS: {memory['vms_mb']}MB, 사용률: {memory['percent']}%"
    logger.info(message)
    return memory


def get_system_memory() -> Dict[str, float]:
    """
    시스템 전체 메모리 정보 반환

    Returns:
        시스템 메모리 정보 딕셔너리
    """
    if not PSUTIL_AVAILABLE:
        return {"total_mb": 0.0, "available_mb": 0.0, "used_mb": 0.0, "percent": 0.0}

    mem = psutil.virtual_memory()

    return {
        "total_mb": round(mem.total / 1024 / 1024, 2),
        "available_mb": round(mem.available / 1024 / 1024, 2),
        "used_mb": round(mem.used / 1024 / 1024, 2),
        "percent": mem.percent
    }


def log_system_memory():
    """
    시스템 전체 메모리 정보를 로그에 출력
    """
    if not PSUTIL_AVAILABLE:
        logger.debug("메모리 모니터링 비활성화 (psutil 없음)")
        return {"total_mb": 0.0, "available_mb": 0.0, "used_mb": 0.0, "percent": 0.0}

    memory = get_system_memory()
    message = (
        f"시스템 메모리 - "
        f"전체: {memory['total_mb']}MB, "
        f"사용: {memory['used_mb']}MB, "
        f"가용: {memory['available_mb']}MB, "
        f"사용률: {memory['percent']}%"
    )
    logger.info(message)
    return memory
