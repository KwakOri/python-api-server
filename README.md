# 시험지 정렬 및 채점 API

스캔된 시험지 이미지를 정렬(Perspective Alignment)하고 이후 채점 기능을 제공하는 Python 기반 REST API 서버입니다.

## 주요 기능

- **이미지 정렬**: 스캔된 시험지의 기울기 및 투시 왜곡 보정
- **두 가지 정렬 방식**: SIFT 기반 고정확도 방식과 Contour 기반 고속 방식
- **배치 처리**: 여러 이미지를 한 번에 처리
- **이미지 품질 개선**: CLAHE 및 노이즈 제거
- **OMR 채점**: (추후 구현 예정)

## 기술 스택

| 구성 요소 | 기술 |
|-----------|------|
| 언어 | Python 3.10+ |
| 웹 프레임워크 | FastAPI |
| 서버 | Uvicorn |
| 이미지 처리 | OpenCV, NumPy, Pillow |
| 배포 | Fly.io (Docker) |

## 프로젝트 구조

```
python-api-server/
├── main.py                 # FastAPI 진입점
├── app/
│   ├── routers/
│   │   └── align.py        # 이미지 정렬 API 엔드포인트
│   └── core/
│       ├── image_utils.py  # 이미지 처리 로직
│       └── omr_utils.py    # OMR 채점 로직 (추후 구현)
├── requirements.txt        # Python 패키지 의존성
├── Dockerfile             # Docker 이미지 빌드 설정
├── .dockerignore          # Docker 빌드 제외 파일
└── fly.toml               # Fly.io 배포 설정
```

## 설치 및 실행

### 로컬 환경에서 실행

1. 저장소 클론 및 이동
```bash
git clone <repository-url>
cd python-api-server
```

2. 가상환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. 패키지 설치
```bash
pip install -r requirements.txt
```

4. 서버 실행
```bash
python main.py
# 또는
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

5. API 문서 확인
- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc

### Docker로 실행

```bash
# 이미지 빌드
docker build -t exam-alignment-api .

# 컨테이너 실행
docker run -p 8080:8080 exam-alignment-api
```

### Fly.io 배포

1. Fly.io CLI 설치
```bash
# macOS
brew install flyctl

# Windows
powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"

# Linux
curl -L https://fly.io/install.sh | sh
```

2. Fly.io 로그인
```bash
flyctl auth login
```

3. 앱 생성 및 배포
```bash
# 최초 배포
flyctl launch

# 이후 배포
flyctl deploy
```

4. 배포된 앱 확인
```bash
flyctl status
flyctl open
```

## API 사용법

### 1. 이미지 정렬 (단일)

**엔드포인트**: `POST /api/align`

**Parameters**:
- `scan` (file, required): 스캔된 시험지 이미지
- `template` (file, optional): 기준 템플릿 이미지 (SIFT 방식에 필요)
- `method` (string, default: "sift"): 정렬 방식 ("sift" 또는 "contour")
- `enhance` (boolean, default: true): 이미지 품질 개선 여부
- `return_image` (boolean, default: false): 이미지 반환 여부

**예제 (curl)**:

```bash
# JSON 메타데이터 반환
curl -X POST "http://localhost:8080/api/align" \
  -F "scan=@scan.jpg" \
  -F "template=@template.jpg" \
  -F "method=sift" \
  -F "enhance=true" \
  -F "return_image=false"

# 정렬된 이미지 반환
curl -X POST "http://localhost:8080/api/align" \
  -F "scan=@scan.jpg" \
  -F "template=@template.jpg" \
  -F "method=sift" \
  -F "return_image=true" \
  -o aligned.png
```

**예제 (Python)**:

```python
import requests

# JSON 메타데이터 반환
with open('scan.jpg', 'rb') as scan_file, open('template.jpg', 'rb') as template_file:
    files = {
        'scan': scan_file,
        'template': template_file
    }
    data = {
        'method': 'sift',
        'enhance': True,
        'return_image': False
    }
    response = requests.post('http://localhost:8080/api/align', files=files, data=data)
    print(response.json())

# 정렬된 이미지 저장
with open('scan.jpg', 'rb') as scan_file, open('template.jpg', 'rb') as template_file:
    files = {
        'scan': scan_file,
        'template': template_file
    }
    data = {
        'method': 'sift',
        'return_image': True
    }
    response = requests.post('http://localhost:8080/api/align', files=files, data=data)

    with open('aligned.png', 'wb') as f:
        f.write(response.content)
```

### 2. 배치 이미지 정렬

**엔드포인트**: `POST /api/align/batch`

**Parameters**:
- `scans` (files, required): 스캔된 시험지 이미지들 (여러 개)
- `template` (file, optional): 기준 템플릿 이미지
- `method` (string, default: "sift"): 정렬 방식
- `enhance` (boolean, default: true): 이미지 품질 개선 여부

**예제 (curl)**:

```bash
curl -X POST "http://localhost:8080/api/align/batch" \
  -F "scans=@scan1.jpg" \
  -F "scans=@scan2.jpg" \
  -F "scans=@scan3.jpg" \
  -F "template=@template.jpg" \
  -F "method=sift"
```

## 정렬 방식

### SIFT (Scale-Invariant Feature Transform)

- **장점**: 높은 정확도, 회전/크기/왜곡에 강함
- **단점**: 처리 속도가 느림, 템플릿 이미지 필요
- **사용 사례**: 정확한 정렬이 중요한 경우

```python
method = "sift"
```

### Contour (외곽선 검출)

- **장점**: 빠른 처리 속도, 템플릿 선택사항
- **단점**: 배경이 깔끔해야 함
- **사용 사례**: 스캔 품질이 좋고 빠른 처리가 필요한 경우

```python
method = "contour"
```

## API 응답 예제

### 성공 응답 (JSON)

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
  },
  "note": "정렬된 이미지를 받으려면 return_image=true로 요청하세요"
}
```

### 배치 처리 응답

```json
{
  "success": true,
  "total": 3,
  "successful": 2,
  "failed": 1,
  "results": [
    {
      "index": 0,
      "filename": "scan1.jpg",
      "success": true,
      "metadata": {...}
    },
    {
      "index": 1,
      "filename": "scan2.jpg",
      "success": true,
      "metadata": {...}
    },
    {
      "index": 2,
      "filename": "scan3.jpg",
      "success": false,
      "error": "특징점 매칭 실패"
    }
  ]
}
```

## 이미지 품질 개선

`enhance=true`로 설정하면 다음 처리를 수행합니다:

1. **CLAHE (Contrast Limited Adaptive Histogram Equalization)**: 대비 개선
2. **노이즈 제거**: Non-local Means Denoising

## 헬스 체크

```bash
curl http://localhost:8080/health
```

응답:
```json
{
  "status": "healthy",
  "service": "exam-alignment-api"
}
```

## 개발 로드맵

- [x] 이미지 정렬 (SIFT)
- [x] 이미지 정렬 (Contour)
- [x] 배치 처리
- [x] 이미지 품질 개선
- [ ] OMR 채점 기능
- [ ] 학생 정보 추출
- [ ] 다중 마킹 검출
- [ ] 통계 분석

## 문제 해결

### OpenCV 설치 오류

```bash
# 시스템 패키지 설치 (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install libgl1-mesa-glx libglib2.0-0

# macOS
brew install opencv
```

### 메모리 부족

Fly.io에서 메모리 부족 시 `fly.toml`에서 메모리 증가:

```toml
[[vm]]
  memory_mb = 1024  # 512MB에서 1024MB로 증가
```

## 라이선스

MIT License

## 기여

이슈 및 풀 리퀘스트는 언제든 환영합니다!

## 문의

문제가 발생하거나 궁금한 점이 있으면 Issue를 등록해주세요.
