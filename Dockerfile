# Python 3.10 슬림 이미지 사용
FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 OpenCV 의존성 설치
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgomp1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# requirements 파일 복사 및 패키지 설치
COPY requirements.production.txt requirements.txt ./
RUN pip install --no-cache-dir -r requirements.production.txt

# 애플리케이션 코드 복사
COPY . .

# 포트 노출 (Render는 동적 PORT 환경변수 사용)
EXPOSE 8080

# 환경 변수 기본값 설정
ENV PORT=8080
# Python 메모리 최적화
ENV PYTHONUNBUFFERED=1
ENV PYTHONOPTIMIZE=1
# 가비지 컬렉션 적극적으로 수행
ENV MALLOC_TRIM_THRESHOLD_=100000

# 헬스체크 설정
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health')" || exit 1

# Uvicorn으로 FastAPI 앱 실행 (메모리 최적화 설정)
# --workers 1: 512MB 메모리 제한에서 단일 워커만 사용
# --limit-concurrency 10: 동시 요청 수 제한으로 메모리 폭발 방지
# --timeout-keep-alive 30: Keep-alive 타임아웃 단축
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 1 --limit-concurrency 10 --timeout-keep-alive 30
