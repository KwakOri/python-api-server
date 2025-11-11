# 이미지 정렬 API 테스트 가이드

이 문서는 시험지 정렬 API를 테스트하는 방법을 안내합니다.

## 목차

1. [빠른 시작](#빠른-시작)
2. [샘플 이미지 생성](#샘플-이미지-생성)
3. [자동 테스트 실행](#자동-테스트-실행)
4. [수동 테스트](#수동-테스트)
5. [실제 이미지로 테스트](#실제-이미지로-테스트)

---

## 빠른 시작

### 1단계: 서버 실행

터미널 1에서 서버를 실행합니다:

```bash
# 의존성 설치 (최초 1회)
pip install -r requirements.txt

# 서버 실행
python main.py
```

서버가 `http://localhost:8080`에서 실행됩니다.

### 2단계: 샘플 이미지 생성

터미널 2에서 테스트용 샘플 이미지를 생성합니다:

```bash
python tests/generate_sample_images.py
```

생성되는 이미지:
- `samples/template.png` - 기준 템플릿
- `samples/scan1_rotated.png` - 약간 회전된 스캔
- `samples/scan2_heavily_rotated.png` - 많이 회전된 스캔
- `samples/scan3_perspective.png` - 투시 왜곡된 스캔
- `samples/scan_marked_1.png` - 답안 마킹된 스캔 1
- `samples/scan_marked_2.png` - 답안 마킹된 스캔 2

### 3단계: 자동 테스트 실행

```bash
python tests/test_api.py
```

모든 API 엔드포인트를 자동으로 테스트하고 결과를 `test_results/` 디렉토리에 저장합니다.

---

## 샘플 이미지 생성

### 자동 생성

```bash
python tests/generate_sample_images.py
```

### 생성되는 이미지 설명

| 파일명 | 설명 | 용도 |
|--------|------|------|
| `template.png` | 깨끗한 시험지 템플릿 | SIFT 정렬의 기준 이미지 |
| `scan1_rotated.png` | 15도 회전 + 약간의 노이즈 | 기본 정렬 테스트 |
| `scan2_heavily_rotated.png` | 25도 회전 + 많은 노이즈 | 심한 왜곡 테스트 |
| `scan3_perspective.png` | 투시 변환 왜곡 | 투시 보정 테스트 |
| `scan_marked_1.png` | 답안 마킹된 스캔 | OMR 채점 테스트용 |
| `scan_marked_2.png` | 답안 마킹된 스캔 | OMR 채점 테스트용 |

### 커스텀 샘플 생성

`generate_sample_images.py`를 수정하여 원하는 왜곡 정도를 조절할 수 있습니다:

```python
# 회전 각도 조절
create_scanned_image(template, 'scan_custom.png',
                     rotation=30,      # 회전 각도 (도)
                     scale=1.2,        # 크기 배율
                     noise_level=20)   # 노이즈 레벨
```

---

## 자동 테스트 실행

### 전체 테스트

```bash
python tests/test_api.py
```

실행되는 테스트:
1. ✓ 헬스 체크
2. ✓ 루트 엔드포인트
3. ✓ 이미지 정렬 (JSON 응답)
4. ✓ 이미지 정렬 (SIFT 방식)
5. ✓ 이미지 정렬 (Contour 방식)
6. ✓ 배치 처리
7. ✓ 전체 샘플 테스트

### 다른 서버 URL로 테스트

```bash
# 로컬 다른 포트
python tests/test_api.py http://localhost:3000

# 원격 서버
python tests/test_api.py https://your-app.fly.dev
```

### 테스트 결과 확인

정렬된 이미지는 `test_results/` 디렉토리에 저장됩니다:

```
test_results/
├── aligned_sift.png
├── aligned_contour.png
├── aligned_scan1_rotated.png
├── aligned_scan2_heavily_rotated.png
└── aligned_scan3_perspective.png
```

---

## 수동 테스트

### 1. 헬스 체크

```bash
curl http://localhost:8080/health
```

**예상 응답:**
```json
{
  "status": "healthy",
  "service": "exam-alignment-api"
}
```

### 2. API 정보 확인

```bash
curl http://localhost:8080/
```

### 3. 이미지 정렬 (SIFT 방식)

#### JSON 응답받기

```bash
curl -X POST http://localhost:8080/api/align \
  -F "scan=@samples/scan1_rotated.png" \
  -F "template=@samples/template.png" \
  -F "method=sift" \
  -F "enhance=true" \
  -F "return_image=false"
```

**예상 응답:**
```json
{
  "success": true,
  "message": "이미지 정렬 완료",
  "metadata": {
    "method": "sift",
    "success": true,
    "match_count": 150,
    "enhanced": true,
    "width": 800,
    "height": 1131
  }
}
```

#### 이미지 파일로 받기

```bash
curl -X POST http://localhost:8080/api/align \
  -F "scan=@samples/scan1_rotated.png" \
  -F "template=@samples/template.png" \
  -F "method=sift" \
  -F "return_image=true" \
  -o aligned_result.png
```

정렬된 이미지가 `aligned_result.png`로 저장됩니다.

### 4. 이미지 정렬 (Contour 방식)

템플릿 없이 외곽선 검출로 정렬:

```bash
curl -X POST http://localhost:8080/api/align \
  -F "scan=@samples/scan1_rotated.png" \
  -F "method=contour" \
  -F "return_image=true" \
  -o aligned_contour.png
```

### 5. 배치 처리

여러 이미지를 한 번에 정렬:

```bash
curl -X POST http://localhost:8080/api/align/batch \
  -F "scans=@samples/scan1_rotated.png" \
  -F "scans=@samples/scan2_heavily_rotated.png" \
  -F "scans=@samples/scan3_perspective.png" \
  -F "template=@samples/template.png" \
  -F "method=sift"
```

**예상 응답:**
```json
{
  "success": true,
  "total": 3,
  "successful": 3,
  "failed": 0,
  "results": [
    {
      "index": 0,
      "filename": "scan1_rotated.png",
      "success": true,
      "metadata": { ... }
    },
    ...
  ]
}
```

---

## 실제 이미지로 테스트

### 준비사항

1. 스캔된 시험지 이미지 준비
2. 기준 템플릿 이미지 준비 (SIFT 방식 사용 시)

### SIFT 방식 (권장)

정확한 정렬이 필요한 경우:

```bash
curl -X POST http://localhost:8080/api/align \
  -F "scan=@/path/to/your/scan.jpg" \
  -F "template=@/path/to/your/template.jpg" \
  -F "method=sift" \
  -F "enhance=true" \
  -F "return_image=true" \
  -o aligned.png
```

### Contour 방식

빠른 처리가 필요하고 배경이 깨끗한 경우:

```bash
curl -X POST http://localhost:8080/api/align \
  -F "scan=@/path/to/your/scan.jpg" \
  -F "method=contour" \
  -F "enhance=true" \
  -F "return_image=true" \
  -o aligned.png
```

### Python으로 테스트

```python
import requests

# 이미지 파일 경로
scan_path = 'path/to/scan.jpg'
template_path = 'path/to/template.jpg'

# API 호출
with open(scan_path, 'rb') as scan_file, \
     open(template_path, 'rb') as template_file:

    files = {
        'scan': scan_file,
        'template': template_file
    }
    data = {
        'method': 'sift',
        'enhance': True,
        'return_image': True
    }

    response = requests.post(
        'http://localhost:8080/api/align',
        files=files,
        data=data
    )

    # 결과 저장
    if response.status_code == 200:
        with open('aligned.png', 'wb') as f:
            f.write(response.content)
        print("✓ 정렬 완료: aligned.png")
    else:
        print(f"✗ 오류: {response.json()}")
```

---

## 성능 테스트

### 처리 시간 측정

```bash
time curl -X POST http://localhost:8080/api/align \
  -F "scan=@samples/scan1_rotated.png" \
  -F "template=@samples/template.png" \
  -F "method=sift" \
  -F "return_image=true" \
  -o /dev/null
```

### 메모리 사용량 확인

서버 실행 중에:

```bash
# Linux/Mac
ps aux | grep "python main.py"

# 또는 htop 사용
htop
```

---

## 문제 해결

### 서버가 시작되지 않음

```bash
# 포트가 사용 중인지 확인
lsof -i :8080

# 다른 포트로 실행
uvicorn main:app --host 0.0.0.0 --port 8081
```

### 샘플 이미지가 생성되지 않음

```bash
# OpenCV 설치 확인
python -c "import cv2; print(cv2.__version__)"

# 패키지 재설치
pip install --upgrade opencv-python numpy
```

### 정렬이 실패함

**SIFT 방식:**
- 템플릿 이미지가 제공되었는지 확인
- 특징점 매칭 개수가 충분한지 확인 (최소 10개)
- 이미지 품질이 너무 낮지 않은지 확인

**Contour 방식:**
- 배경이 깔끔한지 확인
- 시험지 테두리가 명확한지 확인
- 이미지가 너무 어둡지 않은지 확인

### 메모리 부족

큰 이미지 처리 시:
- 이미지 크기를 줄여서 테스트
- 서버 메모리 할당량 증가
- Docker/Fly.io 메모리 설정 조정

---

## Swagger UI로 테스트

브라우저에서 http://localhost:8080/docs 접속

1. `POST /api/align` 엔드포인트 클릭
2. "Try it out" 버튼 클릭
3. 파일 업로드 및 파라미터 설정
4. "Execute" 버튼 클릭
5. 응답 확인

인터랙티브하게 API를 테스트할 수 있어 편리합니다!

---

## 다음 단계

1. **성능 최적화 테스트**
   - 여러 해상도의 이미지로 테스트
   - 처리 시간 측정 및 비교

2. **엣지 케이스 테스트**
   - 매우 어두운 이미지
   - 매우 밝은 이미지
   - 해상도가 매우 낮은 이미지
   - 회전 각도가 큰 이미지

3. **OMR 채점 기능 테스트** (추후)
   - 마킹 검출
   - 자동 채점

4. **프로덕션 배포 테스트**
   - Fly.io 배포 후 테스트
   - 실제 환경에서 성능 확인

---

## 도움말

문제가 발생하거나 질문이 있으면:
- GitHub Issues 등록
- README.md 참고
- API 문서 확인: http://localhost:8080/docs
