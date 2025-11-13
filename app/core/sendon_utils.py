"""
센드온(Sendon) API 호출 유틸리티
알림톡 발송을 위한 센드온 API 통신 로직
"""
import os
import logging
import requests
import base64
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

logger = logging.getLogger(__name__)

# 센드온 API 설정
SENDON_ID = os.getenv("SENDON_ID", "")
SENDON_API_KEY = os.getenv("SENDON_API_KEY", "")
SENDON_API_BASE_URL = "https://api.sendon.io"


class SendonAPIException(Exception):
    """센드온 API 호출 중 발생하는 예외"""
    def __init__(self, code: int, message: str, response_data: Optional[Dict] = None):
        self.code = code
        self.message = message
        self.response_data = response_data
        super().__init__(f"Sendon API Error [{code}]: {message}")


def send_alimtok(
    send_profile_id: str,
    template_id: str,
    to: list,
    reservation: Optional[Dict[str, Any]] = None,
    use_credit: bool = True,
    fallback: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    센드온 API를 통해 알림톡 메시지 발송

    Args:
        send_profile_id: 채널 ID (카카오 채널 관리자센터에서 등록한 채널 ID)
        template_id: 알림톡 템플릿 ID (사전 검수 승인된 템플릿 ID)
        to: 수신자 정보 목록 (최대 1,000명)
            - 변수 없는 경우: ["01011112222", "01011113333"]
            - 변수 있는 경우: [{"phone": "01011112222", "variables": {"#{고객명}": "홍길동"}}]
        reservation: 예약 발송 설정 (선택)
            - {"reservedAt": "2024-01-01T09:00:00+09:00"}
        use_credit: 크레딧 우선 사용 여부 (기본값: True)
        fallback: 대체문자 설정 (선택)
            - {"fallbackType": "NONE"} - 대체문자 미사용 (기본값)
            - {"fallbackType": "TEMPLATE"} - 템플릿에 설정된 대체문자 사용
            - {"fallbackType": "CUSTOM", "custom": {...}} - 직접 지정한 대체문자 사용

    Returns:
        센드온 API 응답 데이터

    Raises:
        SendonAPIException: API 호출 실패 시
    """
    if not SENDON_ID or not SENDON_API_KEY:
        raise SendonAPIException(
            code=500,
            message="SENDON_ID 또는 SENDON_API_KEY 환경 변수가 설정되지 않았습니다."
        )

    # API 엔드포인트
    url = f"{SENDON_API_BASE_URL}/v2/messages/kakao/alim-talk"

    # Basic 인증을 위한 base64 인코딩
    # 형식: base64(SENDON_ID:SENDON_API_KEY)
    credentials = f"{SENDON_ID}:{SENDON_API_KEY}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    # 요청 헤더
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/json"
    }

    # 요청 바디 구성
    payload = {
        "sendProfileId": send_profile_id,
        "templateId": template_id,
        "to": to,
        "useCredit": use_credit
    }

    # 선택적 파라미터 추가
    if reservation:
        payload["reservation"] = reservation

    if fallback:
        payload["fallback"] = fallback

    try:
        logger.info(f"알림톡 발송 요청: 템플릿ID={template_id}, 수신자 수={len(to)}")

        # API 호출
        response = requests.post(url, json=payload, headers=headers, timeout=30)

        # 응답 데이터 파싱
        response_data = response.json()

        # 센드온 API는 항상 HTTP 200으로 응답하므로, body의 code로 성공/실패 판단
        code = response_data.get("code", 500)
        message = response_data.get("message", "알 수 없는 오류")

        if code != 200:
            logger.error(f"알림톡 발송 실패: [{code}] {message}")
            raise SendonAPIException(
                code=code,
                message=message,
                response_data=response_data
            )

        logger.info(f"알림톡 발송 성공: {message}")
        return response_data

    except requests.exceptions.RequestException as e:
        logger.error(f"센드온 API 호출 중 네트워크 오류: {str(e)}")
        raise SendonAPIException(
            code=500,
            message=f"API 호출 중 네트워크 오류가 발생했습니다: {str(e)}"
        )
    except ValueError as e:
        logger.error(f"센드온 API 응답 파싱 오류: {str(e)}")
        raise SendonAPIException(
            code=500,
            message=f"API 응답 파싱 중 오류가 발생했습니다: {str(e)}"
        )


def validate_phone_number(phone: str) -> bool:
    """
    전화번호 유효성 검사

    Args:
        phone: 전화번호 (예: "01012345678")

    Returns:
        유효한 전화번호인 경우 True, 그렇지 않으면 False
    """
    # 기본 검증: 숫자만, 10-11자리
    if not phone.isdigit():
        return False

    if len(phone) not in [10, 11]:
        return False

    # 휴대폰 번호 형식: 010, 011, 016, 017, 018, 019로 시작
    if phone.startswith("01"):
        return True

    return False
