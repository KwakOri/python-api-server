"""
OMR(Optical Mark Recognition) 채점 관련 유틸리티 함수
"""
import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
import logging

logger = logging.getLogger(__name__)

# ===== OMR 템플릿 좌표 설정 (퍼센트 기준) =====
GRID_CONFIG = {
    # 선택지 간 간격 (%)
    "horizontal_spacing": 1.48,  # 가로 간격
    "vertical_spacing": 3.76,    # 세로 간격

    # 마커 크기 (%)
    "marker_width": 1.4,
    "marker_height": 2.0,

    # 각 열의 설정
    "columns": [
        {"start": 1, "end": 20, "start_x": 59.4, "start_y": 17.92},   # 1열
        {"start": 21, "end": 34, "start_x": 72.4, "start_y": 17.92},  # 2열
        {"start": 35, "end": 45, "start_x": 84.5, "start_y": 17.92},  # 3열
    ],

    # 선택지 개수
    "options_per_question": 5,
}
# ============================================


def get_bubble_roi(
    img_height: int,
    img_width: int,
    question: int,
    option: int
) -> Tuple[int, int, int, int]:
    """
    특정 문제와 선택지의 버블 ROI 좌표를 반환 (픽셀 단위)

    Args:
        img_height: 이미지 높이
        img_width: 이미지 너비
        question: 문제 번호 (1-45)
        option: 선택지 번호 (1-5)

    Returns:
        (x, y, width, height) 픽셀 좌표
    """
    # 해당 문제가 속한 열 찾기
    column = None
    for col in GRID_CONFIG["columns"]:
        if col["start"] <= question <= col["end"]:
            column = col
            break

    if column is None:
        raise ValueError(f"문제 번호 {question}은(는) 유효하지 않습니다 (1-45)")

    if not (1 <= option <= GRID_CONFIG["options_per_question"]):
        raise ValueError(f"선택지 번호 {option}은(는) 유효하지 않습니다 (1-5)")

    # 열 내에서의 인덱스
    index_in_column = question - column["start"]

    # 퍼센트를 픽셀로 변환
    x_percent = column["start_x"] + (option - 1) * GRID_CONFIG["horizontal_spacing"]
    y_percent = column["start_y"] + index_in_column * GRID_CONFIG["vertical_spacing"]

    x = int(x_percent * img_width / 100)
    y = int(y_percent * img_height / 100)
    width = int(GRID_CONFIG["marker_width"] * img_width / 100)
    height = int(GRID_CONFIG["marker_height"] * img_height / 100)

    return (x, y, width, height)


def is_bubble_marked(
    img: np.ndarray,
    x: int,
    y: int,
    width: int,
    height: int,
    threshold: float = 0.35
) -> Tuple[bool, float]:
    """
    특정 버블 영역이 마킹되었는지 판단

    Args:
        img: 그레이스케일 이미지
        x, y, width, height: 버블 ROI 좌표
        threshold: 마킹 판단 임계값 (0.0 ~ 1.0, 낮을수록 민감)

    Returns:
        (마킹 여부, 어두움 비율)
    """
    # ROI 추출
    roi = img[y:y+height, x:x+width]

    if roi.size == 0:
        logger.warning(f"ROI가 비어있습니다: ({x}, {y}, {width}, {height})")
        return False, 0.0

    # 이진화 (Otsu)
    _, binary = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # 어두운 픽셀 비율 계산
    dark_pixel_ratio = np.count_nonzero(binary) / binary.size

    # 임계값보다 높으면 마킹된 것으로 판단
    is_marked = dark_pixel_ratio > threshold

    return is_marked, dark_pixel_ratio


def detect_bubbles(
    img: np.ndarray,
    threshold: float = 0.35
) -> Dict[int, Optional[int]]:
    """
    OMR 답안지에서 마킹된 답안 검출

    Args:
        img: 정렬된 답안지 이미지 (컬러 또는 그레이스케일)
        threshold: 마킹 판단 임계값 (기본값: 0.35)

    Returns:
        문제 번호를 키로, 마킹된 선택지를 값으로 하는 딕셔너리
        {1: 3, 2: 1, 3: None, ...}  # None은 무응답
    """
    # 그레이스케일 변환
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()

    img_height, img_width = gray.shape
    answers = {}

    # 45개 문제 순회
    for question in range(1, 46):
        marked_options = []

        # 5개 선택지 순회
        for option in range(1, 6):
            try:
                x, y, width, height = get_bubble_roi(img_height, img_width, question, option)
                is_marked, density = is_bubble_marked(gray, x, y, width, height, threshold)

                if is_marked:
                    marked_options.append((option, density))

            except Exception as e:
                logger.error(f"문제 {question}, 선택지 {option} 처리 중 오류: {str(e)}")

        # 마킹된 선택지 처리
        if len(marked_options) == 0:
            # 무응답
            answers[question] = None
        elif len(marked_options) == 1:
            # 정상 마킹
            answers[question] = marked_options[0][0]
        else:
            # 중복 마킹 - 가장 어두운 것 선택 (또는 None 처리 가능)
            marked_options.sort(key=lambda x: x[1], reverse=True)
            answers[question] = marked_options[0][0]
            logger.warning(f"문제 {question}: 중복 마킹 감지 ({[m[0] for m in marked_options]}), "
                          f"{marked_options[0][0]}번을 선택했습니다.")

    return answers


def grade_omr_sheet(
    img: np.ndarray,
    answer_key: List[int],
    threshold: float = 0.35,
    score_per_question: float = 1.0
) -> Dict[str, Any]:
    """
    OMR 답안지 자동 채점

    Args:
        img: 정렬된 OMR 답안지 이미지
        answer_key: 정답 리스트 [1, 3, 2, 4, ...] (1-indexed, 45개)
        threshold: 마킹 판단 임계값 (기본값: 0.35)
        score_per_question: 문제당 배점 (기본값: 1.0)

    Returns:
        채점 결과 딕셔너리
        {
            "total_score": 전체 점수,
            "correct": 맞은 개수,
            "wrong": 틀린 개수,
            "blank": 공란 개수,
            "multiple_marked": 중복 마킹 개수,
            "accuracy": 정답률 (%),
            "details": [
                {
                    "question": 1,
                    "marked": 3,
                    "correct_answer": 3,
                    "is_correct": True,
                    "status": "correct"  # correct, wrong, blank, multiple
                },
                ...
            ]
        }
    """
    if len(answer_key) != 45:
        raise ValueError(f"정답은 45개여야 합니다 (현재: {len(answer_key)}개)")

    # 답안 검출
    detected_answers = detect_bubbles(img, threshold)

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

    return {
        "total_score": total_score,
        "max_score": max_score,
        "correct": correct_count,
        "wrong": wrong_count,
        "blank": blank_count,
        "accuracy": round(accuracy, 2),
        "details": details
    }


def extract_student_info(img: np.ndarray) -> Dict[str, str]:
    """
    답안지에서 학생 정보 추출 (수험번호, 이름 등)

    Args:
        img: 정렬된 답안지 이미지

    Returns:
        학생 정보 딕셔너리
        {
            "student_id": "20240001",
            "name": "홍길동",
            ...
        }
    """
    # TODO: 구현 예정
    # 1. 수험번호 영역 ROI 추출
    # 2. OCR 또는 OMR 방식으로 번호 인식
    # 3. 이름 영역 OCR (선택적)
    raise NotImplementedError("추후 구현 예정")


# 향후 추가 기능:
# - 다중 마킹 검출
# - 마킹 강도 분석
# - 답안지 품질 평가
# - 통계 분석 (정답률, 난이도 등)
