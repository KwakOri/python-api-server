"""
이미지 정렬 API 엔드포인트
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import Response
from typing import Optional
import logging
from pathlib import Path

from app.core.image_utils import align_scan_to_template

# 로거 설정
logger = logging.getLogger(__name__)

# 기본 템플릿 이미지 경로
DEFAULT_TEMPLATE_PATH = Path(__file__).parent.parent.parent / "omr_card.jpg"

# 라우터 생성
router = APIRouter(
    prefix="/api/align",
    tags=["alignment"]
)


@router.get("/")
async def health_check():
    """
    정렬 API 상태 확인
    """
    return {
        "status": "ok",
        "service": "Image Alignment API",
        "methods": ["sift", "contour"]
    }


@router.post("/")
async def align_image(
    scan: UploadFile = File(..., description="스캔된 시험지 이미지"),
    template: Optional[UploadFile] = File(None, description="기준 템플릿 이미지 (SIFT 방식에 필요)"),
    method: str = Form("sift", description="정렬 방식: 'sift' 또는 'contour'"),
    enhance: bool = Form(True, description="이미지 품질 개선 여부"),
    return_image: bool = Form(False, description="정렬된 이미지를 바로 반환할지 여부")
):
    """
    스캔된 시험지 이미지를 정렬

    **Parameters:**
    - **scan**: 스캔된 시험지 이미지 파일 (필수)
    - **template**: 기준 템플릿 이미지 파일 (선택사항, 미제공 시 omr_card.jpg 사용)
    - **method**: 정렬 방식 ('sift' 또는 'contour', 기본값: 'sift')
    - **enhance**: 이미지 품질 개선 여부 (기본값: true)
    - **return_image**: true이면 이미지 바이너리를 반환, false이면 JSON 메타데이터 반환

    **Returns:**
    - return_image=false: JSON 형식의 메타데이터
    - return_image=true: PNG 이미지 바이너리

    **Methods:**
    - **sift**: SIFT + FLANN + Homography (높은 정확도, 템플릿 자동 사용)
    - **contour**: 외곽선 검출 + 투시 변환 (빠른 속도, 템플릿 불필요)
    """
    try:
        # 파일 검증
        if not scan.content_type or not scan.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail="scan 파라미터는 이미지 파일이어야 합니다"
            )

        # 스캔 이미지 읽기
        scan_bytes = await scan.read()

        # 템플릿 이미지 읽기
        template_bytes = None
        if template:
            # 사용자가 템플릿을 제공한 경우
            if not template.content_type or not template.content_type.startswith("image/"):
                raise HTTPException(
                    status_code=400,
                    detail="template 파라미터는 이미지 파일이어야 합니다"
                )
            template_bytes = await template.read()
        elif method == "sift":
            # SIFT 방식이고 템플릿이 없으면 기본 템플릿(omr_card.jpg) 사용
            if not DEFAULT_TEMPLATE_PATH.exists():
                raise HTTPException(
                    status_code=500,
                    detail=f"기본 템플릿 파일을 찾을 수 없습니다: {DEFAULT_TEMPLATE_PATH}"
                )
            template_bytes = DEFAULT_TEMPLATE_PATH.read_bytes()
            logger.info(f"기본 템플릿 사용: {DEFAULT_TEMPLATE_PATH}")

        # 정렬 방식 검증
        if method not in ["sift", "contour"]:
            raise HTTPException(
                status_code=400,
                detail="method는 'sift' 또는 'contour'여야 합니다"
            )

        # 이미지 정렬 수행
        logger.info(f"이미지 정렬 시작 - 방식: {method}, 품질개선: {enhance}")
        aligned_bytes, metadata = align_scan_to_template(
            scan_bytes=scan_bytes,
            template_bytes=template_bytes,
            method=method,
            enhance=enhance
        )

        # 결과 반환
        if return_image:
            # 이미지 바이너리 반환
            return Response(
                content=aligned_bytes,
                media_type="image/png",
                headers={
                    "X-Alignment-Success": str(metadata.get("success", False)),
                    "X-Alignment-Method": metadata.get("method", "unknown"),
                    "X-Image-Width": str(metadata.get("width", 0)),
                    "X-Image-Height": str(metadata.get("height", 0))
                }
            )
        else:
            # JSON 메타데이터 반환
            return {
                "success": True,
                "message": "이미지 정렬 완료" if metadata.get("success") else "정렬 실패",
                "metadata": metadata,
                "note": "정렬된 이미지를 받으려면 return_image=true로 요청하세요"
            }

    except ValueError as e:
        logger.error(f"입력 검증 오류: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"이미지 정렬 중 오류 발생: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"이미지 정렬 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/batch")
async def align_images_batch(
    scans: list[UploadFile] = File(..., description="스캔된 시험지 이미지들"),
    template: Optional[UploadFile] = File(None, description="기준 템플릿 이미지"),
    method: str = Form("sift", description="정렬 방식"),
    enhance: bool = Form(True, description="이미지 품질 개선 여부")
):
    """
    여러 스캔 이미지를 배치로 정렬

    **Parameters:**
    - **scans**: 스캔된 시험지 이미지 파일들 (여러 개)
    - **template**: 기준 템플릿 이미지 파일 (선택사항, 미제공 시 omr_card.jpg 사용)
    - **method**: 정렬 방식 ('sift' 또는 'contour', 기본값: 'sift')
    - **enhance**: 이미지 품질 개선 여부

    **Returns:**
    - JSON 형식의 배치 처리 결과
    """
    try:
        # 템플릿 이미지 읽기
        template_bytes = None
        if template:
            # 사용자가 템플릿을 제공한 경우
            template_bytes = await template.read()
        elif method == "sift":
            # SIFT 방식이고 템플릿이 없으면 기본 템플릿(omr_card.jpg) 사용
            if not DEFAULT_TEMPLATE_PATH.exists():
                raise HTTPException(
                    status_code=500,
                    detail=f"기본 템플릿 파일을 찾을 수 없습니다: {DEFAULT_TEMPLATE_PATH}"
                )
            template_bytes = DEFAULT_TEMPLATE_PATH.read_bytes()
            logger.info(f"배치 처리에서 기본 템플릿 사용: {DEFAULT_TEMPLATE_PATH}")

        results = []
        for idx, scan in enumerate(scans):
            try:
                scan_bytes = await scan.read()
                aligned_bytes, metadata = align_scan_to_template(
                    scan_bytes=scan_bytes,
                    template_bytes=template_bytes,
                    method=method,
                    enhance=enhance
                )

                results.append({
                    "index": idx,
                    "filename": scan.filename,
                    "success": metadata.get("success", False),
                    "metadata": metadata
                })

                logger.info(f"배치 [{idx + 1}/{len(scans)}] {scan.filename} 처리 완료")

            except Exception as e:
                logger.error(f"배치 [{idx + 1}/{len(scans)}] {scan.filename} 처리 실패: {str(e)}")
                results.append({
                    "index": idx,
                    "filename": scan.filename,
                    "success": False,
                    "error": str(e)
                })

        # 통계 계산
        successful = sum(1 for r in results if r.get("success", False))
        failed = len(results) - successful

        return {
            "success": True,
            "total": len(results),
            "successful": successful,
            "failed": failed,
            "results": results
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"배치 처리 중 오류 발생: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"배치 처리 중 오류가 발생했습니다: {str(e)}"
        )
