# 알림톡 API 사용 가이드 (프론트엔드)

이 문서는 프론트엔드에서 알림톡 API를 호출하는 방법을 설명합니다.

## 📋 목차

- [기본 정보](#기본-정보)
- [인증](#인증)
- [API 엔드포인트](#api-엔드포인트)
- [요청 예제](#요청-예제)
- [응답 형식](#응답-형식)
- [에러 처리](#에러-처리)
- [코드 예제](#코드-예제)

---

## 기본 정보

### Base URL
```
https://your-api-server.fly.dev
# 로컬 개발: http://localhost:8080
```

### Content-Type
```
application/json
```

---

## 인증

모든 POST 요청은 API 키 인증이 필요합니다.

### 헤더 설정
```
X-API-Key: your-api-key-here
```

---

## API 엔드포인트

### 1. 알림톡 발송

**POST** `/api/alimtok/send`

카카오 알림톡 메시지를 발송합니다.

#### 요청 Body

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `sendProfileId` | string | ✅ | 채널 ID |
| `templateId` | string | ✅ | 템플릿 ID |
| `to` | array | ✅ | 수신자 정보 (최대 1,000명) |
| `reservation` | object | ❌ | 예약 발송 설정 |
| `useCredit` | boolean | ❌ | 크레딧 우선 사용 (기본값: true) |
| `fallback` | object | ❌ | 대체문자 설정 |

#### 수신자 정보 (`to`) 형식

**변수 없는 경우:**
```json
["01012345678", "01087654321"]
```

**변수 있는 경우:**
```json
[
  {
    "phone": "01012345678",
    "variables": {
      "#{고객명}": "홍길동",
      "#{날짜}": "2024-01-01"
    }
  }
]
```

---

### 2. 서비스 상태 확인

**GET** `/api/alimtok/health`

알림톡 서비스의 상태를 확인합니다. (인증 불필요)

---

## 요청 예제

### 1. 기본 발송 (변수 없음)

```json
{
  "sendProfileId": "231edu",
  "templateId": "351J9e9RAH1GdhPQGVgM8HFpBgA",
  "to": ["01012345678", "01087654321"]
}
```

### 2. 변수 포함 발송

```json
{
  "sendProfileId": "231edu",
  "templateId": "351J9e9RAH1GdhPQGVgM8HFpBgA",
  "to": [
    {
      "phone": "01055952289",
      "variables": {
        "#{report_id}": "1000",
        "#{student_id}": "1000",
        "#{student}": "김국어",
        "#{start_date}": "2025-11-10",
        "#{end_date}": "2025-11-16"
      }
    }
  ]
}
```

### 3. 예약 발송

```json
{
  "sendProfileId": "231edu",
  "templateId": "351J9e9RAH1GdhPQGVgM8HFpBgA",
  "to": ["01012345678"],
  "reservation": {
    "reservedAt": "2024-12-25T09:00:00+09:00"
  }
}
```

### 4. 대체문자 설정 (LMS)

```json
{
  "sendProfileId": "231edu",
  "templateId": "351J9e9RAH1GdhPQGVgM8HFpBgA",
  "to": ["01012345678"],
  "fallback": {
    "fallbackType": "CUSTOM",
    "custom": {
      "type": "LMS",
      "senderNumber": "02-1234-5678",
      "title": "알림",
      "message": "알림톡 발송이 실패하여 문자로 발송합니다.",
      "isAd": false
    }
  }
}
```

---

## 응답 형식

### 성공 응답 (200)

```json
{
  "code": 200,
  "message": "요청이 성공했습니다",
  "data": {
    "groupId": "발송-그룹-ID"
  }
}
```

### 에러 응답 (4xx, 5xx)

```json
{
  "detail": {
    "code": 400,
    "message": "에러 메시지",
    "data": {}
  }
}
```

---

## 에러 처리

### 주요 에러 코드

| HTTP 상태 | 센드온 코드 | 설명 | 해결 방법 |
|-----------|-------------|------|-----------|
| 401 | - | API 키 인증 실패 | X-API-Key 헤더 확인 |
| 400 | 400 | 잘못된 요청 | 요청 파라미터 확인 |
| 400 | 403 | 센드온 API 키 오류 | 서버 관리자에게 문의 |
| 400 | 422 | 요청 데이터 형식 오류 | JSON 형식 확인 |
| 500 | 500 | 서버 내부 오류 | 서버 관리자에게 문의 |

---

## 코드 예제

### JavaScript (Fetch API)

```javascript
async function sendAlimtok(recipients, variables) {
  const response = await fetch('https://your-api-server.fly.dev/api/alimtok/send', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': 'your-api-key-here'
    },
    body: JSON.stringify({
      sendProfileId: '231edu',
      templateId: '351J9e9RAH1GdhPQGVgM8HFpBgA',
      to: recipients.map(phone => ({
        phone,
        variables
      }))
    })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail?.message || '알림톡 발송 실패');
  }

  return await response.json();
}

// 사용 예시
try {
  const result = await sendAlimtok(
    ['01012345678'],
    {
      '#{report_id}': '1000',
      '#{student}': '김국어',
      '#{start_date}': '2025-11-10',
      '#{end_date}': '2025-11-16'
    }
  );
  console.log('발송 성공:', result);
} catch (error) {
  console.error('발송 실패:', error.message);
}
```

### TypeScript + Axios

```typescript
import axios, { AxiosError } from 'axios';

interface AlimtokVariables {
  [key: string]: string;
}

interface AlimtokRecipient {
  phone: string;
  variables: AlimtokVariables;
}

interface AlimtokRequest {
  sendProfileId: string;
  templateId: string;
  to: (string | AlimtokRecipient)[];
  reservation?: {
    reservedAt: string;
  };
  useCredit?: boolean;
  fallback?: {
    fallbackType: 'NONE' | 'TEMPLATE' | 'CUSTOM';
    custom?: {
      type: 'SMS' | 'LMS' | 'MMS';
      senderNumber: string;
      message: string;
      isAd: boolean;
      title?: string;
      images?: string[];
    };
  };
}

interface AlimtokResponse {
  code: number;
  message: string;
  data?: {
    groupId: string;
  };
}

const API_BASE_URL = 'https://your-api-server.fly.dev';
const API_KEY = 'your-api-key-here';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY
  }
});

async function sendAlimtok(
  phoneNumbers: string[],
  variables: AlimtokVariables,
  templateId: string = '351J9e9RAH1GdhPQGVgM8HFpBgA'
): Promise<AlimtokResponse> {
  try {
    const request: AlimtokRequest = {
      sendProfileId: '231edu',
      templateId,
      to: phoneNumbers.map(phone => ({
        phone,
        variables
      }))
    };

    const response = await apiClient.post<AlimtokResponse>(
      '/api/alimtok/send',
      request
    );

    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError<{ detail: { message: string } }>;
      throw new Error(
        axiosError.response?.data?.detail?.message || '알림톡 발송 실패'
      );
    }
    throw error;
  }
}

// 사용 예시
async function example() {
  try {
    const result = await sendAlimtok(
      ['01012345678'],
      {
        '#{report_id}': '1000',
        '#{student_id}': '1000',
        '#{student}': '김국어',
        '#{start_date}': '2025-11-10',
        '#{end_date}': '2025-11-16'
      }
    );
    console.log('발송 성공:', result);
  } catch (error) {
    console.error('발송 실패:', error);
  }
}
```

### React Hook

```typescript
import { useState } from 'react';
import axios from 'axios';

interface AlimtokVariables {
  [key: string]: string;
}

interface UseAlimtokReturn {
  send: (phoneNumbers: string[], variables: AlimtokVariables) => Promise<void>;
  loading: boolean;
  error: string | null;
  success: boolean;
}

export function useAlimtok(
  apiBaseUrl: string,
  apiKey: string,
  sendProfileId: string,
  templateId: string
): UseAlimtokReturn {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const send = async (
    phoneNumbers: string[],
    variables: AlimtokVariables
  ) => {
    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      await axios.post(
        `${apiBaseUrl}/api/alimtok/send`,
        {
          sendProfileId,
          templateId,
          to: phoneNumbers.map(phone => ({
            phone,
            variables
          }))
        },
        {
          headers: {
            'Content-Type': 'application/json',
            'X-API-Key': apiKey
          }
        }
      );

      setSuccess(true);
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.detail?.message || '알림톡 발송 실패';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return { send, loading, error, success };
}

// 사용 예시
function MyComponent() {
  const { send, loading, error, success } = useAlimtok(
    'https://your-api-server.fly.dev',
    'your-api-key-here',
    '231edu',
    '351J9e9RAH1GdhPQGVgM8HFpBgA'
  );

  const handleSend = async () => {
    try {
      await send(['01012345678'], {
        '#{report_id}': '1000',
        '#{student}': '김국어',
        '#{start_date}': '2025-11-10',
        '#{end_date}': '2025-11-16'
      });
      alert('알림톡 발송 성공!');
    } catch (error) {
      alert('알림톡 발송 실패');
    }
  };

  return (
    <div>
      <button onClick={handleSend} disabled={loading}>
        {loading ? '발송 중...' : '알림톡 발송'}
      </button>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {success && <p style={{ color: 'green' }}>발송 성공!</p>}
    </div>
  );
}
```

### Next.js API Route (Server-Side)

```typescript
// pages/api/send-alimtok.ts
import type { NextApiRequest, NextApiResponse } from 'next';
import axios from 'axios';

const API_BASE_URL = process.env.ALIMTOK_API_URL!;
const API_KEY = process.env.ALIMTOK_API_KEY!;

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { phoneNumbers, variables, templateId } = req.body;

  try {
    const response = await axios.post(
      `${API_BASE_URL}/api/alimtok/send`,
      {
        sendProfileId: '231edu',
        templateId: templateId || '351J9e9RAH1GdhPQGVgM8HFpBgA',
        to: phoneNumbers.map((phone: string) => ({
          phone,
          variables
        }))
      },
      {
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': API_KEY
        }
      }
    );

    res.status(200).json(response.data);
  } catch (error: any) {
    console.error('알림톡 발송 실패:', error);
    res.status(500).json({
      error: error.response?.data?.detail?.message || '알림톡 발송 실패'
    });
  }
}
```

```typescript
// 클라이언트에서 호출
async function sendAlimtokFromClient() {
  const response = await fetch('/api/send-alimtok', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      phoneNumbers: ['01012345678'],
      variables: {
        '#{report_id}': '1000',
        '#{student}': '김국어',
        '#{start_date}': '2025-11-10',
        '#{end_date}': '2025-11-16'
      }
    })
  });

  if (!response.ok) {
    throw new Error('알림톡 발송 실패');
  }

  return await response.json();
}
```

---

## 환경 변수 설정

### .env.local (Next.js)

```bash
# 알림톡 API 설정
ALIMTOK_API_URL=https://your-api-server.fly.dev
ALIMTOK_API_KEY=your-api-key-here
```

### 주의사항

⚠️ **API 키를 클라이언트 코드에 노출하지 마세요!**

- ✅ 서버 사이드에서 API 호출 (Next.js API Routes, Express 등)
- ✅ 환경 변수에 API 키 저장
- ❌ 클라이언트 번들에 API 키 포함

---

## 테스트

### Swagger UI
http://localhost:8080/docs

### cURL 테스트

```bash
curl -X POST "http://localhost:8080/api/alimtok/send" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "sendProfileId": "231edu",
    "templateId": "351J9e9RAH1GdhPQGVgM8HFpBgA",
    "to": [
      {
        "phone": "01012345678",
        "variables": {
          "#{report_id}": "1000",
          "#{student}": "김국어",
          "#{start_date}": "2025-11-10",
          "#{end_date}": "2025-11-16"
        }
      }
    ]
  }'
```

---

## 문의

API 관련 문의사항은 서버 관리자에게 연락하세요.

- API 문서: http://localhost:8080/docs
- Health Check: http://localhost:8080/health
