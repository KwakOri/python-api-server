#!/bin/bash

###############################################################################
# API Key 로테이션 스크립트
###############################################################################

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================="
echo "  API Key 로테이션"
echo "========================================="
echo ""

# 새 API Key 생성
NEW_API_KEY=$(openssl rand -base64 32)

echo -e "${GREEN}새로운 API Key가 생성되었습니다:${NC}"
echo ""
echo "$NEW_API_KEY"
echo ""

echo -e "${YELLOW}다음 단계를 진행하세요:${NC}"
echo ""
echo "1. .env 파일의 API_KEY 업데이트"
echo "   sed -i 's/^API_KEY=.*/API_KEY=$NEW_API_KEY/' /opt/zuku-exam-server/.env"
echo ""
echo "2. 클라이언트 애플리케이션의 API Key도 업데이트하세요"
echo ""
echo "3. Docker 컨테이너 재시작"
echo "   cd /opt/zuku-exam-server && docker compose restart"
echo ""
echo "========================================="
