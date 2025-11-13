"""
알림톡 발송 API 라우터
센드온(Sendon) API를 통한 카카오 알림톡 메시지 발송
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Union, Dict, Any
import logging

from app.core.sendon_utils import send_alimtok, validate_phone_number, SendonAPIException

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/alimtok",
    tags=["알림톡"],
    responses={404: {"description": "Not found"}}
)


# =====================================
# Pydantic 모델 정의
# =====================================

class RecipientSimple(BaseModel):
    """수신자 정보 (변수 없는 경우)"""
    phone: str = Field(..., description="수신자 전화번호 (예: 01012345678)")

    @validator('phone')
    def validate_phone(cls, v):
        if not validate_phone_number(v):
            raise ValueError('올바른 전화번호 형식이 아닙니다 (예: 01012345678)')
        return v


class RecipientWithVariables(BaseModel):
    """수신자 정보 (변수 있는 경우)"""
    phone: str = Field(..., description="수신자 전화번호 (예: 01012345678)")
    variables: Dict[str, str] = Field(
        ...,
        description="템플릿 변수 (예: {'#{고객명}': '홍길동', '#{날짜}': '2024-01-01'})"
    )

    @validator('phone')
    def validate_phone(cls, v):
        if not validate_phone_number(v):
            raise ValueError('올바른 전화번호 형식이 아닙니다 (예: 01012345678)')
        return v


class ReservationSettings(BaseModel):
    """예약 발송 설정"""
    reserved_at: str = Field(
        ...,
        alias="reservedAt",
        description="예약 발송 시간 (ISO 8601 형식, 예: 2024-01-01T09:00:00+09:00)"
    )


class CustomFallback(BaseModel):
    """대체문자 상세 설정 (CUSTOM 타입용)"""
    type: str = Field(
        ...,
        description="대체문자 유형 (SMS, LMS, MMS)"
    )
    sender_number: str = Field(
        ...,
        alias="senderNumber",
        description="발신번호 (센드온에 등록된 번호)"
    )
    message: str = Field(
        ...,
        description="메시지 내용"
    )
    is_ad: bool = Field(
        ...,
        alias="isAd",
        description="광고성 메시지 여부"
    )
    title: Optional[str] = Field(
        None,
        description="메시지 제목 (LMS/MMS의 경우 선택)"
    )
    images: Optional[List[str]] = Field(
        None,
        description="이미지 ID 배열 (MMS의 경우 필수, 최대 3개)"
    )

    @validator('type')
    def validate_type(cls, v):
        if v not in ['SMS', 'LMS', 'MMS']:
            raise ValueError('type은 SMS, LMS, MMS 중 하나여야 합니다')
        return v

    @validator('images')
    def validate_images(cls, v, values):
        if values.get('type') == 'MMS' and not v:
            raise ValueError('MMS 타입의 경우 images 필드가 필수입니다')
        if v and len(v) > 3:
            raise ValueError('이미지는 최대 3개까지 첨부 가능합니다')
        return v


class FallbackSettings(BaseModel):
    """대체문자 설정"""
    fallback_type: str = Field(
        ...,
        alias="fallbackType",
        description="대체발송 유형 (NONE: 미사용, TEMPLATE: 템플릿 사용, CUSTOM: 직접 지정)"
    )
    custom: Optional[CustomFallback] = Field(
        None,
        description="대체문자 상세 설정 (CUSTOM 타입의 경우 필수)"
    )

    @validator('fallback_type')
    def validate_fallback_type(cls, v):
        if v not in ['NONE', 'TEMPLATE', 'CUSTOM']:
            raise ValueError('fallbackType은 NONE, TEMPLATE, CUSTOM 중 하나여야 합니다')
        return v

    @validator('custom')
    def validate_custom(cls, v, values):
        if values.get('fallback_type') == 'CUSTOM' and not v:
            raise ValueError('CUSTOM 타입의 경우 custom 필드가 필수입니다')
        return v


class AlimtokSendRequest(BaseModel):
    """알림톡 발송 요청"""
    send_profile_id: str = Field(
        ...,
        alias="sendProfileId",
        description="채널 ID (카카오 채널 관리자센터에서 등록한 채널 ID)"
    )
    template_id: str = Field(
        ...,
        alias="templateId",
        description="알림톡 템플릿 ID (사전 검수 승인된 템플릿 ID)"
    )
    to: List[Union[str, RecipientWithVariables]] = Field(
        ...,
        min_items=1,
        max_items=1000,
        description="수신자 정보 목록 (최대 1,000명). 변수 없으면 전화번호 문자열 배열, 변수 있으면 객체 배열"
    )
    reservation: Optional[ReservationSettings] = Field(
        None,
        description="예약 발송 설정 (선택, 미입력시 즉시 발송)"
    )
    use_credit: bool = Field(
        True,
        alias="useCredit",
        description="크레딧 우선 사용 여부 (기본값: true)"
    )
    fallback: Optional[FallbackSettings] = Field(
        None,
        description="대체문자 설정 (선택)"
    )

    class Config:
        populate_by_name = True

    @validator('to')
    def validate_recipients(cls, v):
        # 전화번호 문자열인 경우 유효성 검사
        for item in v:
            if isinstance(item, str):
                if not validate_phone_number(item):
                    raise ValueError(f'올바른 전화번호 형식이 아닙니다: {item}')
        return v


class AlimtokSendResponse(BaseModel):
    """알림톡 발송 응답"""
    code: int = Field(..., description="응답 코드 (200: 성공)")
    message: str = Field(..., description="응답 메시지")
    data: Optional[Dict[str, Any]] = Field(None, description="발송 결과 데이터 (그룹 ID 등)")


# =====================================
# API 엔드포인트
# =====================================

@router.post(
    "/send",
    response_model=AlimtokSendResponse,
    status_code=status.HTTP_200_OK,
    summary="알림톡 메시지 발송",
    description="""
    카카오 채널을 통해 알림톡 메시지를 발송합니다.

    ## 사전 준비사항
    - 카카오 비즈니스 채널 생성 및 연동
    - 알림톡 템플릿 등록 및 승인 완료
    - 센드온 API 키 발급 및 설정

    ## 수신자 정보 형식
    - **변수 없는 경우**: `["01011112222", "01011113333"]`
    - **변수 있는 경우**: `[{"phone": "01011112222", "variables": {"#{고객명}": "홍길동"}}]`

    ## 대체문자 설정
    - **NONE**: 대체문자 미사용 (기본값)
    - **TEMPLATE**: 템플릿에 설정된 대체문자 사용 (알림톡만 가능)
    - **CUSTOM**: 직접 지정한 대체문자 사용 (SMS/LMS/MMS)

    ## 주의사항
    - 센드온 API는 HTTP 200으로 항상 응답합니다
    - 실제 성공/실패는 응답 body의 `code` 필드로 판단하세요
    - 최대 1,000명까지 동시 발송 가능
    """
)
async def send_alimtok_message(request: AlimtokSendRequest):
    """
    알림톡 메시지 발송

    정보성 메시지를 사전 승인된 템플릿으로 발송합니다.
    """
    try:
        # 수신자 정보 변환
        recipients = []
        for recipient in request.to:
            if isinstance(recipient, str):
                recipients.append(recipient)
            else:
                # RecipientWithVariables 객체를 dict로 변환
                recipients.append({
                    "phone": recipient.phone,
                    "variables": recipient.variables
                })

        # 예약 설정 변환
        reservation = None
        if request.reservation:
            reservation = {"reservedAt": request.reservation.reserved_at}

        # 대체문자 설정 변환
        fallback = None
        if request.fallback:
            fallback = {"fallbackType": request.fallback.fallback_type}
            if request.fallback.custom:
                custom = request.fallback.custom
                fallback["custom"] = {
                    "type": custom.type,
                    "senderNumber": custom.sender_number,
                    "message": custom.message,
                    "isAd": custom.is_ad
                }
                if custom.title:
                    fallback["custom"]["title"] = custom.title
                if custom.images:
                    fallback["custom"]["images"] = custom.images

        # 센드온 API 호출
        result = send_alimtok(
            send_profile_id=request.send_profile_id,
            template_id=request.template_id,
            to=recipients,
            reservation=reservation,
            use_credit=request.use_credit,
            fallback=fallback
        )

        return AlimtokSendResponse(**result)

    except SendonAPIException as e:
        # 센드온 API 오류
        logger.error(f"센드온 API 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": e.code,
                "message": e.message,
                "data": e.response_data
            }
        )
    except Exception as e:
        # 기타 오류
        logger.error(f"알림톡 발송 중 오류 발생: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": 500,
                "message": f"서버 내부 오류가 발생했습니다: {str(e)}"
            }
        )


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="알림톡 서비스 상태 확인"
)
async def health_check():
    """
    알림톡 서비스의 상태를 확인합니다.
    """
    import os
    sendon_id = os.getenv("SENDON_ID", "")
    sendon_api_key = os.getenv("SENDON_API_KEY", "")

    return {
        "status": "healthy",
        "service": "alimtok",
        "sendon_id_configured": bool(sendon_id),
        "sendon_api_key_configured": bool(sendon_api_key),
        "auth_configured": bool(sendon_id and sendon_api_key)
    }
