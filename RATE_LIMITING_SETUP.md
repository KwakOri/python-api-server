# Rate Limiting 설정 가이드

API 남용을 방지하고 서버를 보호하기 위한 Rate Limiting 설정 가이드입니다.

---

## 📋 Rate Limiting 전략

| 엔드포인트 | 제한 | 이유 |
|------------|------|------|
| `/health` | 제한 없음 | 모니터링용 |
| `/docs`, `/redoc` | 초당 5개, 버스트 10개 | 문서 열람 |
| `/api/align`, `/api/grade` | **분당 2개**, 버스트 2개 | 이미지 처리 무거움 |
| 기타 `/api/*` | 초당 10개, 버스트 20개 | 일반 API |
| 기타 경로 | 제한 없음 | 메인 페이지 등 |

---

## 🔧 설정 방법

### 1단계: Nginx HTTP 블록에 Zone 추가

```bash
# 서버에서 실행
sudo vim /etc/nginx/nginx.conf
```

**http 블록 안에 추가:**

```nginx
http {
    # ... 기존 설정 ...

    # Rate Limiting Zone 정의
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=upload_limit:10m rate=2r/m;

    # ... 나머지 설정 ...
}
```

**설명:**
- `$binary_remote_addr`: 클라이언트 IP 주소
- `zone=api_limit:10m`: 메모리 10MB 할당 (약 16만 개 IP 추적 가능)
- `rate=10r/s`: 초당 10개 요청
- `rate=2r/m`: 분당 2개 요청

### 2단계: Nginx 사이트 설정 업데이트

```bash
# 기존 설정 백업
sudo cp /etc/nginx/sites-available/zuku-exam /etc/nginx/sites-available/zuku-exam.backup

# 새 설정 복사
sudo cp /opt/zuku-exam-server/nginx-with-rate-limit.conf /etc/nginx/sites-available/zuku-exam

# 설정 검증
sudo nginx -t

# Nginx 재시작
sudo systemctl restart nginx
```

---

## 🧪 테스트

### 일반 API 테스트

```bash
# 초당 10개까지 허용
for i in {1..15}; do
  curl -s https://exam.231edu.cloud/ | head -1
  echo " - Request $i"
done
```

**예상 결과:**
- 처음 10-20개: 정상 응답
- 그 이후: `429 Too Many Requests`

### 이미지 업로드 API 테스트

```bash
# 분당 2개까지 허용
for i in {1..5}; do
  curl -X POST https://exam.231edu.cloud/api/align \
    -F "scan=@test.jpg" \
    -F "method=sift" \
    -w "\nStatus: %{http_code}\n"
  echo "Request $i"
  sleep 1
done
```

**예상 결과:**
- 처음 2개: 200 OK
- 3번째부터: 429 Too Many Requests

---

## 📊 Rate Limit 응답 예시

### 정상 응답
```json
{
  "service": "시험지 정렬 및 채점 API",
  "version": "1.0.0",
  ...
}
```

### Rate Limit 초과
```
HTTP/1.1 429 Too Many Requests

{
  "error": "Too Many Requests",
  "message": "요청이 너무 많습니다. 잠시 후 다시 시도해주세요.",
  "retry_after": 60
}
```

---

## 🔍 Rate Limiting 확인

### Nginx 로그 확인

```bash
# Rate Limit 초과 로그 확인
sudo tail -f /var/log/nginx/zuku-exam-error.log | grep "limiting requests"
```

**예시 로그:**
```
2025/11/13 10:30:15 [warn] 1234#1234: *5678 limiting requests, excess: 20.500 by zone "api_limit", client: 1.2.3.4
```

### 실시간 모니터링 스크립트

```bash
#!/bin/bash
# /opt/zuku-exam-server/scripts/monitor_rate_limit.sh

watch -n 1 'tail -20 /var/log/nginx/zuku-exam-error.log | grep "limiting requests" | tail -5'
```

---

## ⚙️ Rate Limit 조정

상황에 맞게 조정하세요:

### 더 엄격하게 (보안 강화)

```nginx
# nginx.conf
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=5r/s;      # 초당 5개
limit_req_zone $binary_remote_addr zone=upload_limit:10m rate=1r/m;   # 분당 1개
```

### 더 완화 (사용자 편의)

```nginx
# nginx.conf
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=20r/s;     # 초당 20개
limit_req_zone $binary_remote_addr zone=upload_limit:10m rate=5r/m;   # 분당 5개
```

### 특정 IP 화이트리스트

```nginx
# Nginx 사이트 설정
geo $limit {
    default 1;
    # 내부 IP는 제한 없음
    192.168.1.0/24 0;
    10.0.0.0/8 0;
}

map $limit $limit_key {
    0 "";
    1 $binary_remote_addr;
}

limit_req_zone $limit_key zone=api_limit:10m rate=10r/s;
```

---

## 🎯 버스트(Burst) 설정 이해

```nginx
limit_req zone=api_limit burst=20 nodelay;
```

- **burst=20**: 순간적으로 20개까지 버퍼링
- **nodelay**: 버퍼링된 요청을 즉시 처리 (지연 없음)
- 없으면: 초과 요청은 대기열에서 천천히 처리

### 예시

**rate=10r/s, burst=20:**
- 순간 30개 요청 → 처음 30개 허용, 31번째부터 거부
- 1초 후 → 다시 10개 허용

**rate=10r/s, burst=0:**
- 순간 15개 요청 → 처음 10개만 허용, 11번째부터 즉시 거부

---

## 📈 통계 확인

### 최근 1시간 Rate Limit 발생 횟수

```bash
# 서버에서
sudo grep "limiting requests" /var/log/nginx/zuku-exam-error.log | \
  grep "$(date -u +%d/%b/%Y:%H -d '1 hour ago')" | wc -l
```

### IP별 Rate Limit 통계

```bash
sudo grep "limiting requests" /var/log/nginx/zuku-exam-error.log | \
  grep -oP 'client: \K[\d.]+' | sort | uniq -c | sort -rn | head -10
```

---

## 🚨 문제 해결

### Rate Limit이 작동하지 않음

1. **Zone 정의 확인**
   ```bash
   sudo nginx -t
   sudo grep "limit_req_zone" /etc/nginx/nginx.conf
   ```

2. **Nginx 재시작**
   ```bash
   sudo systemctl restart nginx
   ```

3. **로그 확인**
   ```bash
   sudo tail -f /var/log/nginx/error.log
   ```

### 정상 사용자도 차단됨

- **burst 값 증가**
- **rate 값 증가**
- 특정 IP 화이트리스트 추가

---

## 📝 권장 설정 요약

### 프로덕션 환경

```nginx
# nginx.conf
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=upload_limit:10m rate=2r/m;

# 사이트 설정
location /api/align {
    limit_req zone=upload_limit burst=2 nodelay;
}

location /api/ {
    limit_req zone=api_limit burst=20 nodelay;
}
```

### 개발/테스트 환경

```nginx
# 더 완화된 설정
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=50r/s;
limit_req_zone $binary_remote_addr zone=upload_limit:10m rate=10r/m;
```

---

## ✅ 적용 체크리스트

- [ ] `/etc/nginx/nginx.conf`에 zone 정의 추가
- [ ] `/etc/nginx/sites-available/zuku-exam` 업데이트
- [ ] `nginx -t` 설정 검증
- [ ] Nginx 재시작
- [ ] 테스트 실행 (curl)
- [ ] 로그 확인
- [ ] Rate Limit 동작 확인

---

완료 시간: **20분**
