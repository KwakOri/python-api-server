"""
메모리 최적화된 OMR 채점 유틸리티
ROI를 배치로 나눠서 처리하여 메모리 사용량 최소화
"""
import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
import logging
import gc
from app.core.omr_utils import get_bubble_roi, is_bubble_marked, GRID_CONFIG

logger = logging.getLogger(__name__)


def detect_bubbles_batch_optimized(
    img: np.ndarray,
    threshold: float = 0.45,
    batch_size: int = 15
) -> Dict[int, Optional[int]]:
    """
    메모리 최적화된 버블 검출 (배치 처리)

    Args:
        img: 정렬된 답안지 이미지
        threshold: 마킹 판단 임계값
        batch_size: 한 번에 처리할 문제 수 (기본값: 15)

    Returns:
        문제 번호를 키로, 마킹된 선택지를 값으로 하는 딕셔너리
    """
    # 그레이스케일 변환
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()

    img_height, img_width = gray.shape
    answers = {}

    # 45개 문제를 배치로 나눠서 처리
    total_questions = 45
    batches = (total_questions + batch_size - 1) // batch_size  # 올림

    logger.info(f"메모리 최적화 모드: {total_questions}개 문제를 {batches}개 배치로 처리")

    for batch_idx in range(batches):
        start_q = batch_idx * batch_size + 1
        end_q = min((batch_idx + 1) * batch_size, total_questions) + 1

        logger.debug(f"배치 {batch_idx + 1}/{batches}: 문제 {start_q}~{end_q-1}")

        # 배치 내 문제 처리
        for question in range(start_q, end_q):
            marked_options = []
            all_densities = []

            # 5개 선택지 순회
            for option in range(1, 6):
                try:
                    x, y, width, height = get_bubble_roi(img_height, img_width, question, option)
                    is_marked, density = is_bubble_marked(gray, x, y, width, height, threshold)

                    all_densities.append((option, density))

                    if is_marked:
                        marked_options.append((option, density))

                except Exception as e:
                    logger.error(f"문제 {question}, 선택지 {option} 처리 중 오류: {str(e)}")

            # 마킹된 선택지 처리
            if len(marked_options) == 0:
                answers[question] = None
            elif len(marked_options) == 1:
                answers[question] = marked_options[0][0]
                logger.debug(f"문제 {question}: {marked_options[0][0]}번 마킹 (어두움: {marked_options[0][1]:.3f})")
            else:
                # 중복 마킹 - 가장 어두운 것 선택
                marked_options.sort(key=lambda x: x[1], reverse=True)
                answers[question] = marked_options[0][0]

                marked_details = ", ".join([f"{opt}번:{density:.3f}" for opt, density in marked_options])
                all_details = ", ".join([f"{opt}:{density:.3f}" for opt, density in all_densities])

                logger.warning(f"문제 {question}: 중복 마킹 감지 - 마킹됨:[{marked_details}] | "
                              f"전체:[{all_details}] | 선택: {marked_options[0][0]}번")

        # 배치마다 메모리 정리
        if batch_idx < batches - 1:
            gc.collect()
            logger.debug(f"배치 {batch_idx + 1} 처리 완료, 메모리 정리")

    # 최종 메모리 정리
    del gray
    gc.collect()

    return answers


def grade_omr_sheet_memory_optimized(
    img: np.ndarray,
    answer_key: List[int],
    threshold: float = 0.45,
    score_per_question: float = 1.0,
    batch_size: int = 15
) -> Dict[str, Any]:
    """
    메모리 최적화된 OMR 자동 채점

    Args:
        img: 정렬된 OMR 답안지 이미지
        answer_key: 정답 리스트 (45개)
        threshold: 마킹 판단 임계값
        score_per_question: 문제당 배점
        batch_size: 배치 크기

    Returns:
        채점 결과 딕셔너리
    """
    if len(answer_key) != 45:
        raise ValueError(f"정답은 45개여야 합니다 (현재: {len(answer_key)}개)")

    # 배치 처리로 답안 검출
    detected_answers = detect_bubbles_batch_optimized(img, threshold, batch_size)

    # 채점
    correct_count = 0
    wrong_count = 0
    blank_count = 0
    details = []

    for question in range(1, 46):
        marked = detected_answers.get(question)
        correct_answer = answer_key[question - 1]

        is_correct = False
        status = "wrong"

        if marked is None:
            status = "blank"
            blank_count += 1
        elif marked == correct_answer:
            status = "correct"
            is_correct = True
            correct_count += 1
        else:
            status = "wrong"
            wrong_count += 1

        details.append({
            "question": question,
            "marked": marked,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
            "status": status
        })

    # 점수 계산
    total_score = correct_count * score_per_question
    max_score = 45 * score_per_question
    accuracy = (correct_count / 45) * 100 if correct_count > 0 else 0.0

    result = {
        "total_score": total_score,
        "max_score": max_score,
        "correct": correct_count,
        "wrong": wrong_count,
        "blank": blank_count,
        "accuracy": round(accuracy, 2),
        "details": details,
        "memory_optimized": True,
        "batch_size": batch_size
    }

    # 메모리 정리
    gc.collect()

    return result


def extract_and_grade_roi_minimal_memory(
    img: np.ndarray,
    question: int,
    option: int,
    threshold: float = 0.45
) -> Tuple[bool, float]:
    """
    최소 메모리로 단일 ROI 추출 및 판정

    Args:
        img: 그레이스케일 이미지
        question: 문제 번호
        option: 선택지 번호
        threshold: 임계값

    Returns:
        (마킹 여부, 어두움 비율)
    """
    img_height, img_width = img.shape[:2]
    x, y, width, height = get_bubble_roi(img_height, img_width, question, option)

    # ROI만 추출 (전체 이미지 복사하지 않음)
    roi = img[y:y+height, x:x+width]

    if roi.size == 0:
        return False, 0.0

    # 이진화
    _, binary = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # 어두운 픽셀 비율
    dark_pixel_ratio = np.count_nonzero(binary) / binary.size

    # 임시 변수 삭제
    del roi
    del binary

    is_marked = dark_pixel_ratio > threshold

    return is_marked, dark_pixel_ratio
