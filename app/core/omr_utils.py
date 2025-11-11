"""
OMR(Optical Mark Recognition) 채점 관련 유틸리티 함수
추후 구현 예정
"""
import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional


def detect_bubbles(
    img: np.ndarray,
    roi: Optional[Tuple[int, int, int, int]] = None
) -> List[Tuple[int, int, int, int]]:
    """
    OMR 답안지에서 마킹된 버블(동그라미) 검출

    Args:
        img: 입력 이미지
        roi: 관심 영역 (x, y, width, height). None이면 전체 이미지

    Returns:
        검출된 버블 좌표 리스트 [(x, y, w, h), ...]
    """
    # TODO: 구현 예정
    # 1. 이미지 전처리 (그레이스케일, 이진화)
    # 2. 원형 검출 (HoughCircles 또는 컨투어)
    # 3. 마킹 여부 판단 (픽셀 밀도 분석)
    raise NotImplementedError("추후 구현 예정")


def grade_omr_sheet(
    img: np.ndarray,
    answer_key: List[int],
    num_questions: int,
    choices_per_question: int = 5
) -> Dict:
    """
    OMR 답안지 자동 채점

    Args:
        img: 정렬된 OMR 답안지 이미지
        answer_key: 정답 리스트 [1, 3, 2, 4, ...] (1-indexed)
        num_questions: 문제 개수
        choices_per_question: 문항당 선택지 개수 (기본값: 5)

    Returns:
        채점 결과 딕셔너리
        {
            "score": 점수,
            "correct": 맞은 개수,
            "wrong": 틀린 개수,
            "blank": 공란 개수,
            "details": [{"question": 1, "marked": 3, "correct": 3, "is_correct": True}, ...]
        }
    """
    # TODO: 구현 예정
    # 1. 답안 영역 ROI 설정
    # 2. 각 문항별 마킹 검출
    # 3. 정답과 비교
    # 4. 점수 계산
    raise NotImplementedError("추후 구현 예정")


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
