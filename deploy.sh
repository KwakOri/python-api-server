#!/bin/bash

###############################################################################
# Zuku Exam Server - 자동 배포 스크립트 (Vultr용)
###############################################################################

set -e  # 에러 발생 시 즉시 중단

# 색상 출력
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 프로젝트 디렉토리
PROJECT_DIR="/opt/zuku-exam-server"
LOG_FILE="/var/log/zuku-deploy.log"

# 로그 함수
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# 배포 시작
log "================================================="
log "Zuku Exam Server 배포 시작"
log "================================================="

# 1. 프로젝트 디렉토리로 이동
if [ ! -d "$PROJECT_DIR" ]; then
    error "프로젝트 디렉토리를 찾을 수 없습니다: $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR"
log "디렉토리 이동: $PROJECT_DIR"

# 2. Git Pull
log "최신 코드 가져오기..."
git fetch origin
git pull origin main

# 3. 환경 변수 확인
if [ ! -f ".env" ]; then
    warning ".env 파일이 없습니다. .env.example을 복사하세요."
fi

# 4. Docker Compose 중지
log "기존 컨테이너 중지..."
docker compose down || true

# 5. Docker 이미지 빌드
log "Docker 이미지 빌드..."
docker compose build --no-cache

# 6. Docker Compose 실행
log "새 컨테이너 실행..."
docker compose up -d

# 7. 컨테이너 상태 확인
log "컨테이너 상태 확인..."
sleep 5
docker compose ps

# 8. 헬스체크
log "헬스체크 실행 (최대 30초 대기)..."
for i in {1..30}; do
    if curl -f http://localhost:8080/health > /dev/null 2>&1; then
        log "헬스체크 성공! 서버가 정상 작동 중입니다."
        break
    fi

    if [ $i -eq 30 ]; then
        error "헬스체크 실패. 로그를 확인하세요."
        docker compose logs --tail=50
        exit 1
    fi

    sleep 1
done

# 9. 불필요한 Docker 리소스 정리
log "Docker 리소스 정리..."
docker system prune -f

# 10. 메모리 상태 확인
log "시스템 메모리 상태:"
free -h

# 11. 배포 완료
log "================================================="
log "배포 완료: $(date)"
log "================================================="
log "API 문서: http://your-domain.com/docs"
log "대기열 상태: http://your-domain.com/queue/status"
log ""
log "로그 확인: docker compose logs -f"
log "컨테이너 중지: docker compose down"
log "================================================="

exit 0
