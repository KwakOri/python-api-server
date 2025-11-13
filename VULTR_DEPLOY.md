# Vultr 배포 가이드 (1GB RAM 최적화)

이 문서는 Zuku Exam Server를 Vultr VPS에 배포하는 전체 과정을 설명합니다.

## 📋 목차

1. [Vultr 인스턴스 생성](#1-vultr-인스턴스-생성)
2. [서버 초기 설정](#2-서버-초기-설정)
3. [Swap 메모리 설정 (1GB RAM 필수)](#3-swap-메모리-설정-1gb-ram-필수)
4. [프로젝트 배포](#4-프로젝트-배포)
5. [Nginx 설정](#5-nginx-설정)
6. [SSL 인증서 설정](#6-ssl-인증서-설정)
7. [자동 배포 설정](#7-자동-배포-설정)
8. [모니터링 및 관리](#8-모니터링-및-관리)
9. [트러블슈팅](#9-트러블슈팅)

---

## 1. Vultr 인스턴스 생성

### 권장 사양

| 항목 | 값 |
|------|-----|
| OS | Ubuntu 22.04 LTS |
| RAM | 1GB (최소) / 2GB (권장) |
| Storage | 25GB SSD |
| Location | 가장 가까운 지역 선택 |

### Vultr 웹 콘솔에서 설정

1. Vultr 로그인 → **Deploy New Server**
2. **Server Type**: Cloud Compute - Shared CPU
3. **Location**: Seoul 또는 Tokyo (한국 사용자)
4. **OS**: Ubuntu 22.04 x64
5. **Server Size**: 1GB RAM ($6/월) 또는 2GB RAM ($12/월)
6. **SSH Keys**: 사전에 등록한 SSH 키 선택 (보안 강화)
7. **Server Hostname**: zuku-exam-server
8. **Deploy Now** 클릭

---

## 2. 서버 초기 설정

### SSH 접속

```bash
# IP는 Vultr 대시보드에서 확인
ssh root@YOUR_SERVER_IP
```

### 시스템 업데이트

```bash
# 패키지 목록 업데이트
apt update && apt upgrade -y

# 기본 유틸리티 설치
apt install -y curl wget git vim htop ufw
```

### 방화벽 설정

```bash
# UFW 방화벽 설정
ufw allow 22/tcp     # SSH
ufw allow 80/tcp     # HTTP
ufw allow 443/tcp    # HTTPS
ufw enable

# 상태 확인
ufw status verbose
```

### Docker 설치

```bash
# Docker 공식 스크립트로 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Docker 서비스 시작 및 자동 시작 설정
systemctl start docker
systemctl enable docker

# Docker Compose Plugin 설치
apt install -y docker-compose-plugin

# 설치 확인
docker --version
docker compose version
```

---

## 3. Swap 메모리 설정 (1GB RAM 필수)

**1GB RAM 서버에서는 Swap 메모리가 필수입니다!**

```bash
# 2GB Swap 파일 생성
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile

# 영구 적용 (재부팅 후에도 유지)
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# Swap 우선순위 조정 (메모리 부족 시에만 사용)
sysctl vm.swappiness=10
echo 'vm.swappiness=10' >> /etc/sysctl.conf

# Swap 상태 확인
free -h
swapon --show
```

**예상 출력:**
```
              total        used        free      shared  buff/cache   available
Mem:           985M        200M        500M         5M        285M        700M
Swap:          2.0G          0B        2.0G
```

---

## 4. 프로젝트 배포

### 프로젝트 클론

```bash
# /opt 디렉토리에 클론 (권장 위치)
cd /opt
git clone https://github.com/YOUR_USERNAME/zuku-exam-server.git
cd zuku-exam-server
```

### 환경 변수 설정

```bash
# .env 파일 생성
cp .env.example .env
vim .env
```

**.env 예시:**
```env
# API 인증 키 (필수)
API_KEY=your-secure-api-key-here

# 서버 포트
PORT=8080

# 환경 (production)
ENVIRONMENT=production
```

### Docker Compose로 실행

```bash
# 이미지 빌드 및 실행
docker compose up -d --build

# 로그 확인
docker compose logs -f
```

### 헬스체크

```bash
# API 정상 작동 확인
curl http://localhost:8080/health

# 예상 출력: {"status":"healthy","service":"exam-alignment-api"}
```

---

## 5. Nginx 설정

### Nginx 설치

```bash
apt install -y nginx
systemctl start nginx
systemctl enable nginx
```

### Nginx 설정 파일 생성

```bash
# 프로젝트의 샘플 파일 복사
cp /opt/zuku-exam-server/nginx.conf.sample /etc/nginx/sites-available/zuku-exam

# 도메인 수정 (your-domain.com을 실제 도메인으로 변경)
vim /etc/nginx/sites-available/zuku-exam
```

**수정해야 할 부분:**
- `your-domain.com` → 실제 도메인으로 변경 (예: `exam.example.com`)

### Nginx 설정 활성화

```bash
# 심볼릭 링크 생성
ln -s /etc/nginx/sites-available/zuku-exam /etc/nginx/sites-enabled/

# 기본 설정 비활성화 (선택사항)
rm /etc/nginx/sites-enabled/default

# 설정 검증
nginx -t

# Nginx 재시작
systemctl restart nginx
```

---

## 6. SSL 인증서 설정

### Certbot 설치

```bash
apt install -y certbot python3-certbot-nginx
```

### SSL 인증서 발급

```bash
# Certbot 자동 설정 (Nginx 설정 자동 수정)
certbot --nginx -d your-domain.com -d www.your-domain.com

# 이메일 입력 요청: 알림용 이메일 입력
# 약관 동의: Y
# 이메일 공유: N (선택사항)
```

### 자동 갱신 확인

```bash
# Certbot 타이머 상태 확인 (자동 갱신)
systemctl status certbot.timer

# 수동 갱신 테스트
certbot renew --dry-run
```

**자동 갱신은 이미 설정되어 있습니다!** (Certbot이 systemd timer로 자동 관리)

---

## 7. 자동 배포 설정

### 배포 스크립트 활용

프로젝트에 포함된 `deploy.sh`를 사용하면 간편하게 배포할 수 있습니다.

```bash
# 배포 스크립트 실행
cd /opt/zuku-exam-server
./deploy.sh
```

**deploy.sh가 하는 일:**
1. Git Pull (최신 코드)
2. Docker 이미지 재빌드
3. 컨테이너 재시작
4. 헬스체크
5. Docker 리소스 정리

### Git Webhook 설정 (고급)

GitHub Actions 또는 Webhook을 사용하여 Push 시 자동 배포 가능:

```bash
# GitHub Webhook Secret 설정
# POST /deploy 엔드포인트 구현 필요
```

---

## 8. 모니터링 및 관리

### 기본 명령어

```bash
# 컨테이너 상태 확인
docker compose ps

# 실시간 로그 확인
docker compose logs -f

# 메모리 사용량 확인
free -h
docker stats

# 대기열 상태 확인
curl http://localhost:8080/queue/status
```

### 로그 확인

```bash
# Docker 로그
docker compose logs --tail=100

# Nginx 로그
tail -f /var/log/nginx/zuku-exam-access.log
tail -f /var/log/nginx/zuku-exam-error.log

# 배포 로그
tail -f /var/log/zuku-deploy.log
```

### 시스템 리소스 모니터링

```bash
# htop으로 실시간 모니터링
htop

# 디스크 사용량
df -h

# Docker 리소스 정리
docker system prune -f
```

---

## 9. 트러블슈팅

### 메모리 부족 (OOM Killer)

**증상:**
- 컨테이너가 갑자기 종료됨
- `docker compose logs`에 메모리 관련 오류

**해결:**
```bash
# Swap 메모리 확인
free -h

# Swap이 없으면 섹션 3으로 돌아가 Swap 설정

# Docker 메모리 제한 확인
docker stats

# 동시 요청 수 확인
curl http://localhost:8080/queue/status
```

### SSL 인증서 갱신 실패

**증상:**
- HTTPS 접속 불가
- 인증서 만료 경고

**해결:**
```bash
# 수동 갱신 시도
certbot renew --force-renewal

# Nginx 재시작
systemctl restart nginx

# 로그 확인
journalctl -u certbot -n 50
```

### Docker 빌드 실패

**증상:**
- `docker compose up` 실패
- 이미지 빌드 오류

**해결:**
```bash
# Docker 캐시 삭제 후 재빌드
docker compose down
docker system prune -a -f
docker compose up -d --build --no-cache
```

### Nginx 502 Bad Gateway

**증상:**
- 웹 브라우저에서 502 에러

**해결:**
```bash
# FastAPI 컨테이너 상태 확인
docker compose ps

# 컨테이너 재시작
docker compose restart

# Nginx 설정 검증
nginx -t

# Nginx 재시작
systemctl restart nginx
```

### API 응답 느림

**증상:**
- 대기 시간 초과 에러
- 타임아웃 발생

**확인:**
```bash
# 대기열 상태 확인
curl http://localhost:8080/queue/status

# 현재 처리 중인 요청 확인
docker compose logs --tail=20 | grep "처리"
```

**해결:**
- 1GB RAM에서는 순차 처리가 정상 동작입니다
- 2개 이상 동시 요청 시 대기열에 추가됨
- 타임아웃 시간: 최대 120초 (수정 가능: `app/core/processing_limiter.py`)

---

## 📊 성능 최적화 팁

### 1GB RAM 서버

- ✅ Swap 메모리 필수 (2GB 권장)
- ✅ 순차 처리 (동시 1개)
- ✅ Docker 메모리 제한 (700MB)
- ⚠️ 배치 처리 제한 (최대 100개)

### 2GB RAM 서버

- ✅ 안정적인 운영 가능
- ✅ 동시 2개까지 처리 가능 (수정 필요)
- ✅ Swap 선택사항

---

## 🔗 유용한 링크

- [FastAPI 문서](https://fastapi.tiangolo.com/)
- [Docker Compose 문서](https://docs.docker.com/compose/)
- [Nginx 문서](https://nginx.org/en/docs/)
- [Let's Encrypt](https://letsencrypt.org/)

---

## 📞 문제 발생 시

1. GitHub Issues에 문제 제보
2. 로그 파일 첨부 (`docker compose logs`)
3. 서버 사양 및 메모리 상태 공유 (`free -h`)

---

**배포 완료!** 🎉

API 문서: `https://your-domain.com/docs`
대기열 상태: `https://your-domain.com/queue/status`
