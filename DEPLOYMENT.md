# Render 배포 가이드

시험지 정렬 및 채점 API 서버를 Render에 배포하는 방법입니다.

## 사전 준비

1. [Render 계정](https://render.com/) 생성
2. GitHub 저장소에 코드 푸시
3. API 키 준비 (`.env` 파일의 `API_KEY` 값)

## 배포 방법

### 방법 1: render.yaml 사용 (추천)

가장 간단하고 자동화된 방법입니다.

1. **GitHub 저장소 연결**
   - Render 대시보드에서 "New +" 클릭
   - "Blueprint" 선택
   - GitHub 저장소 연결 및 선택

2. **자동 감지**
   - `render.yaml` 파일을 자동으로 감지합니다
   - 설정을 확인하고 "Apply" 클릭

3. **환경 변수 설정**
   - 대시보드에서 서비스 선택
   - "Environment" 탭으로 이동
   - `API_KEY` 환경 변수 추가:
     ```
     API_KEY=your-secure-api-key-here
     ```
   - "Save Changes" 클릭

4. **배포 완료**
   - 자동으로 빌드 및 배포가 시작됩니다
   - 배포 완료 후 제공되는 URL로 접근 가능

### 방법 2: 수동 설정

1. **새 Web Service 생성**
   - Render 대시보드에서 "New +" → "Web Service" 클릭
   - GitHub 저장소 선택

2. **서비스 설정**
   ```
   Name: zuku-exam-server
   Region: Singapore (또는 원하는 리전)
   Branch: main
   Runtime: Docker
   Instance Type: Free
   ```

3. **빌드 설정**
   ```
   Dockerfile Path: ./Dockerfile
   Docker Build Context Directory: .
   ```

4. **환경 변수 설정**
   ```
   API_KEY=your-secure-api-key-here
   ENVIRONMENT=production
   HOST=0.0.0.0
   ```

5. **고급 설정**
   ```
   Health Check Path: /health
   Auto-Deploy: Yes
   ```

6. **"Create Web Service" 클릭**

## 배포 후 확인

### 1. 헬스체크
```bash
curl https://your-app.onrender.com/health
```

**예상 응답:**
```json
{
  "status": "healthy",
  "service": "exam-alignment-api"
}
```

### 2. API 문서 확인
브라우저에서 접속:
```
https://your-app.onrender.com/docs
```

### 3. API 테스트
```bash
curl -X POST "https://your-app.onrender.com/api/align" \
  -H "X-API-Key: your-api-key" \
  -F "scan=@test-image.jpg"
```

## 환경 변수 관리

### 필수 환경 변수

| 변수명 | 설명 | 예시 |
|--------|------|------|
| `API_KEY` | API 인증 키 | `fgu9AoIWnf-QLnisfLmAxTw9LR17Kn7jJmEh3uuqDkc` |

### 선택 환경 변수

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `ENVIRONMENT` | 실행 환경 | `production` |
| `HOST` | 바인딩 호스트 | `0.0.0.0` |
| `PORT` | 포트 번호 | Render가 자동 설정 |

### 환경 변수 업데이트 방법

1. Render 대시보드에서 서비스 선택
2. "Environment" 탭 클릭
3. 환경 변수 수정/추가
4. "Save Changes" 클릭 → 자동 재배포

## 자동 배포

`render.yaml` 파일에서 `autoDeploy: true` 설정 시:
- `main` 브랜치에 푸시하면 자동 배포
- 배포 상태는 대시보드에서 확인

수동 배포가 필요한 경우:
```bash
git push origin main
```

## 로그 확인

1. Render 대시보드에서 서비스 선택
2. "Logs" 탭 클릭
3. 실시간 로그 확인

또는 CLI 사용:
```bash
render logs -s zuku-exam-server
```

## 비용

### Free 플랜
- 무료
- 750시간/월
- 512MB RAM
- 비활성 시 자동 슬립 (요청 시 재시작, 약 30초 소요)
- 대역폭 제한 있음

### Starter 플랜 (~$7/월)
- 무제한 활성 시간
- 512MB RAM
- 슬립 없음
- 더 많은 대역폭

### Standard 플랜 (~$25/월)
- 2GB RAM
- 더 높은 성능
- 더 많은 대역폭

자세한 가격은 [Render 가격 페이지](https://render.com/pricing)에서 확인하세요.

## 커스텀 도메인 연결

1. Render 대시보드에서 서비스 선택
2. "Settings" 탭 클릭
3. "Custom Domain" 섹션에서 도메인 추가
4. DNS 설정에 CNAME 레코드 추가:
   ```
   CNAME: your-domain.com → your-app.onrender.com
   ```

## 모니터링

### Render 내장 모니터링
- 대시보드에서 CPU, 메모리, 네트워크 사용량 확인
- 헬스체크 상태 확인
- 배포 히스토리 확인

### 외부 모니터링 (선택사항)
- [UptimeRobot](https://uptimerobot.com/) - 가동 시간 모니터링
- [Better Stack](https://betterstack.com/) - 로그 관리
- [Sentry](https://sentry.io/) - 에러 추적

## 문제 해결

### 배포 실패
1. 로그 확인: "Logs" 탭에서 에러 메시지 확인
2. Dockerfile 검증: 로컬에서 Docker 빌드 테스트
   ```bash
   docker build -t zuku-exam-server .
   docker run -p 8080:8080 -e API_KEY=test zuku-exam-server
   ```

### API 키 에러
- Render 대시보드에서 환경 변수 `API_KEY`가 올바르게 설정되었는지 확인
- 환경 변수 수정 후 재배포 필요

### 헬스체크 실패
- `/health` 엔드포인트가 정상 작동하는지 확인
- 포트 설정이 올바른지 확인

### 느린 응답 (Free 플랜)
- Free 플랜은 비활성 시 슬립 상태가 됩니다
- 첫 요청 시 30초 정도 소요될 수 있습니다
- Starter 이상 플랜으로 업그레이드하면 해결됩니다

## 보안 권장사항

1. **API 키 관리**
   - API 키를 주기적으로 변경
   - 노출된 경우 즉시 재생성

2. **CORS 설정**
   - `main.py`에서 `allow_origins`를 특정 도메인으로 제한
   ```python
   allow_origins=["https://your-frontend.com"]
   ```

3. **Rate Limiting** (선택사항)
   - `slowapi` 라이브러리 사용 고려

4. **HTTPS**
   - Render는 자동으로 SSL 인증서 제공

## 참고 자료

- [Render 공식 문서](https://render.com/docs)
- [Docker 배포 가이드](https://render.com/docs/deploy-docker)
- [환경 변수 설정](https://render.com/docs/environment-variables)
- [커스텀 도메인](https://render.com/docs/custom-domains)
