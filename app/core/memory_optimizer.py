"""
메모리 최적화 유틸리티
512MB 제한 환경에서 이미지 처리를 위한 메모리 관리
"""
import cv2
import numpy as np
import gc
from typing import Tuple, Optional, List
import logging

logger = logging.getLogger(__name__)


def calculate_image_memory(img: np.ndarray) -> float:
    """
    이미지가 사용하는 메모리 크기 계산 (MB)
    """
    if img is None:
        return 0.0
    return img.nbytes / (1024 * 1024)


def optimize_image_size(img: np.ndarray, max_memory_mb: float = 5.0) -> np.ndarray:
    """
    이미지 크기를 메모리 제한에 맞춰 최적화

    Args:
        img: 입력 이미지
        max_memory_mb: 최대 메모리 크기 (MB)

    Returns:
        최적화된 이미지
    """
    current_memory = calculate_image_memory(img)

    if current_memory <= max_memory_mb:
        return img

    # 축소 비율 계산
    scale = np.sqrt(max_memory_mb / current_memory)
    h, w = img.shape[:2]
    new_w = int(w * scale)
    new_h = int(h * scale)

    logger.info(f"메모리 최적화: {current_memory:.2f}MB → {max_memory_mb:.2f}MB, "
                f"크기: {w}x{h} → {new_w}x{new_h}")

    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

    # 원본 메모리 해제
    del img
    gc.collect()

    return resized


def aggressive_cleanup():
    """
    공격적인 메모리 정리
    """
    gc.collect()
    gc.collect()  # 2번 호출하면 더 효과적
    gc.collect()


def process_with_memory_limit(
    func,
    *args,
    cleanup_after: bool = True,
    **kwargs
):
    """
    메모리 제한을 고려한 함수 실행

    Args:
        func: 실행할 함수
        cleanup_after: 실행 후 메모리 정리 여부
    """
    try:
        result = func(*args, **kwargs)
        return result
    finally:
        if cleanup_after:
            aggressive_cleanup()


def downsample_for_alignment(img: np.ndarray, target_size: int = 800) -> Tuple[np.ndarray, float]:
    """
    정렬용으로 이미지를 다운샘플링 (메모리 절약)

    Args:
        img: 원본 이미지
        target_size: 목표 최대 크기 (px)

    Returns:
        (다운샘플된 이미지, 스케일 비율)
    """
    h, w = img.shape[:2]
    max_dim = max(h, w)

    if max_dim <= target_size:
        return img, 1.0

    scale = target_size / max_dim
    new_w = int(w * scale)
    new_h = int(h * scale)

    downsampled = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

    logger.info(f"정렬용 다운샘플: {w}x{h} → {new_w}x{new_h} (스케일: {scale:.3f})")

    return downsampled, scale


def upsample_with_homography(
    img: np.ndarray,
    homography: np.ndarray,
    target_shape: Tuple[int, int],
    scale: float = 1.0
) -> np.ndarray:
    """
    Homography 행렬을 스케일 조정하여 원본 크기로 업샘플

    Args:
        img: 원본 고해상도 이미지
        homography: 다운샘플된 이미지로 계산한 Homography
        target_shape: 목표 크기 (width, height)
        scale: 다운샘플 시 사용한 스케일

    Returns:
        정렬된 고해상도 이미지
    """
    # Homography 스케일 조정
    scale_matrix = np.array([
        [1/scale, 0, 0],
        [0, 1/scale, 0],
        [0, 0, 1]
    ], dtype=np.float32)

    # H_full = S^-1 * H * S
    adjusted_H = scale_matrix @ homography @ np.linalg.inv(scale_matrix)

    # 고해상도 이미지에 적용
    aligned = cv2.warpPerspective(img, adjusted_H, target_shape)

    return aligned


def process_roi_in_batches(
    img: np.ndarray,
    roi_processor_func,
    total_items: int,
    batch_size: int = 15,
    **kwargs
) -> List:
    """
    ROI를 배치로 나눠서 처리 (메모리 절약)

    Args:
        img: 이미지
        roi_processor_func: ROI 처리 함수
        total_items: 총 아이템 수
        batch_size: 배치 크기
        **kwargs: 처리 함수에 전달할 추가 인자

    Returns:
        처리 결과 리스트
    """
    results = []

    for batch_start in range(0, total_items, batch_size):
        batch_end = min(batch_start + batch_size, total_items)

        logger.debug(f"ROI 배치 처리: {batch_start+1}-{batch_end}/{total_items}")

        # 배치 처리
        batch_results = roi_processor_func(
            img,
            start=batch_start,
            end=batch_end,
            **kwargs
        )

        results.extend(batch_results)

        # 배치마다 메모리 정리
        if batch_end < total_items:
            gc.collect()

    return results


def get_memory_efficient_sift_params(image_size: Tuple[int, int]) -> dict:
    """
    이미지 크기에 따른 메모리 효율적인 SIFT 파라미터

    Args:
        image_size: (width, height)

    Returns:
        SIFT 파라미터 딕셔너리
    """
    w, h = image_size
    max_dim = max(w, h)

    if max_dim <= 800:
        return {
            'nfeatures': 150,
            'downsample_size': 800,
            'description': '800px 이하 - 150 특징점'
        }
    elif max_dim <= 1000:
        return {
            'nfeatures': 200,
            'downsample_size': 900,
            'description': '1000px 이하 - 200 특징점'
        }
    elif max_dim <= 1200:
        return {
            'nfeatures': 250,
            'downsample_size': 1000,
            'description': '1200px 이하 - 250 특징점'
        }
    else:
        return {
            'nfeatures': 300,
            'downsample_size': 1000,
            'description': '1200px 초과 - 300 특징점, 1000px로 다운샘플'
        }


def compress_image_quality(img: np.ndarray, quality: int = 75) -> np.ndarray:
    """
    JPEG 압축을 통한 메모리 절약 (손실 압축)

    Args:
        img: 입력 이미지
        quality: JPEG 품질 (1-100)

    Returns:
        압축 후 이미지
    """
    encode_param = [cv2.IMWRITE_JPEG_QUALITY, quality]
    _, encoded = cv2.imencode('.jpg', img, encode_param)
    compressed = cv2.imdecode(encoded, cv2.IMREAD_COLOR)

    original_memory = calculate_image_memory(img)
    compressed_memory = calculate_image_memory(compressed)

    logger.info(f"이미지 압축: {original_memory:.2f}MB → {compressed_memory:.2f}MB "
                f"(품질: {quality})")

    return compressed
