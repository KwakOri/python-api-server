# 설치 가이드

## 환경별 설치 방법

### 🖥️ 로컬 개발 환경

로컬에서 개발할 때는 메모리 모니터링 및 디버깅 도구를 포함하여 설치합니다.

```bash
# 1. 기본 패키지 설치
pip install -r requirements.txt

# 2. 개발용 패키지 추가 설치
pip install -r requirements-dev.txt
```

**포함되는 추가 기능:**
- ✅ 메모리 모니터링 (`psutil`)
- ✅ Flask 디버그 서버 (`flask`)
- ✅ ROI 시각화 도구

---

### 🚀 서버 배포 환경 (Render, Fly.io 등)

서버 환경에서는 필수 패키지만 설치하여 가볍게 유지합니다.

```bash
# 기본 패키지만 설치 (메모리 모니터링 없음)
pip install -r requirements.txt
```

**특징:**
- ✅ 경량화 (psutil 제외)
- ✅ Headless OpenCV 사용
- ✅ 빠른 빌드 시간

---

## 개발 환경 설정

### Python 버전
```bash
python --version  # Python 3.10 이상 권장
```

### 가상 환경 생성 (권장)

```bash
# venv 생성
python -m venv venv

# 활성화 (Mac/Linux)
source venv/bin/activate

# 활성화 (Windows)
venv\Scripts\activate
```

### 환경 변수 설정

`.env` 파일 생성:
```env
# 환경 설정
ENVIRONMENT=development  # development 또는 production

# API 키 (필요 시)
API_SECRET_KEY=your-secret-key-here
```

---

## 메모리 모니터링 활성화/비활성화

### 자동 감지 (기본)
`psutil`이 설치되어 있으면 자동으로 활성화되고, 없으면 비활성화됩니다.

```python
# app/core/memory_monitor.py에서 자동 처리
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
```

### 로컬에서 메모리 모니터링 사용
```bash
pip install psutil
python main.py
```

로그에 메모리 사용량이 표시됩니다:
```
INFO - [배치 채점 시작] 메모리 사용량 - RSS: 66.16MB, VMS: 402468.16MB, 사용률: 0.81%
```

### 서버에서 메모리 모니터링 없이 실행
```bash
# psutil 설치 안 함
pip install -r requirements.txt
python main.py
```

로그에 간단한 디버그 메시지만 표시됩니다:
```
DEBUG - [배치 채점 시작] 메모리 모니터링 비활성화 (psutil 없음)
```

---

## OpenCV 패키지 선택

### 로컬 개발 (GUI 있는 환경)

GUI 디버깅이 필요한 경우:
```bash
pip uninstall opencv-python-headless opencv-contrib-python-headless
pip install opencv-python==4.9.0.80
pip install opencv-contrib-python==4.9.0.80
```

### 서버 배포 (Headless 환경)

requirements.txt의 기본 설정 사용:
```
opencv-python-headless==4.9.0.80
opencv-contrib-python-headless==4.9.0.80
```

---

## 디버그 도구 사용

### Flask ROI 뷰어 (로컬 전용)

```bash
# requirements-dev.txt 설치 필요
pip install -r requirements-dev.txt

# Flask 디버그 서버 실행
python debug_roi_viewer.py
```

브라우저에서 `http://localhost:5001` 접속

---

## 트러블슈팅

### psutil 설치 오류 (Mac)
```bash
# Xcode Command Line Tools 설치
xcode-select --install

# 재시도
pip install psutil
```

### OpenCV import 오류
```bash
# 기존 OpenCV 완전 제거
pip uninstall opencv-python opencv-contrib-python opencv-python-headless opencv-contrib-python-headless

# 재설치
pip install opencv-python-headless opencv-contrib-python-headless
```

### 서버에서 빌드 실패
```bash
# requirements.txt 확인
cat requirements.txt | grep psutil
# 주석 처리되어 있는지 확인: # psutil==5.9.8

# Render/Fly.io 재배포
git add requirements.txt
git commit -m "Disable psutil in production"
git push
```

---

## 패키지 업데이트

### 의존성 업데이트
```bash
pip list --outdated
pip install --upgrade package-name
```

### requirements 재생성
```bash
pip freeze > requirements-freeze.txt
# 필요한 패키지만 선별하여 requirements.txt 업데이트
```

---

## 참고 링크

- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [OpenCV-Python 튜토리얼](https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html)
- [Render 배포 가이드](https://render.com/docs/deploy-fastapi)
- [psutil 문서](https://psutil.readthedocs.io/)

---

**작성일:** 2025-11-12
**버전:** 1.0
