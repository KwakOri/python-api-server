#!/bin/bash

###############################################################################
# 보안 점검 스크립트
###############################################################################

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo "========================================="
echo "  보안 점검 시작"
echo "========================================="
echo ""

# 1. 시스템 업데이트 확인
echo -e "${YELLOW}[1] 시스템 업데이트 확인${NC}"
sudo apt update -qq
UPGRADABLE=$(apt list --upgradable 2>/dev/null | grep -v "Listing" | wc -l)
if [ "$UPGRADABLE" -gt 0 ]; then
    echo -e "${YELLOW}업데이트 가능: $UPGRADABLE 개${NC}"
else
    echo -e "${GREEN}최신 상태입니다${NC}"
fi
echo ""

# 2. Fail2ban 상태
echo -e "${YELLOW}[2] Fail2ban 상태${NC}"
if systemctl is-active --quiet fail2ban; then
    echo -e "${GREEN}Fail2ban 실행 중${NC}"
    sudo fail2ban-client status | grep "Number of jail"
else
    echo -e "${RED}Fail2ban이 실행되지 않습니다${NC}"
fi
echo ""

# 3. 열린 포트 확인
echo -e "${YELLOW}[3] 열린 포트${NC}"
sudo ss -tulpn | grep LISTEN | awk '{print $5}' | sort -u
echo ""

# 4. 최근 로그인 시도
echo -e "${YELLOW}[4] 최근 실패한 로그인 시도 (최근 10개)${NC}"
sudo grep "Failed password" /var/log/auth.log 2>/dev/null | tail -10 | cut -d' ' -f1,2,3,11 || echo "없음"
echo ""

# 5. Docker 컨테이너 상태
echo -e "${YELLOW}[5] Docker 컨테이너${NC}"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

# 6. SSL 인증서 만료일
echo -e "${YELLOW}[6] SSL 인증서 만료일${NC}"
echo | openssl s_client -servername exam.231edu.cloud -connect exam.231edu.cloud:443 2>/dev/null | \
    openssl x509 -noout -dates 2>/dev/null || echo "확인 실패"
echo ""

# 7. 디스크 사용량
echo -e "${YELLOW}[7] 디스크 사용량${NC}"
df -h / | tail -1
DISK_USAGE=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    echo -e "${RED}⚠️  디스크 사용량이 80%를 초과했습니다!${NC}"
fi
echo ""

# 8. 메모리 사용량
echo -e "${YELLOW}[8] 메모리 사용량${NC}"
free -h | grep -E "Mem:|Swap:"
echo ""

# 9. UFW 방화벽 상태
echo -e "${YELLOW}[9] 방화벽 상태${NC}"
sudo ufw status | head -10
echo ""

# 10. API 헬스체크
echo -e "${YELLOW}[10] API 헬스체크${NC}"
HEALTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health)
if [ "$HEALTH_CHECK" = "200" ]; then
    echo -e "${GREEN}✅ 정상 (HTTP $HEALTH_CHECK)${NC}"
else
    echo -e "${RED}❌ 비정상 (HTTP $HEALTH_CHECK)${NC}"
fi
echo ""

echo "========================================="
echo "  점검 완료: $(date)"
echo "========================================="
