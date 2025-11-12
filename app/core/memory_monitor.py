"""
메모리 사용량 모니터링 유틸리티
"""
import psutil
import logging
from typing import Dict

logger = logging.getLogger(__name__)


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
