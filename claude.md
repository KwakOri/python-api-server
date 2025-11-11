🧩 프로젝트 개요

스캔된 시험지 이미지들을 정렬(Perspective Alignment)하고 이후 채점 기능을 추가하기 위한 Python 기반 API 서버를 개발하려고 합니다.
프론트엔드는 별도로 존재하지 않으며, FastAPI를 통해 REST API로 이미지를 받아 정렬된 결과를 반환할 예정입니다.

🧱 주요 목표

스캔된 시험지 이미지의 기울기 및 투시 왜곡 보정

기준 템플릿 이미지에 맞춰 자동 정렬

이후 채점(OMR 등)을 위한 전처리 단계로 활용

API 서버로 구현 (FastAPI)

배포는 Fly.io(Docker 기반) 예정

⚙️ 기술 스택
구성 선택
언어 Python 3.10+
웹 프레임워크 FastAPI
서버 실행기 Uvicorn
이미지 처리 OpenCV, NumPy, Pillow
배포 Fly.io
(선택) AI/ML PyTorch or TensorFlow (채점 단계에서 사용 예정)
🧠 정렬 알고리즘 설계

스캔본은 복합기나 스캐너로 입력되므로 배경이 깔끔하고 테두리가 명확합니다.
이에 따라 두 가지 정렬 방식을 고려합니다.

1️⃣ 특징점 기반 정렬 (정확도 ↑)

SIFT + FLANN + Homography

단계

기준 템플릿 이미지와 스캔 이미지를 그레이스케일로 변환

SIFT를 이용해 특징점 추출

FLANN으로 매칭

좋은 매칭점만 남기고 RANSAC으로 Homography 계산

cv2.warpPerspective()로 투시 변환

코드 요약

sift = cv2.SIFT*create()
kp1, des1 = sift.detectAndCompute(scan, None)
kp2, des2 = sift.detectAndCompute(template, None)
flann = cv2.FlannBasedMatcher(dict(algorithm=1, trees=5), dict(checks=50))
matches = flann.knnMatch(des1, des2, k=2)
good = [m for m, n in matches if m.distance < 0.7 * n.distance]
M, \* = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
aligned = cv2.warpPerspective(scan, M, (template.shape[1], template.shape[0]))

2️⃣ 외곽선 기반 정렬 (단순 속도 ↑)

Contour Detection + Perspective Transform

단계

Canny Edge로 외곽선 검출

가장 큰 사각형을 문서 영역으로 인식

4개 꼭짓점을 정렬 후 cv2.getPerspectiveTransform() 수행

코드 요약

gray = cv2.cvtColor(img, cv2.COLOR*BGR2GRAY)
edged = cv2.Canny(gray, 50, 200)
contours, * = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
doc = sorted(contours, key=cv2.contourArea, reverse=True)[0]
M = cv2.getPerspectiveTransform(src_pts, dst_pts)
warped = cv2.warpPerspective(img, M, (width, height))

🧩 FastAPI 구조 제안
grading_api/
│
├── main.py # FastAPI 진입점
├── app/
│ ├── routers/
│ │ ├── align.py # /api/align (이미지 정렬 API)
│ └── core/
│ ├── image_utils.py # OpenCV 관련 함수 (정렬, 투시보정)
│ └── omr_utils.py # 채점 로직 (추후 구현)
└── requirements.txt

FastAPI 엔드포인트 예시

from fastapi import FastAPI, UploadFile, File
from app.core.image_utils import align_scan_to_template

app = FastAPI()

@app.post("/api/align")
async def align_image(file: UploadFile = File(...)):
image_bytes = await file.read()
result = align_scan_to_template(image_bytes)
return {"message": "정렬 완료", "width": result.shape[1], "height": result.shape[0]}

🐳 Dockerfile (Fly.io 배포용)
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

requirements.txt

fastapi
uvicorn
opencv-python
numpy
pillow

🧾 참고 사항

기준 템플릿 이미지는 template.png 로 지정

스캔본이 많을 경우 glob.glob() 으로 배치 정렬 가능

조명 보정이 필요하면 cv2.equalizeHist() 또는 CLAHE 적용

API 호출 시 multipart/form-data 로 파일 업로드

✅ 정리
항목 선택
정렬 방식 SIFT + Homography (기본), Contour (대안)
입력 스캔된 시험지 이미지
출력 기준 템플릿에 정렬된 이미지
API 서버 FastAPI
배포 Fly.io
사용 예 Vercel → Fly.io FastAPI 호출 (정렬 결과 반환)
