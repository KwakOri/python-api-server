#!/bin/bash

###############################################################################
# 로그 분석 및 에러 체크 스크립트
###############################################################################

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo "========================================="
echo "  Zuku Exam Server - 로그 분석"
echo "========================================="
echo ""

# 1. Docker 로그에서 최근 에러 확인
echo -e "${YELLOW}[1] Docker 컨테이너 에러 (최근 50줄)${NC}"
cd /opt/zuku-exam-server
docker compose logs --tail=50 | grep -i "error\|exception\|failed\|warning" || echo -e "${GREEN}에러 없음${NC}"
echo ""

# 2. Nginx 에러 로그 확인
echo -e "${YELLOW}[2] Nginx 에러 로그 (최근 20줄)${NC}"
if [ -f /var/log/nginx/zuku-exam-error.log ]; then
    tail -20 /var/log/nginx/zuku-exam-error.log | grep -i "error\|crit\|alert" || echo -e "${GREEN}에러 없음${NC}"
else
    echo "로그 파일 없음"
fi
echo ""

# 3. 디스크 사용량 확인
echo -e "${YELLOW}[3] 디스크 사용량${NC}"
df -h / | tail -1 | awk '{print "사용: "$3" / "$2" ("$5")"}'
DISK_USAGE=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    echo -e "${RED}⚠️  디스크 사용량이 80%를 초과했습니다!${NC}"
fi
echo ""

# 4. 메모리 사용량 확인
echo -e "${YELLOW}[4] 메모리 사용량${NC}"
free -h | grep "Mem:" | awk '{print "사용: "$3" / "$2}'
free -h | grep "Swap:" | awk '{print "Swap: "$3" / "$2}'
echo ""

# 5. Docker 컨테이너 상태
echo -e "${YELLOW}[5] Docker 컨테이너 상태${NC}"
docker compose ps
echo ""

# 6. 최근 API 요청 통계 (Nginx access log)
echo -e "${YELLOW}[6] 최근 API 요청 (1시간 이내)${NC}"
if [ -f /var/log/nginx/zuku-exam-access.log ]; then
    # 최근 1시간 요청 수
    RECENT_REQUESTS=$(grep "$(date -u +%d/%b/%Y:%H -d '1 hour ago')" /var/log/nginx/zuku-exam-access.log 2>/dev/null | wc -l)
    echo "요청 수: $RECENT_REQUESTS"

    # 상태 코드별 통계
    echo "상태 코드 분포:"
    grep "$(date -u +%d/%b/%Y:%H -d '1 hour ago')" /var/log/nginx/zuku-exam-access.log 2>/dev/null | \
        awk '{print $9}' | sort | uniq -c | sort -rn | head -5 || echo "데이터 없음"
else
    echo "로그 파일 없음"
fi
echo ""

# 7. 헬스체크
echo -e "${YELLOW}[7] API 헬스체크${NC}"
HEALTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health)
if [ "$HEALTH_CHECK" = "200" ]; then
    echo -e "${GREEN}✅ 정상 (HTTP $HEALTH_CHECK)${NC}"
else
    echo -e "${RED}❌ 비정상 (HTTP $HEALTH_CHECK)${NC}"
fi
echo ""

echo "========================================="
echo "  분석 완료: $(date)"
echo "========================================="
