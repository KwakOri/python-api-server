# 헬스체크 모니터링 설정 가이드

서버 다운 시 즉시 알림을 받기 위한 모니터링 서비스 설정 가이드입니다.

---

## 1️⃣ UptimeRobot 설정 (권장 - 무료)

### 가입 및 설정

1. **가입**
   - https://uptimerobot.com 접속
   - 무료 계정 가입 (이메일 인증)

2. **모니터 추가**
   - Dashboard → **Add New Monitor** 클릭

3. **모니터 설정**
   ```
   Monitor Type: HTTP(s)
   Friendly Name: Zuku Exam Server - Health
   URL: https://exam.231edu.cloud/health
   Monitoring Interval: 5 minutes (무료 플랜)
   Monitor Timeout: 30 seconds
   ```

4. **알림 설정**
   - **Alert Contacts** 탭
   - **Add Alert Contact** 클릭
   - 이메일, SMS, Telegram, Discord, Slack 중 선택

### 권장 알림 채널

#### A. 이메일 (기본)
```
Type: E-mail
E-mail: your-email@example.com
```

#### B. Telegram (권장)
```
1. Telegram에서 @BotFather 검색
2. /newbot 명령어로 봇 생성
3. Bot Token 받기
4. @userinfobot에서 Chat ID 확인
5. UptimeRobot에 입력
```

#### C. Discord Webhook
```
1. Discord 서버 → 서버 설정 → 통합
2. 웹후크 만들기
3. 웹후크 URL 복사
4. UptimeRobot에 입력
```

---

## 2️⃣ BetterStack (Uptime.com) - 고급 기능

더 자세한 모니터링이 필요하다면:

1. https://betterstack.com 가입
2. 무료 플랜: 10개 모니터, 3분 간격
3. 더 많은 기능:
   - Status Page 제공
   - 상세한 다운타임 분석
   - 여러 지역에서 동시 체크

---

## 3️⃣ 직접 구현 (간단한 스크립트)

### 서버 헬스체크 스크립트

`/opt/zuku-exam-server/scripts/health_check.sh`:

```bash
#!/bin/bash

URL="https://exam.231edu.cloud/health"
EXPECTED="healthy"

# 헬스체크 요청
RESPONSE=$(curl -s "$URL")

# 응답 확인
if echo "$RESPONSE" | grep -q "$EXPECTED"; then
    echo "✅ 서버 정상: $(date)"
    exit 0
else
    echo "❌ 서버 이상: $(date)"
    echo "Response: $RESPONSE"

    # 이메일 발송 (선택사항)
    # echo "Server Down: $RESPONSE" | mail -s "Server Alert" your-email@example.com

    exit 1
fi
```

### Cron으로 5분마다 실행

```bash
# 실행 권한 부여
chmod +x /opt/zuku-exam-server/scripts/health_check.sh

# Crontab 설정
crontab -e

# 5분마다 실행
*/5 * * * * /opt/zuku-exam-server/scripts/health_check.sh >> /var/log/health_check.log 2>&1
```

---

## 4️⃣ 모니터링 항목

### 기본 모니터링

| URL | 목적 | 예상 응답 |
|-----|------|-----------|
| `https://exam.231edu.cloud/health` | API 서버 상태 | `{"status":"healthy"}` |
| `https://exam.231edu.cloud/` | 기본 응답 | `{"service":"..."}` |

### 추가 모니터링 (선택)

```
https://exam.231edu.cloud/docs  → Swagger UI 접근 가능 확인
```

---

## 5️⃣ Status Page 만들기 (선택)

### UptimeRobot Status Page

1. Dashboard → **Public Status Pages**
2. **Create Public Status Page**
3. 모니터 선택
4. 공개 URL 생성: `https://stats.uptimerobot.com/xxxxx`

사용자들이 현재 서버 상태를 실시간으로 확인 가능!

---

## 6️⃣ 알림 테스트

### UptimeRobot에서 테스트

1. 모니터 선택
2. **3점 메뉴** → **Pause**
3. 알림 수신 확인
4. 다시 **Resume**

### 수동 테스트

```bash
# 서버 중지
docker compose down

# 1-2분 후 알림 확인

# 서버 재시작
docker compose up -d
```

---

## 7️⃣ 권장 설정 요약

### 무료로 시작하기

**UptimeRobot (무료)**
- Monitor 1: `https://exam.231edu.cloud/health`
- Interval: 5분
- Alert: 이메일

### 더 자세한 모니터링

**BetterStack (무료/유료)**
- Monitor 1: Health endpoint
- Monitor 2: Main page
- Interval: 3분 (무료) / 30초 (유료)
- Alert: Telegram, Discord, Slack
- Status Page 제공

---

## 8️⃣ 모니터링 대시보드 예시

```
✅ Zuku Exam Server - Health
   Last Check: 2 minutes ago
   Uptime: 99.9%
   Response Time: 45ms

📊 Statistics (30 days)
   Uptime: 99.8%
   Avg Response Time: 52ms
   Downtime: 1h 32m
   Incidents: 2
```

---

## 9️⃣ 추천 설정

1. **UptimeRobot 설정** (5분)
   - https://exam.231edu.cloud/health 모니터링
   - 이메일 알림

2. **Telegram 연동** (10분)
   - 봇 생성 및 연결
   - 즉시 푸시 알림

3. **Status Page 생성** (5분)
   - 공개 상태 페이지
   - 팀원/사용자 공유

**총 소요 시간: 20분**

---

## 🔔 알림 예시

### 다운타임 알림
```
🔴 Zuku Exam Server is DOWN
URL: https://exam.231edu.cloud/health
Time: 2025-11-13 10:30:00 UTC
Reason: Connection timeout
```

### 복구 알림
```
🟢 Zuku Exam Server is UP
URL: https://exam.231edu.cloud/health
Time: 2025-11-13 10:35:00 UTC
Downtime: 5 minutes
```
