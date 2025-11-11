"""
로깅 설정 및 헬스체크 필터
"""
import logging


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
