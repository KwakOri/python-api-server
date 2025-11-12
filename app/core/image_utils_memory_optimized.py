"""
메모리 최적화된 이미지 정렬 함수
512MB 제한 환경에서 동작하도록 설계
"""
import cv2
import numpy as np
import gc
from typing import Tuple, Optional
import logging
from app.core.memory_optimizer import (
    downsample_for_alignment,
    upsample_with_homography,
    aggressive_cleanup,
    get_memory_efficient_sift_params,
    calculate_image_memory
)

logger = logging.getLogger(__name__)


def align_with_sift_memory_optimized(
    scan_img: np.ndarray,
    template_img: np.ndarray,
    ratio_threshold: float = 0.7,
    min_good_matches: int = 10,
    max_memory_mb: float = 10.0
) -> Tuple[Optional[np.ndarray], int]:
    """
    메모리 최적화된 SIFT 정렬
    다운샘플 → 정렬 → 업샘플 전략 사용

    Args:
        scan_img: 스캔된 이미지
        template_img: 기준 템플릿 이미지
        ratio_threshold: Lowe's ratio test 임계값
        min_good_matches: 최소 유효 매칭 수
        max_memory_mb: 이미지당 최대 메모리 (MB)

    Returns:
        (정렬된 이미지, 매칭 개수) 튜플
    """
    original_scan = scan_img.copy()
    original_template = template_img.copy()

    try:
        # 1. 메모리 계산
        scan_memory = calculate_image_memory(scan_img)
        template_memory = calculate_image_memory(template_img)
        logger.info(f"원본 메모리: 스캔={scan_memory:.2f}MB, 템플릿={template_memory:.2f}MB")

        # 2. 이미지 크기에 따른 최적 파라미터
        params = get_memory_efficient_sift_params(scan_img.shape[:2][::-1])
        logger.info(f"SIFT 파라미터: {params['description']}")

        # 3. 정렬용 다운샘플 (메모리 절약)
        downsample_size = params['downsample_size']
        scan_small, scan_scale = downsample_for_alignment(scan_img, downsample_size)
        template_small, template_scale = downsample_for_alignment(template_img, downsample_size)

        # 원본 이미지 임시 삭제 (메모리 절약)
        del scan_img
        del template_img
        gc.collect()

        # 4. 그레이스케일 변환
        gray_scan = cv2.cvtColor(scan_small, cv2.COLOR_BGR2GRAY)
        gray_template = cv2.cvtColor(template_small, cv2.COLOR_BGR2GRAY)

        # 5. SIFT 특징점 검출
        sift = cv2.SIFT_create(nfeatures=params['nfeatures'])
        kp1, des1 = sift.detectAndCompute(gray_scan, None)
        kp2, des2 = sift.detectAndCompute(gray_template, None)

        # 그레이스케일 이미지 삭제
        del gray_scan
        del gray_template
        gc.collect()

        if des1 is None or des2 is None:
            logger.warning("SIFT 특징점 검출 실패")
            return None, 0

        logger.info(f"SIFT 특징점: 스캔={len(kp1)}, 템플릿={len(kp2)}")

        # 6. FLANN 매칭
        FLANN_INDEX_KDTREE = 1
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=50)
        flann = cv2.FlannBasedMatcher(index_params, search_params)

        matches = flann.knnMatch(des1, des2, k=2)

        # 디스크립터 삭제
        del des1
        del des2
        gc.collect()

        # 7. 좋은 매칭 선택
        good_matches = []
        for match_pair in matches:
            if len(match_pair) == 2:
                m, n = match_pair
                if m.distance < ratio_threshold * n.distance:
                    good_matches.append(m)

        del matches
        gc.collect()

        if len(good_matches) < min_good_matches:
            logger.warning(f"매칭 수 부족: {len(good_matches)} < {min_good_matches}")
            return None, len(good_matches)

        logger.info(f"좋은 매칭 수: {len(good_matches)}")

        # 8. Homography 계산 (다운샘플된 이미지 기준)
        src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

        del kp1
        del kp2
        del good_matches
        gc.collect()

        M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

        del src_pts
        del dst_pts
        gc.collect()

        if M is None:
            logger.warning("Homography 계산 실패")
            return None, 0

        # 9. 다운샘플된 이미지 삭제
        del scan_small
        del template_small
        gc.collect()

        # 10. 원본 크기로 업샘플 (Homography 스케일 조정)
        h, w = original_template.shape[:2]
        target_shape = (w, h)

        aligned = upsample_with_homography(
            original_scan,
            M,
            target_shape,
            scan_scale
        )

        del original_scan
        del original_template
        gc.collect()

        aligned_memory = calculate_image_memory(aligned)
        logger.info(f"정렬 완료: {aligned_memory:.2f}MB")

        match_count = int(np.sum(mask)) if mask is not None else 0

        return aligned, match_count

    except Exception as e:
        logger.error(f"메모리 최적화 정렬 중 오류: {str(e)}")
        aggressive_cleanup()
        return None, 0


def align_scan_to_template_memory_optimized(
    scan_bytes: bytes,
    template_bytes: Optional[bytes] = None,
    method: str = "sift",
    enhance: bool = True,
    max_dimension: int = 1000  # 기본값을 1000px로 낮춤
) -> Tuple[bytes, dict]:
    """
    메모리 최적화된 이미지 정렬 (통합 함수)

    Args:
        scan_bytes: 스캔 이미지 바이트
        template_bytes: 템플릿 이미지 바이트
        method: 정렬 방식 ("sift" 또는 "contour")
        enhance: 이미지 품질 개선 여부
        max_dimension: 최대 이미지 크기 (px)

    Returns:
        (정렬된 이미지 바이트, 메타데이터)
    """
    from app.core.image_utils import bytes_to_cv2, cv2_to_bytes, enhance_image

    scan_img = None
    template_img = None
    aligned_img = None

    try:
        # 1. 이미지 로드 (크기 제한)
        scan_img = bytes_to_cv2(scan_bytes, max_dimension=max_dimension)
        if scan_img is None:
            raise ValueError("스캔 이미지를 불러올 수 없습니다")

        del scan_bytes
        gc.collect()

        metadata = {"method": method, "success": False, "max_dimension": max_dimension}

        if method == "sift":
            if template_bytes is None:
                raise ValueError("SIFT 방식에는 템플릿 이미지가 필요합니다")

            template_img = bytes_to_cv2(template_bytes, max_dimension=max_dimension)
            if template_img is None:
                raise ValueError("템플릿 이미지를 불러올 수 없습니다")

            del template_bytes
            gc.collect()

            # 메모리 최적화 정렬
            aligned_img, match_count = align_with_sift_memory_optimized(
                scan_img, template_img
            )

            metadata["match_count"] = match_count

            # 템플릿 이미지 삭제
            del template_img
            template_img = None
            gc.collect()

            if aligned_img is not None:
                metadata["success"] = True

        elif method == "contour":
            from app.core.image_utils import align_with_contour

            if template_bytes:
                template_img = bytes_to_cv2(template_bytes, max_dimension=max_dimension)
                h, w = template_img.shape[:2]
                del template_img
                del template_bytes
                gc.collect()
            else:
                w, h = max_dimension, int(max_dimension * 1.414)  # A4 비율

            aligned_img = align_with_contour(scan_img, w, h)

            if aligned_img is not None:
                metadata["success"] = True

        else:
            raise ValueError(f"지원하지 않는 정렬 방식: {method}")

        # 2. 정렬 실패 시 원본 반환
        if aligned_img is None:
            aligned_img = scan_img
            metadata["success"] = False
            metadata["message"] = "정렬 실패. 원본 이미지를 반환합니다."
        else:
            # 스캔 이미지 삭제
            del scan_img
            scan_img = None
            gc.collect()

        # 3. 이미지 품질 개선 (선택적)
        if enhance and metadata["success"]:
            aligned_img = enhance_image(aligned_img, denoise=False)
            metadata["enhanced"] = True
            gc.collect()

        # 4. 메타데이터 추가
        metadata["width"] = aligned_img.shape[1]
        metadata["height"] = aligned_img.shape[0]
        metadata["memory_mb"] = calculate_image_memory(aligned_img)

        # 5. 바이트로 변환 (압축 품질 낮춰서 메모리 절약)
        result_bytes = cv2_to_bytes(aligned_img, format='.jpg', quality=85)

        del aligned_img
        gc.collect()

        return result_bytes, metadata

    except Exception as e:
        logger.error(f"메모리 최적화 정렬 오류: {str(e)}")
        raise
    finally:
        # 최종 메모리 정리
        if scan_img is not None:
            del scan_img
        if template_img is not None:
            del template_img
        if aligned_img is not None:
            del aligned_img
        aggressive_cleanup()
