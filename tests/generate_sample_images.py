"""
테스트용 샘플 이미지 생성 스크립트
시험지 템플릿과 왜곡된 스캔본을 생성합니다.
"""
import cv2
import numpy as np
import os


def create_exam_template(width=800, height=1131, filename='template.png'):
    """
    시험지 템플릿 이미지 생성 (A4 비율)

    Args:
        width: 이미지 너비
        height: 이미지 높이
        filename: 저장할 파일명
    """
    # 흰색 배경 생성
    img = np.ones((height, width, 3), dtype=np.uint8) * 255

    # 테두리 그리기 (검은색)
    cv2.rectangle(img, (50, 50), (width-50, height-50), (0, 0, 0), 3)

    # 제목 영역
    cv2.putText(img, "EXAM PAPER", (width//2 - 150, 100),
                cv2.FONT_HERSHEY_BOLD, 1.5, (0, 0, 0), 3)

    # 학생 정보 영역
    cv2.rectangle(img, (80, 130), (width-80, 250), (0, 0, 0), 2)
    cv2.putText(img, "Name: _________________", (100, 170),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.putText(img, "Student ID: ___________", (100, 210),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

    # 문제 영역 (OMR 형식)
    y_offset = 280
    for i in range(10):
        # 문제 번호
        cv2.putText(img, f"{i+1}.", (100, y_offset + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

        # 선택지 원 (1-5)
        for j in range(5):
            x = 180 + j * 80
            cv2.circle(img, (x, y_offset + 25), 20, (0, 0, 0), 2)
            cv2.putText(img, str(j+1), (x-8, y_offset + 33),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

        y_offset += 60

    # 모서리 마커 (정렬 기준점)
    marker_size = 30
    # 좌상단
    cv2.rectangle(img, (50, 50), (50+marker_size, 50+marker_size), (0, 0, 0), -1)
    # 우상단
    cv2.rectangle(img, (width-50-marker_size, 50), (width-50, 50+marker_size), (0, 0, 0), -1)
    # 좌하단
    cv2.rectangle(img, (50, height-50-marker_size), (50+marker_size, height-50), (0, 0, 0), -1)
    # 우하단
    cv2.rectangle(img, (width-50-marker_size, height-50-marker_size),
                  (width-50, height-50), (0, 0, 0), -1)

    # 저장
    cv2.imwrite(filename, img)
    print(f"✓ 템플릿 이미지 생성 완료: {filename}")
    return img


def create_scanned_image(template_img, filename='scan.png',
                         rotation=15, scale=1.1, noise_level=10):
    """
    왜곡된 스캔 이미지 생성

    Args:
        template_img: 원본 템플릿 이미지
        filename: 저장할 파일명
        rotation: 회전 각도 (도)
        scale: 크기 배율
        noise_level: 노이즈 레벨
    """
    h, w = template_img.shape[:2]

    # 1. 회전 변환
    center = (w // 2, h // 2)
    M_rotate = cv2.getRotationMatrix2D(center, rotation, scale)
    rotated = cv2.warpAffine(template_img, M_rotate, (w, h),
                             borderMode=cv2.BORDER_CONSTANT,
                             borderValue=(255, 255, 255))

    # 2. 투시 변환 (약간의 왜곡)
    pts1 = np.float32([[0, 0], [w, 0], [0, h], [w, h]])
    pts2 = np.float32([
        [50, 30],           # 좌상단
        [w-30, 20],         # 우상단
        [40, h-20],         # 좌하단
        [w-50, h-40]        # 우하단
    ])
    M_perspective = cv2.getPerspectiveTransform(pts1, pts2)
    warped = cv2.warpPerspective(rotated, M_perspective, (w, h),
                                  borderMode=cv2.BORDER_CONSTANT,
                                  borderValue=(255, 255, 255))

    # 3. 노이즈 추가
    noise = np.random.normal(0, noise_level, warped.shape).astype(np.uint8)
    noisy = cv2.add(warped, noise)

    # 4. 약간의 블러 (스캔 효과)
    blurred = cv2.GaussianBlur(noisy, (3, 3), 0)

    # 5. 밝기 조정 (약간 어둡게)
    adjusted = cv2.convertScaleAbs(blurred, alpha=0.95, beta=-5)

    # 저장
    cv2.imwrite(filename, adjusted)
    print(f"✓ 스캔 이미지 생성 완료: {filename}")
    return adjusted


def create_marked_exam(template_img, filename='scan_marked.png',
                       answers=[1, 3, 2, 4, 5, 2, 1, 3, 4, 5]):
    """
    답안이 마킹된 시험지 생성

    Args:
        template_img: 원본 템플릿 이미지
        filename: 저장할 파일명
        answers: 마킹할 답안 리스트 (1-indexed)
    """
    marked_img = template_img.copy()

    y_offset = 280
    for i, answer in enumerate(answers):
        if 1 <= answer <= 5:
            # 선택된 답안에 채우기
            x = 180 + (answer - 1) * 80
            cv2.circle(marked_img, (x, y_offset + 25), 18, (0, 0, 0), -1)
        y_offset += 60

    # 스캔 효과 추가
    scanned = create_scanned_image(marked_img, filename,
                                    rotation=10, scale=1.05, noise_level=8)
    return scanned


def main():
    """메인 함수"""
    # 샘플 디렉토리 확인
    samples_dir = 'samples'
    if not os.path.exists(samples_dir):
        os.makedirs(samples_dir)

    print("\n" + "="*50)
    print("테스트용 샘플 이미지 생성")
    print("="*50 + "\n")

    # 1. 템플릿 이미지 생성
    template_path = os.path.join(samples_dir, 'template.png')
    template = create_exam_template(filename=template_path)

    # 2. 왜곡된 스캔 이미지들 생성
    print("\n왜곡된 스캔 이미지 생성 중...")

    # 약간 회전된 스캔
    scan1_path = os.path.join(samples_dir, 'scan1_rotated.png')
    create_scanned_image(template, scan1_path, rotation=15, scale=1.05, noise_level=10)

    # 많이 회전된 스캔
    scan2_path = os.path.join(samples_dir, 'scan2_heavily_rotated.png')
    create_scanned_image(template, scan2_path, rotation=-25, scale=1.1, noise_level=15)

    # 투시 왜곡이 심한 스캔
    scan3_path = os.path.join(samples_dir, 'scan3_perspective.png')
    create_scanned_image(template, scan3_path, rotation=8, scale=0.95, noise_level=12)

    # 3. 답안이 마킹된 시험지 생성
    print("\n답안 마킹된 시험지 생성 중...")
    marked1_path = os.path.join(samples_dir, 'scan_marked_1.png')
    create_marked_exam(template, marked1_path,
                       answers=[1, 3, 2, 4, 5, 2, 1, 3, 4, 5])

    marked2_path = os.path.join(samples_dir, 'scan_marked_2.png')
    create_marked_exam(template, marked2_path,
                       answers=[2, 2, 3, 3, 4, 4, 5, 5, 1, 1])

    print("\n" + "="*50)
    print("✓ 모든 샘플 이미지 생성 완료!")
    print("="*50)
    print(f"\n생성된 이미지 위치: {samples_dir}/")
    print("\n생성된 파일:")
    print("  - template.png (기준 템플릿)")
    print("  - scan1_rotated.png (약간 회전)")
    print("  - scan2_heavily_rotated.png (많이 회전)")
    print("  - scan3_perspective.png (투시 왜곡)")
    print("  - scan_marked_1.png (답안 마킹 1)")
    print("  - scan_marked_2.png (답안 마킹 2)")
    print("\n사용 예시:")
    print("  curl -X POST http://localhost:8080/api/align \\")
    print(f"    -F 'scan=@{samples_dir}/scan1_rotated.png' \\")
    print(f"    -F 'template=@{samples_dir}/template.png' \\")
    print("    -F 'method=sift' \\")
    print("    -F 'return_image=true' \\")
    print("    -o aligned.png")
    print()


if __name__ == "__main__":
    main()
