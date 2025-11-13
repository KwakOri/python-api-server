# 로그 관리 설정 가이드

## 1. 로그 로테이션 설정

### Nginx 로그 로테이션

```bash
# 서버에서 실행
sudo cp /opt/zuku-exam-server/logrotate.conf /etc/logrotate.d/zuku-exam

# 권한 설정
sudo chmod 644 /etc/logrotate.d/zuku-exam

# 테스트 실행
sudo logrotate -d /etc/logrotate.d/zuku-exam

# 수동 실행 (테스트)
sudo logrotate -f /etc/logrotate.d/zuku-exam
```

### Docker 로그 확인

Docker 로그는 `docker-compose.yml`에서 이미 설정됨:
- 최대 파일 크기: 10MB
- 최대 파일 수: 3개
- 총 30MB까지만 저장

```bash
# Docker 로그 확인
docker compose logs -f

# 특정 시간 이후 로그
docker compose logs --since 1h

# 마지막 100줄
docker compose logs --tail=100
```

---

## 2. 로그 분석 스크립트 사용

```bash
# 실행 권한 부여
chmod +x /opt/zuku-exam-server/scripts/check_logs.sh

# 실행
/opt/zuku-exam-server/scripts/check_logs.sh
```

### Cron으로 정기 실행 (선택사항)

```bash
# crontab 편집
sudo crontab -e

# 매일 오전 9시에 로그 분석 실행 (이메일로 결과 전송)
0 9 * * * /opt/zuku-exam-server/scripts/check_logs.sh > /tmp/log_check.txt 2>&1
```

---

## 3. 실시간 로그 모니터링

### Docker 로그 실시간 확인

```bash
# 전체 로그
docker compose logs -f

# 에러만 필터링
docker compose logs -f | grep -i "error\|exception"

# 특정 시간 이후
docker compose logs -f --since 1h
```

### Nginx 로그 실시간 확인

```bash
# Access 로그
tail -f /var/log/nginx/zuku-exam-access.log

# Error 로그
tail -f /var/log/nginx/zuku-exam-error.log

# 에러만 필터링
tail -f /var/log/nginx/zuku-exam-error.log | grep "error"
```

---

## 4. 로그 위치

| 로그 종류 | 위치 | 용도 |
|----------|------|------|
| Docker 로그 | `docker compose logs` | 애플리케이션 로그 |
| Nginx Access | `/var/log/nginx/zuku-exam-access.log` | HTTP 요청 로그 |
| Nginx Error | `/var/log/nginx/zuku-exam-error.log` | Nginx 에러 로그 |
| System 로그 | `/var/log/syslog` | 시스템 전체 로그 |

---

## 5. 디스크 공간 관리

### 현재 사용량 확인

```bash
# 전체 디스크
df -h

# 로그 디렉토리
du -sh /var/log/nginx/
du -sh /var/lib/docker/
```

### 오래된 로그 수동 삭제

```bash
# 7일 이상 된 압축 로그 삭제
find /var/log/nginx/ -name "*.gz" -mtime +7 -delete

# Docker 로그 정리
docker system prune -f
```

---

## 6. 주요 명령어 요약

```bash
# 로그 분석 스크립트
/opt/zuku-exam-server/scripts/check_logs.sh

# Docker 로그 (최근 50줄)
docker compose logs --tail=50

# Docker 로그 (에러만)
docker compose logs | grep -i error

# Nginx 에러 로그
tail -20 /var/log/nginx/zuku-exam-error.log

# 디스크 사용량
df -h

# 메모리 사용량
free -h

# 컨테이너 상태
docker compose ps
```
