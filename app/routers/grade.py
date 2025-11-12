"""
OMR 채점 API 엔드포인트
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional, List
import logging
import json
import gc

from app.core.image_utils import bytes_to_cv2, align_scan_to_template
from app.core.omr_utils import detect_bubbles, grade_omr_sheet
from app.core.memory_monitor import log_memory_usage
from pathlib import Path

# 로거 설정
logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter(
    prefix="/api/grade",
    tags=["grading"]
)

# 기본 템플릿 이미지 경로
DEFAULT_TEMPLATE_PATH = Path(__file__).parent.parent.parent / "omr_card.jpg"


@router.get("/")
async def health_check():
    """
    채점 API 상태 확인
    """
    return {
        "status": "ok",
        "service": "OMR Grading API",
        "total_questions": 45,
        "options_per_question": 5
    }


@router.post("/detect")
async def detect_answers(
    scan: UploadFile = File(..., description="스캔된 시험지 이미지"),
    template: Optional[UploadFile] = File(None, description="기준 템플릿 이미지"),
    method: str = Form("sift", description="정렬 방식: 'sift' 또는 'contour'"),
    threshold: float = Form(0.35, description="마킹 판단 임계값 (0.0~1.0)")
):
    """
    OMR 답안지에서 마킹된 답안만 검출 (채점하지 않음)

    **Parameters:**
    - **scan**: 스캔된 시험지 이미지 (필수)
    - **template**: 기준 템플릿 (선택사항, 미제공 시 omr_card.jpg 사용)
    - **method**: 정렬 방식 ('sift' 또는 'contour', 기본값: 'sift')
    - **threshold**: 마킹 판단 임계값 (기본값: 0.35, 낮을수록 민감)

    **Returns:**
    - JSON 형식의 검출 결과
    """
    scan_bytes = None
    template_bytes = None
    aligned_bytes = None
    aligned_img = None

    try:
        # 스캔 이미지 읽기
        scan_bytes = await scan.read()

        # 템플릿 이미지 읽기
        if template:
            template_bytes = await template.read()
        elif method == "sift":
            if not DEFAULT_TEMPLATE_PATH.exists():
                raise HTTPException(
                    status_code=500,
                    detail=f"기본 템플릿 파일을 찾을 수 없습니다: {DEFAULT_TEMPLATE_PATH}"
                )
            template_bytes = DEFAULT_TEMPLATE_PATH.read_bytes()

        # 이미지 정렬
        logger.info(f"이미지 정렬 시작 - 방식: {method}")
        aligned_bytes, metadata = align_scan_to_template(
            scan_bytes=scan_bytes,
            template_bytes=template_bytes,
            method=method,
            enhance=True
        )

        if not metadata.get("success"):
            raise HTTPException(
                status_code=400,
                detail="이미지 정렬에 실패했습니다"
            )

        # OpenCV 이미지로 변환
        aligned_img = bytes_to_cv2(aligned_bytes)

        # 답안 검출
        logger.info(f"답안 검출 시작 - 임계값: {threshold}")
        detected_answers = detect_bubbles(aligned_img, threshold)

        # 응답 생성
        answered_count = sum(1 for v in detected_answers.values() if v is not None)
        blank_count = sum(1 for v in detected_answers.values() if v is None)

        return {
            "success": True,
            "message": "답안 검출 완료",
            "alignment": metadata,
            "detected_answers": detected_answers,
            "statistics": {
                "total_questions": 45,
                "answered": answered_count,
                "blank": blank_count
            }
        }

    except ValueError as e:
        logger.error(f"입력 검증 오류: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"답안 검출 중 오류 발생: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"답안 검출 중 오류가 발생했습니다: {str(e)}"
        )
    finally:
        # 메모리 정리
        if scan_bytes is not None:
            del scan_bytes
        if template_bytes is not None:
            del template_bytes
        if aligned_bytes is not None:
            del aligned_bytes
        if aligned_img is not None:
            del aligned_img


@router.post("/")
async def grade_exam(
    scan: UploadFile = File(..., description="스캔된 시험지 이미지"),
    answer_key: str = Form(..., description="정답 리스트 JSON 배열 (45개, 1-indexed)"),
    template: Optional[UploadFile] = File(None, description="기준 템플릿 이미지"),
    method: str = Form("sift", description="정렬 방식: 'sift' 또는 'contour'"),
    threshold: float = Form(0.35, description="마킹 판단 임계값 (0.0~1.0)"),
    score_per_question: float = Form(1.0, description="문제당 배점")
):
    """
    OMR 답안지 자동 채점

    **Parameters:**
    - **scan**: 스캔된 시험지 이미지 (필수)
    - **answer_key**: 정답 리스트 JSON 배열 (예: "[1,2,3,4,5,1,2,3,...]" - 45개)
    - **template**: 기준 템플릿 (선택사항)
    - **method**: 정렬 방식 ('sift' 또는 'contour', 기본값: 'sift')
    - **threshold**: 마킹 판단 임계값 (기본값: 0.35)
    - **score_per_question**: 문제당 배점 (기본값: 1.0)

    **Returns:**
    - JSON 형식의 채점 결과
    """
    scan_bytes = None
    template_bytes = None
    aligned_bytes = None
    aligned_img = None

    try:
        # 정답 파싱
        try:
            answer_key_list = json.loads(answer_key)
            if not isinstance(answer_key_list, list) or len(answer_key_list) != 45:
                raise ValueError("정답은 45개의 숫자 배열이어야 합니다")
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400,
                detail="answer_key는 유효한 JSON 배열이어야 합니다 (예: [1,2,3,...])"
            )

        # 스캔 이미지 읽기
        scan_bytes = await scan.read()

        # 템플릿 이미지 읽기
        if template:
            template_bytes = await template.read()
        elif method == "sift":
            if not DEFAULT_TEMPLATE_PATH.exists():
                raise HTTPException(
                    status_code=500,
                    detail=f"기본 템플릿 파일을 찾을 수 없습니다: {DEFAULT_TEMPLATE_PATH}"
                )
            template_bytes = DEFAULT_TEMPLATE_PATH.read_bytes()

        # 이미지 정렬
        logger.info(f"이미지 정렬 시작 - 방식: {method}")
        aligned_bytes, metadata = align_scan_to_template(
            scan_bytes=scan_bytes,
            template_bytes=template_bytes,
            method=method,
            enhance=True
        )

        if not metadata.get("success"):
            raise HTTPException(
                status_code=400,
                detail="이미지 정렬에 실패했습니다"
            )

        # OpenCV 이미지로 변환
        aligned_img = bytes_to_cv2(aligned_bytes)

        # 채점
        logger.info(f"채점 시작 - 임계값: {threshold}, 배점: {score_per_question}")
        grading_result = grade_omr_sheet(
            aligned_img,
            answer_key_list,
            threshold,
            score_per_question
        )

        return {
            "success": True,
            "message": "채점 완료",
            "alignment": metadata,
            "grading": grading_result
        }

    except ValueError as e:
        logger.error(f"입력 검증 오류: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"채점 중 오류 발생: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"채점 중 오류가 발생했습니다: {str(e)}"
        )
    finally:
        # 메모리 정리
        if scan_bytes is not None:
            del scan_bytes
        if template_bytes is not None:
            del template_bytes
        if aligned_bytes is not None:
            del aligned_bytes
        if aligned_img is not None:
            del aligned_img


@router.post("/batch")
async def grade_exams_batch(
    scans: List[UploadFile] = File(..., description="스캔된 시험지 이미지들"),
    answer_key: str = Form(..., description="정답 리스트 JSON 배열 (45개)"),
    template: Optional[UploadFile] = File(None, description="기준 템플릿 이미지"),
    method: str = Form("sift", description="정렬 방식"),
    threshold: float = Form(0.35, description="마킹 판단 임계값"),
    score_per_question: float = Form(1.0, description="문제당 배점")
):
    """
    여러 OMR 답안지를 배치로 채점 (최대 100장)

    **Parameters:**
    - **scans**: 스캔된 시험지 이미지들 (최대 100개)
    - **answer_key**: 정답 리스트 JSON 배열
    - **template**: 기준 템플릿 (선택사항)
    - **method**: 정렬 방식
    - **threshold**: 마킹 판단 임계값
    - **score_per_question**: 문제당 배점

    **Returns:**
    - JSON 형식의 배치 채점 결과

    **Notes:**
    - 메모리 효율을 위해 각 이미지는 순차적으로 처리되며 처리 후 즉시 메모리에서 해제됩니다
    - 결과에는 채점 정보만 포함되며 이미지 바이트는 저장되지 않습니다
    """
    try:
        # 배치 크기 제한 (메모리 보호)
        MAX_BATCH_SIZE = 100
        if len(scans) > MAX_BATCH_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"배치 크기는 최대 {MAX_BATCH_SIZE}개까지 가능합니다 (현재: {len(scans)}개)"
            )
        # 정답 파싱
        try:
            answer_key_list = json.loads(answer_key)
            if not isinstance(answer_key_list, list) or len(answer_key_list) != 45:
                raise ValueError("정답은 45개의 숫자 배열이어야 합니다")
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400,
                detail="answer_key는 유효한 JSON 배열이어야 합니다"
            )

        # 템플릿 이미지 읽기
        template_bytes = None
        if template:
            template_bytes = await template.read()
        elif method == "sift":
            if not DEFAULT_TEMPLATE_PATH.exists():
                raise HTTPException(
                    status_code=500,
                    detail=f"기본 템플릿 파일을 찾을 수 없습니다: {DEFAULT_TEMPLATE_PATH}"
                )
            template_bytes = DEFAULT_TEMPLATE_PATH.read_bytes()

        # 배치 시작 전 메모리 상태
        log_memory_usage("[배치 채점 시작] ")

        results = []
        for idx, scan in enumerate(scans):
            scan_bytes = None
            aligned_bytes = None
            aligned_img = None

            try:
                # 스캔 이미지 읽기
                scan_bytes = await scan.read()

                # 이미지 정렬
                aligned_bytes, metadata = align_scan_to_template(
                    scan_bytes=scan_bytes,
                    template_bytes=template_bytes,
                    method=method,
                    enhance=True
                )

                if not metadata.get("success"):
                    results.append({
                        "index": idx,
                        "filename": scan.filename,
                        "success": False,
                        "error": "이미지 정렬 실패"
                    })
                    continue

                # OpenCV 이미지로 변환
                aligned_img = bytes_to_cv2(aligned_bytes)

                # 채점 수행
                grading_result = grade_omr_sheet(
                    aligned_img,
                    answer_key_list,
                    threshold,
                    score_per_question
                )

                # 결과 저장 (이미지 바이트는 제외, 채점 결과만 저장)
                results.append({
                    "index": idx,
                    "filename": scan.filename,
                    "success": True,
                    "grading": grading_result
                })

                logger.info(f"배치 [{idx + 1}/{len(scans)}] {scan.filename} 채점 완료 "
                           f"- 점수: {grading_result['total_score']}/{grading_result['max_score']}")

            except Exception as e:
                logger.error(f"배치 [{idx + 1}/{len(scans)}] {scan.filename} 처리 실패: {str(e)}")
                results.append({
                    "index": idx,
                    "filename": scan.filename,
                    "success": False,
                    "error": str(e)
                })

            finally:
                # 메모리 효율: 각 이미지 처리 후 즉시 큰 변수 해제
                if scan_bytes is not None:
                    del scan_bytes
                if aligned_bytes is not None:
                    del aligned_bytes
                if aligned_img is not None:
                    del aligned_img

                # 10장마다 가비지 컬렉션 수행 (메모리 회수)
                if (idx + 1) % 10 == 0:
                    gc.collect()
                    log_memory_usage(f"[배치 채점 진행 {idx + 1}/{len(scans)}] ")

        # 최종 메모리 정리
        gc.collect()
        log_memory_usage("[배치 채점 완료] ")
        logger.info(f"배치 채점 완료 - 최종 메모리 정리 수행")

        # 통계 계산
        successful = sum(1 for r in results if r.get("success", False))
        failed = len(results) - successful

        # 평균 점수 계산
        if successful > 0:
            total_scores = [r["grading"]["total_score"] for r in results if r.get("success", False)]
            average_score = sum(total_scores) / len(total_scores)
        else:
            average_score = 0.0

        return {
            "success": True,
            "total": len(results),
            "successful": successful,
            "failed": failed,
            "average_score": round(average_score, 2),
            "results": results
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"배치 채점 중 오류 발생: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"배치 채점 중 오류가 발생했습니다: {str(e)}"
        )
