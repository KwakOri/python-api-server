"""
API 테스트 스크립트
이미지 정렬 API의 모든 엔드포인트를 테스트합니다.
"""
import requests
import os
import time
import json
from pathlib import Path


class APITester:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url
        self.samples_dir = Path("samples")
        self.results_dir = Path("test_results")

        # 결과 디렉토리 생성
        self.results_dir.mkdir(exist_ok=True)

    def test_health_check(self):
        """헬스 체크 테스트"""
        print("\n" + "="*50)
        print("1. 헬스 체크 테스트")
        print("="*50)

        try:
            response = requests.get(f"{self.base_url}/health")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

            if response.status_code == 200:
                print("✓ 헬스 체크 성공")
                return True
            else:
                print("✗ 헬스 체크 실패")
                return False
        except Exception as e:
            print(f"✗ 오류 발생: {str(e)}")
            return False

    def test_root_endpoint(self):
        """루트 엔드포인트 테스트"""
        print("\n" + "="*50)
        print("2. 루트 엔드포인트 테스트")
        print("="*50)

        try:
            response = requests.get(f"{self.base_url}/")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

            if response.status_code == 200:
                print("✓ 루트 엔드포인트 성공")
                return True
            else:
                print("✗ 루트 엔드포인트 실패")
                return False
        except Exception as e:
            print(f"✗ 오류 발생: {str(e)}")
            return False

    def test_align_endpoint_json(self):
        """이미지 정렬 (JSON 응답) 테스트"""
        print("\n" + "="*50)
        print("3. 이미지 정렬 테스트 (JSON 응답)")
        print("="*50)

        template_path = self.samples_dir / "template.png"
        scan_path = self.samples_dir / "scan1_rotated.png"

        if not template_path.exists() or not scan_path.exists():
            print("✗ 샘플 이미지가 없습니다. 먼저 generate_sample_images.py를 실행하세요.")
            return False

        try:
            with open(template_path, 'rb') as template_file, \
                 open(scan_path, 'rb') as scan_file:

                files = {
                    'template': template_file,
                    'scan': scan_file
                }
                data = {
                    'method': 'sift',
                    'enhance': True,
                    'return_image': False
                }

                print(f"Template: {template_path}")
                print(f"Scan: {scan_path}")
                print(f"Method: SIFT")

                start_time = time.time()
                response = requests.post(f"{self.base_url}/api/align", files=files, data=data)
                elapsed_time = time.time() - start_time

                print(f"\nStatus Code: {response.status_code}")
                print(f"처리 시간: {elapsed_time:.2f}초")
                print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

                if response.status_code == 200:
                    print("✓ 이미지 정렬 성공 (JSON)")
                    return True
                else:
                    print("✗ 이미지 정렬 실패")
                    return False

        except Exception as e:
            print(f"✗ 오류 발생: {str(e)}")
            return False

    def test_align_endpoint_image(self, method='sift'):
        """이미지 정렬 (이미지 응답) 테스트"""
        print("\n" + "="*50)
        print(f"4. 이미지 정렬 테스트 ({method.upper()} - 이미지 응답)")
        print("="*50)

        template_path = self.samples_dir / "template.png"
        scan_path = self.samples_dir / "scan1_rotated.png"

        if not template_path.exists() or not scan_path.exists():
            print("✗ 샘플 이미지가 없습니다.")
            return False

        try:
            with open(template_path, 'rb') as template_file, \
                 open(scan_path, 'rb') as scan_file:

                files = {
                    'template': template_file,
                    'scan': scan_file
                }
                data = {
                    'method': method,
                    'enhance': True,
                    'return_image': True
                }

                print(f"Template: {template_path}")
                print(f"Scan: {scan_path}")
                print(f"Method: {method.upper()}")

                start_time = time.time()
                response = requests.post(f"{self.base_url}/api/align", files=files, data=data)
                elapsed_time = time.time() - start_time

                print(f"\nStatus Code: {response.status_code}")
                print(f"처리 시간: {elapsed_time:.2f}초")
                print(f"Content-Type: {response.headers.get('Content-Type')}")
                print(f"Image Size: {len(response.content)} bytes")

                if response.status_code == 200:
                    # 결과 이미지 저장
                    output_path = self.results_dir / f"aligned_{method}.png"
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    print(f"✓ 이미지 정렬 성공 (이미지 저장: {output_path})")
                    return True
                else:
                    print("✗ 이미지 정렬 실패")
                    return False

        except Exception as e:
            print(f"✗ 오류 발생: {str(e)}")
            return False

    def test_contour_method(self):
        """Contour 방식 테스트"""
        print("\n" + "="*50)
        print("5. Contour 방식 정렬 테스트")
        print("="*50)

        scan_path = self.samples_dir / "scan1_rotated.png"

        if not scan_path.exists():
            print("✗ 샘플 이미지가 없습니다.")
            return False

        try:
            with open(scan_path, 'rb') as scan_file:
                files = {
                    'scan': scan_file
                }
                data = {
                    'method': 'contour',
                    'enhance': True,
                    'return_image': True
                }

                print(f"Scan: {scan_path}")
                print(f"Method: Contour (템플릿 없음)")

                start_time = time.time()
                response = requests.post(f"{self.base_url}/api/align", files=files, data=data)
                elapsed_time = time.time() - start_time

                print(f"\nStatus Code: {response.status_code}")
                print(f"처리 시간: {elapsed_time:.2f}초")

                if response.status_code == 200:
                    output_path = self.results_dir / "aligned_contour.png"
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    print(f"✓ Contour 정렬 성공 (이미지 저장: {output_path})")
                    return True
                else:
                    print("✗ Contour 정렬 실패")
                    return False

        except Exception as e:
            print(f"✗ 오류 발생: {str(e)}")
            return False

    def test_batch_processing(self):
        """배치 처리 테스트"""
        print("\n" + "="*50)
        print("6. 배치 처리 테스트")
        print("="*50)

        template_path = self.samples_dir / "template.png"
        scan_files = [
            self.samples_dir / "scan1_rotated.png",
            self.samples_dir / "scan2_heavily_rotated.png",
            self.samples_dir / "scan3_perspective.png"
        ]

        # 존재하는 파일만 선택
        existing_scans = [f for f in scan_files if f.exists()]

        if not template_path.exists() or len(existing_scans) == 0:
            print("✗ 샘플 이미지가 없습니다.")
            return False

        try:
            with open(template_path, 'rb') as template_file:
                files = [('template', template_file)]

                # 스캔 파일들 추가
                scan_file_handles = []
                for scan_path in existing_scans:
                    f = open(scan_path, 'rb')
                    scan_file_handles.append(f)
                    files.append(('scans', f))

                data = {
                    'method': 'sift',
                    'enhance': True
                }

                print(f"Template: {template_path}")
                print(f"Scans: {len(existing_scans)}개")
                for scan in existing_scans:
                    print(f"  - {scan.name}")

                start_time = time.time()
                response = requests.post(f"{self.base_url}/api/align/batch", files=files, data=data)
                elapsed_time = time.time() - start_time

                # 파일 핸들 닫기
                for f in scan_file_handles:
                    f.close()

                print(f"\nStatus Code: {response.status_code}")
                print(f"처리 시간: {elapsed_time:.2f}초")
                print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

                if response.status_code == 200:
                    print("✓ 배치 처리 성공")
                    return True
                else:
                    print("✗ 배치 처리 실패")
                    return False

        except Exception as e:
            print(f"✗ 오류 발생: {str(e)}")
            return False

    def test_all_scans(self):
        """모든 샘플 스캔 테스트"""
        print("\n" + "="*50)
        print("7. 모든 샘플 이미지 정렬 테스트")
        print("="*50)

        template_path = self.samples_dir / "template.png"

        if not template_path.exists():
            print("✗ 템플릿 이미지가 없습니다.")
            return False

        # 모든 스캔 파일 찾기
        scan_files = list(self.samples_dir.glob("scan*.png"))

        if len(scan_files) == 0:
            print("✗ 스캔 이미지가 없습니다.")
            return False

        print(f"\n총 {len(scan_files)}개의 스캔 이미지 테스트\n")

        results = []
        for scan_path in scan_files:
            try:
                with open(template_path, 'rb') as template_file, \
                     open(scan_path, 'rb') as scan_file:

                    files = {
                        'template': template_file,
                        'scan': scan_file
                    }
                    data = {
                        'method': 'sift',
                        'enhance': True,
                        'return_image': True
                    }

                    print(f"처리 중: {scan_path.name}...", end=" ")
                    start_time = time.time()
                    response = requests.post(f"{self.base_url}/api/align", files=files, data=data)
                    elapsed_time = time.time() - start_time

                    if response.status_code == 200:
                        output_path = self.results_dir / f"aligned_{scan_path.stem}.png"
                        with open(output_path, 'wb') as f:
                            f.write(response.content)
                        print(f"✓ 성공 ({elapsed_time:.2f}초)")
                        results.append((scan_path.name, True, elapsed_time))
                    else:
                        print(f"✗ 실패")
                        results.append((scan_path.name, False, elapsed_time))

            except Exception as e:
                print(f"✗ 오류: {str(e)}")
                results.append((scan_path.name, False, 0))

        # 결과 요약
        print("\n" + "-"*50)
        print("결과 요약:")
        success_count = sum(1 for _, success, _ in results if success)
        total_time = sum(t for _, _, t in results)
        print(f"  성공: {success_count}/{len(results)}")
        print(f"  총 처리 시간: {total_time:.2f}초")
        print(f"  평균 처리 시간: {total_time/len(results):.2f}초")

        return success_count == len(results)

    def run_all_tests(self):
        """모든 테스트 실행"""
        print("\n" + "="*60)
        print("         이미지 정렬 API 테스트 시작")
        print("="*60)

        tests = [
            ("헬스 체크", self.test_health_check),
            ("루트 엔드포인트", self.test_root_endpoint),
            ("정렬 (JSON)", self.test_align_endpoint_json),
            ("정렬 (SIFT 이미지)", lambda: self.test_align_endpoint_image('sift')),
            ("정렬 (Contour)", self.test_contour_method),
            ("배치 처리", self.test_batch_processing),
            ("전체 샘플 테스트", self.test_all_scans),
        ]

        results = []
        for test_name, test_func in tests:
            try:
                result = test_func()
                results.append((test_name, result))
            except Exception as e:
                print(f"\n✗ {test_name} 테스트 중 예외 발생: {str(e)}")
                results.append((test_name, False))

        # 최종 결과
        print("\n" + "="*60)
        print("         테스트 결과 요약")
        print("="*60)
        for test_name, result in results:
            status = "✓ 성공" if result else "✗ 실패"
            print(f"{test_name:20s} : {status}")

        success_count = sum(1 for _, result in results if result)
        print("\n" + "-"*60)
        print(f"전체 결과: {success_count}/{len(results)} 성공")
        print("="*60)

        if success_count == len(results):
            print("\n🎉 모든 테스트 성공!")
        else:
            print(f"\n⚠️  {len(results) - success_count}개 테스트 실패")

        print(f"\n정렬된 이미지 저장 위치: {self.results_dir}/")


def main():
    import sys

    # 서버 URL 설정
    base_url = "http://localhost:8080"
    if len(sys.argv) > 1:
        base_url = sys.argv[1]

    print(f"API 서버: {base_url}")

    # 샘플 이미지 확인
    samples_dir = Path("samples")
    if not samples_dir.exists() or len(list(samples_dir.glob("*.png"))) == 0:
        print("\n⚠️  샘플 이미지가 없습니다.")
        print("먼저 다음 명령을 실행하여 샘플 이미지를 생성하세요:")
        print("  python tests/generate_sample_images.py")
        return

    # 테스트 실행
    tester = APITester(base_url)
    tester.run_all_tests()


if __name__ == "__main__":
    main()
