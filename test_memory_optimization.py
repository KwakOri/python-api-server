"""
메모리 최적화 테스트 스크립트
기존 방식 vs 최적화 방식 비교
"""
import cv2
import time
import tracemalloc
from pathlib import Path
from app.core.memory_monitor import log_memory_usage

# 색상 코드
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'


def test_basic_alignment(scan_path: str, template_path: str):
    """기존 방식 테스트 (1200px)"""
    print(f"\n{BLUE}=== 기존 방식 테스트 (1200px) ==={RESET}")

    from app.core.image_utils import bytes_to_cv2, align_with_sift

    # 메모리 추적 시작
    tracemalloc.start()
    start_time = time.time()
    log_memory_usage("[시작]")

    # 이미지 로드
    with open(scan_path, 'rb') as f:
        scan_bytes = f.read()
    with open(template_path, 'rb') as f:
        template_bytes = f.read()

    scan_img = bytes_to_cv2(scan_bytes, max_dimension=1200)
    template_img = bytes_to_cv2(template_bytes, max_dimension=1200)

    log_memory_usage("[이미지 로드 후]")

    # 정렬
    aligned, match_count = align_with_sift(scan_img, template_img, max_features=300)

    # 결과
    end_time = time.time()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    log_memory_usage("[완료]")

    print(f"{GREEN}✓ 정렬 성공{RESET}")
    print(f"  - 매칭 수: {match_count}")
    print(f"  - 처리 시간: {end_time - start_time:.2f}초")
    print(f"  - 피크 메모리: {peak / 1024 / 1024:.2f}MB")
    print(f"  - 최종 크기: {aligned.shape[1]}x{aligned.shape[0]}")

    return {
        'method': 'basic',
        'match_count': match_count,
        'time': end_time - start_time,
        'peak_memory_mb': peak / 1024 / 1024,
        'size': aligned.shape[:2]
    }


def test_optimized_alignment(scan_path: str, template_path: str):
    """최적화 방식 테스트 (1000px, 다운샘플)"""
    print(f"\n{BLUE}=== 최적화 방식 테스트 (1000px, 다운샘플) ==={RESET}")

    from app.core.image_utils_memory_optimized import align_scan_to_template_memory_optimized

    # 메모리 추적 시작
    tracemalloc.start()
    start_time = time.time()
    log_memory_usage("[시작]")

    # 이미지 로드 및 정렬
    with open(scan_path, 'rb') as f:
        scan_bytes = f.read()
    with open(template_path, 'rb') as f:
        template_bytes = f.read()

    log_memory_usage("[이미지 로드 후]")

    aligned_bytes, metadata = align_scan_to_template_memory_optimized(
        scan_bytes=scan_bytes,
        template_bytes=template_bytes,
        method="sift",
        enhance=True,
        max_dimension=1000
    )

    # 결과
    end_time = time.time()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    log_memory_usage("[완료]")

    print(f"{GREEN}✓ 정렬 성공{RESET}")
    print(f"  - 매칭 수: {metadata.get('match_count', 0)}")
    print(f"  - 처리 시간: {end_time - start_time:.2f}초")
    print(f"  - 피크 메모리: {peak / 1024 / 1024:.2f}MB")
    print(f"  - 최종 크기: {metadata['width']}x{metadata['height']}")
    print(f"  - 이미지 메모리: {metadata.get('memory_mb', 0):.2f}MB")

    return {
        'method': 'optimized',
        'match_count': metadata.get('match_count', 0),
        'time': end_time - start_time,
        'peak_memory_mb': peak / 1024 / 1024,
        'size': (metadata['height'], metadata['width'])
    }


def test_omr_detection(aligned_img_path: str):
    """OMR 검출 테스트 (기존 vs 배치)"""
    print(f"\n{BLUE}=== OMR 검출 테스트 ==={RESET}")

    from app.core.omr_utils import detect_bubbles
    from app.core.omr_utils_memory_optimized import detect_bubbles_batch_optimized

    img = cv2.imread(aligned_img_path)

    # 기존 방식
    print(f"\n{YELLOW}기존 방식 (일괄 처리){RESET}")
    tracemalloc.start()
    start_time = time.time()

    answers1 = detect_bubbles(img, threshold=0.45)

    end_time = time.time()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"  - 처리 시간: {end_time - start_time:.3f}초")
    print(f"  - 피크 메모리: {peak / 1024 / 1024:.2f}MB")

    # 최적화 방식
    print(f"\n{YELLOW}최적화 방식 (배치 처리){RESET}")
    tracemalloc.start()
    start_time = time.time()

    answers2 = detect_bubbles_batch_optimized(img, threshold=0.45, batch_size=15)

    end_time = time.time()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"  - 처리 시간: {end_time - start_time:.3f}초")
    print(f"  - 피크 메모리: {peak / 1024 / 1024:.2f}MB")

    # 결과 비교
    print(f"\n{GREEN}결과 일치 여부:{RESET}")
    match = answers1 == answers2
    print(f"  - {'✓ 동일' if match else '✗ 다름'}")

    if not match:
        diff_count = sum(1 for k in answers1 if answers1[k] != answers2.get(k))
        print(f"  - 차이 개수: {diff_count}/45")


def compare_results(result1: dict, result2: dict):
    """결과 비교 출력"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{'='*20} 성능 비교 {'='*21}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")

    print(f"\n{YELLOW}처리 시간:{RESET}")
    print(f"  기존:     {result1['time']:.2f}초")
    print(f"  최적화:   {result2['time']:.2f}초")
    improvement = (result1['time'] - result2['time']) / result1['time'] * 100
    if improvement > 0:
        print(f"  {GREEN}→ {improvement:.1f}% 빠름{RESET}")
    else:
        print(f"  {RED}→ {-improvement:.1f}% 느림{RESET}")

    print(f"\n{YELLOW}피크 메모리:{RESET}")
    print(f"  기존:     {result1['peak_memory_mb']:.2f}MB")
    print(f"  최적화:   {result2['peak_memory_mb']:.2f}MB")
    reduction = (result1['peak_memory_mb'] - result2['peak_memory_mb']) / result1['peak_memory_mb'] * 100
    print(f"  {GREEN}→ {reduction:.1f}% 절감{RESET}")

    print(f"\n{YELLOW}매칭 수:{RESET}")
    print(f"  기존:     {result1['match_count']}")
    print(f"  최적화:   {result2['match_count']}")

    print(f"\n{YELLOW}이미지 크기:{RESET}")
    print(f"  기존:     {result1['size'][1]}x{result1['size'][0]}")
    print(f"  최적화:   {result2['size'][1]}x{result2['size'][0]}")

    print(f"\n{BLUE}{'='*60}{RESET}\n")


def main():
    """메인 테스트 실행"""
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{'='*15} 메모리 최적화 테스트 {'='*15}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")

    # 파일 경로
    scan_path = "samples/20251109130430_페이지_02.png"
    template_path = "omr_card.jpg"

    if not Path(scan_path).exists():
        print(f"{RED}✗ 스캔 이미지를 찾을 수 없습니다: {scan_path}{RESET}")
        return

    if not Path(template_path).exists():
        print(f"{RED}✗ 템플릿 이미지를 찾을 수 없습니다: {template_path}{RESET}")
        return

    print(f"\n{GREEN}✓ 이미지 파일 확인 완료{RESET}")
    print(f"  - 스캔: {scan_path}")
    print(f"  - 템플릿: {template_path}")

    try:
        # 1. 정렬 테스트
        result1 = test_basic_alignment(scan_path, template_path)
        result2 = test_optimized_alignment(scan_path, template_path)

        # 2. 결과 비교
        compare_results(result1, result2)

        # 3. OMR 검출 테스트 (옵션)
        print(f"\n{YELLOW}OMR 검출 테스트를 진행하시겠습니까? (y/n):{RESET} ", end='')
        if input().lower() == 'y':
            test_omr_detection("aligned_01.png")

        print(f"\n{GREEN}✓ 모든 테스트 완료!{RESET}")

    except Exception as e:
        print(f"\n{RED}✗ 오류 발생: {str(e)}{RESET}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
