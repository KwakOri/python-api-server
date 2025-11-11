"""
이미지 정렬 및 투시 보정 관련 유틸리티 함수
"""
import cv2
import numpy as np
from typing import Tuple, Optional, List
from PIL import Image
import io


def bytes_to_cv2(image_bytes: bytes) -> np.ndarray:
    """
    바이트 데이터를 OpenCV 이미지로 변환

    Args:
        image_bytes: 이미지 바이트 데이터

    Returns:
        OpenCV 이미지 (numpy array)
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img


def cv2_to_bytes(img: np.ndarray, format: str = '.png') -> bytes:
    """
    OpenCV 이미지를 바이트 데이터로 변환

    Args:
        img: OpenCV 이미지
        format: 출력 포맷 (기본값: .png)

    Returns:
        이미지 바이트 데이터
    """
    is_success, buffer = cv2.imencode(format, img)
    if not is_success:
        raise ValueError("이미지 인코딩 실패")
    return buffer.tobytes()


def align_with_sift(
    scan_img: np.ndarray,
    template_img: np.ndarray,
    ratio_threshold: float = 0.7,
    min_good_matches: int = 10
) -> Tuple[Optional[np.ndarray], int]:
    """
    SIFT + FLANN + Homography를 이용한 이미지 정렬

    Args:
        scan_img: 스캔된 이미지
        template_img: 기준 템플릿 이미지
        ratio_threshold: Lowe's ratio test 임계값 (기본값: 0.7)
        min_good_matches: 최소 유효 매칭 수 (기본값: 10)

    Returns:
        (정렬된 이미지, 매칭 개수) 튜플. 실패 시 (None, 0)
    """
    # 그레이스케일 변환
    gray_scan = cv2.cvtColor(scan_img, cv2.COLOR_BGR2GRAY)
    gray_template = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)

    # SIFT 특징점 검출
    sift = cv2.SIFT_create()
    kp1, des1 = sift.detectAndCompute(gray_scan, None)
    kp2, des2 = sift.detectAndCompute(gray_template, None)

    if des1 is None or des2 is None:
        return None, 0

    # FLANN 매처 설정
    FLANN_INDEX_KDTREE = 1
    index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
    search_params = dict(checks=50)
    flann = cv2.FlannBasedMatcher(index_params, search_params)

    # 매칭 수행
    matches = flann.knnMatch(des1, des2, k=2)

    # Lowe's ratio test로 좋은 매칭만 선택
    good_matches = []
    for match_pair in matches:
        if len(match_pair) == 2:
            m, n = match_pair
            if m.distance < ratio_threshold * n.distance:
                good_matches.append(m)

    if len(good_matches) < min_good_matches:
        return None, len(good_matches)

    # Homography 계산
    src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

    M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

    if M is None:
        return None, len(good_matches)

    # 투시 변환 적용
    h, w = template_img.shape[:2]
    aligned = cv2.warpPerspective(scan_img, M, (w, h))

    return aligned, len(good_matches)


def order_points(pts: np.ndarray) -> np.ndarray:
    """
    사각형의 4개 꼭짓점을 좌상단, 우상단, 우하단, 좌하단 순서로 정렬

    Args:
        pts: 4개의 점 좌표 (4x2 배열)

    Returns:
        정렬된 좌표 배열
    """
    rect = np.zeros((4, 2), dtype="float32")

    # 좌상단: 합이 가장 작음, 우하단: 합이 가장 큼
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    # 우상단: 차이가 가장 작음, 좌하단: 차이가 가장 큼
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]

    return rect


def align_with_contour(
    scan_img: np.ndarray,
    target_width: int = 800,
    target_height: int = 1131
) -> Optional[np.ndarray]:
    """
    외곽선 검출을 이용한 이미지 정렬

    Args:
        scan_img: 스캔된 이미지
        target_width: 목표 이미지 너비 (기본값: 800, A4 비율)
        target_height: 목표 이미지 높이 (기본값: 1131, A4 비율)

    Returns:
        정렬된 이미지. 실패 시 None
    """
    # 그레이스케일 변환 및 전처리
    gray = cv2.cvtColor(scan_img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 50, 200)

    # 외곽선 검출
    contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if len(contours) == 0:
        return None

    # 가장 큰 외곽선을 문서로 간주
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    doc_contour = None

    # 사각형 외곽선 찾기
    for c in contours[:5]:  # 상위 5개만 검사
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)

        if len(approx) == 4:
            doc_contour = approx
            break

    if doc_contour is None:
        return None

    # 좌표 정렬
    pts = doc_contour.reshape(4, 2)
    rect = order_points(pts)

    # 목표 좌표 설정
    dst = np.array([
        [0, 0],
        [target_width - 1, 0],
        [target_width - 1, target_height - 1],
        [0, target_height - 1]
    ], dtype="float32")

    # 투시 변환 행렬 계산 및 적용
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(scan_img, M, (target_width, target_height))

    return warped


def enhance_image(img: np.ndarray) -> np.ndarray:
    """
    이미지 품질 향상 (대비 개선, 노이즈 제거)

    Args:
        img: 입력 이미지

    Returns:
        개선된 이미지
    """
    # 그레이스케일 변환
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()

    # CLAHE (Contrast Limited Adaptive Histogram Equalization) 적용
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # 노이즈 제거
    denoised = cv2.fastNlMeansDenoising(enhanced, None, 10, 7, 21)

    # 컬러 이미지로 변환 (필요 시)
    if len(img.shape) == 3:
        result = cv2.cvtColor(denoised, cv2.COLOR_GRAY2BGR)
    else:
        result = denoised

    return result


def align_scan_to_template(
    scan_bytes: bytes,
    template_bytes: Optional[bytes] = None,
    method: str = "sift",
    enhance: bool = True
) -> Tuple[bytes, dict]:
    """
    스캔 이미지를 템플릿에 맞춰 정렬 (통합 함수)

    Args:
        scan_bytes: 스캔 이미지 바이트 데이터
        template_bytes: 템플릿 이미지 바이트 데이터 (contour 방식에서는 선택사항)
        method: 정렬 방식 ("sift" 또는 "contour")
        enhance: 이미지 품질 개선 여부 (기본값: True)

    Returns:
        (정렬된 이미지 바이트, 메타데이터 딕셔너리)
    """
    # 이미지 로드
    scan_img = bytes_to_cv2(scan_bytes)

    if scan_img is None:
        raise ValueError("스캔 이미지를 불러올 수 없습니다")

    aligned_img = None
    metadata = {"method": method, "success": False}

    if method == "sift":
        if template_bytes is None:
            raise ValueError("SIFT 방식에는 템플릿 이미지가 필요합니다")

        template_img = bytes_to_cv2(template_bytes)
        if template_img is None:
            raise ValueError("템플릿 이미지를 불러올 수 없습니다")

        aligned_img, match_count = align_with_sift(scan_img, template_img)
        metadata["match_count"] = match_count

        if aligned_img is not None:
            metadata["success"] = True

    elif method == "contour":
        # 템플릿이 제공되면 크기를 가져옴
        if template_bytes:
            template_img = bytes_to_cv2(template_bytes)
            h, w = template_img.shape[:2]
        else:
            # 기본 A4 비율 (300 DPI 기준)
            w, h = 800, 1131

        aligned_img = align_with_contour(scan_img, w, h)

        if aligned_img is not None:
            metadata["success"] = True

    else:
        raise ValueError(f"지원하지 않는 정렬 방식: {method}")

    # 정렬 실패 시 원본 반환
    if aligned_img is None:
        aligned_img = scan_img
        metadata["success"] = False
        metadata["message"] = "정렬 실패. 원본 이미지를 반환합니다."

    # 이미지 품질 개선
    if enhance and metadata["success"]:
        aligned_img = enhance_image(aligned_img)
        metadata["enhanced"] = True

    # 메타데이터 추가
    metadata["width"] = aligned_img.shape[1]
    metadata["height"] = aligned_img.shape[0]

    # 바이트로 변환
    result_bytes = cv2_to_bytes(aligned_img)

    return result_bytes, metadata
