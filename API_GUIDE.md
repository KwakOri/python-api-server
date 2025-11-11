# API 사용 가이드 (프론트엔드)

## 기본 정보

**Base URL**: `https://your-app.onrender.com`
**인증 방식**: API Key (HTTP Header)
**Content-Type**: `multipart/form-data`

## 인증

모든 POST 요청에는 API 키가 필요합니다.

```http
X-API-Key: your-api-key-here
```

## 엔드포인트

### 1. 이미지 정렬

#### POST `/api/align`

스캔된 시험지 이미지를 정렬합니다.

**요청**
```javascript
const formData = new FormData();
formData.append('scan', imageFile);           // 필수: 이미지 파일
formData.append('method', 'sift');            // 선택: 'sift' 또는 'contour' (기본: 'sift')
formData.append('enhance', 'true');           // 선택: 이미지 품질 개선 (기본: true)
formData.append('return_image', 'false');     // 선택: 이미지 반환 여부 (기본: false)

const response = await fetch('https://your-app.onrender.com/api/align', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your-api-key-here'
  },
  body: formData
});

const result = await response.json();
```

**응답 (return_image=false)**
```json
{
  "success": true,
  "message": "이미지 정렬 완료",
  "metadata": {
    "success": true,
    "method": "sift",
    "width": 1200,
    "height": 1800,
    "processing_time": 2.5
  }
}
```

**응답 (return_image=true)**
- Content-Type: `image/png`
- 정렬된 이미지 바이너리 데이터

---

### 2. OMR 답안 검출

#### POST `/api/grade/detect`

마킹된 답안만 검출합니다 (채점하지 않음).

**요청**
```javascript
const formData = new FormData();
formData.append('scan', imageFile);           // 필수: 이미지 파일
formData.append('method', 'sift');            // 선택: 정렬 방식 (기본: 'sift')
formData.append('threshold', '0.35');         // 선택: 마킹 임계값 (기본: 0.35)

const response = await fetch('https://your-app.onrender.com/api/grade/detect', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your-api-key-here'
  },
  body: formData
});

const result = await response.json();
```

**응답**
```json
{
  "success": true,
  "message": "답안 검출 완료",
  "detected_answers": {
    "1": 2,
    "2": 4,
    "3": null,
    "4": 1,
    ...
  },
  "statistics": {
    "total_questions": 45,
    "answered": 42,
    "blank": 3
  }
}
```

---

### 3. OMR 자동 채점

#### POST `/api/grade`

답안을 검출하고 정답과 비교하여 채점합니다.

**요청**
```javascript
const formData = new FormData();
formData.append('scan', imageFile);                              // 필수: 이미지 파일
formData.append('answer_key', JSON.stringify([1,2,3,4,5,...])); // 필수: 정답 배열 (45개)
formData.append('method', 'sift');                               // 선택: 정렬 방식
formData.append('threshold', '0.35');                            // 선택: 마킹 임계값
formData.append('score_per_question', '1.0');                    // 선택: 문제당 배점

const response = await fetch('https://your-app.onrender.com/api/grade', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your-api-key-here'
  },
  body: formData
});

const result = await response.json();
```

**응답**
```json
{
  "success": true,
  "message": "채점 완료",
  "grading": {
    "student_answers": {
      "1": 2,
      "2": 4,
      ...
    },
    "correct_count": 38,
    "wrong_count": 5,
    "blank_count": 2,
    "total_score": 38.0,
    "max_score": 45.0,
    "percentage": 84.44,
    "wrong_questions": [3, 7, 15, 22, 31]
  }
}
```

---

### 4. 배치 처리

#### POST `/api/align/batch`
여러 이미지를 한 번에 정렬합니다.

#### POST `/api/grade/batch`
여러 답안지를 한 번에 채점합니다.

**요청**
```javascript
const formData = new FormData();
formData.append('scans', file1);
formData.append('scans', file2);
formData.append('scans', file3);
formData.append('answer_key', JSON.stringify([1,2,3,...])); // grade만 필요
formData.append('method', 'sift');

const response = await fetch('https://your-app.onrender.com/api/grade/batch', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your-api-key-here'
  },
  body: formData
});
```

**응답**
```json
{
  "success": true,
  "total": 3,
  "successful": 3,
  "failed": 0,
  "average_score": 85.67,
  "results": [...]
}
```

---

## React 예제

```jsx
import { useState } from 'react';

const API_KEY = 'your-api-key-here';
const BASE_URL = 'https://your-app.onrender.com';

function ExamGrader() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleGrade = async () => {
    if (!file) return;

    setLoading(true);
    const formData = new FormData();
    formData.append('scan', file);
    formData.append('answer_key', JSON.stringify([
      1,2,3,4,5,1,2,3,4,5,
      1,2,3,4,5,1,2,3,4,5,
      1,2,3,4,5,1,2,3,4,5,
      1,2,3,4,5,1,2,3,4,5,
      1,2,3,4,5
    ]));

    try {
      const response = await fetch(`${BASE_URL}/api/grade`, {
        method: 'POST',
        headers: {
          'X-API-Key': API_KEY
        },
        body: formData
      });

      const data = await response.json();
      setResult(data);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <input
        type="file"
        onChange={(e) => setFile(e.target.files[0])}
        accept="image/*"
      />
      <button onClick={handleGrade} disabled={loading}>
        {loading ? '채점 중...' : '채점하기'}
      </button>

      {result && (
        <div>
          <h3>채점 결과</h3>
          <p>점수: {result.grading.total_score} / {result.grading.max_score}</p>
          <p>정답률: {result.grading.percentage}%</p>
        </div>
      )}
    </div>
  );
}
```

---

## TypeScript 타입 정의

```typescript
// 채점 결과 타입
interface GradingResult {
  success: boolean;
  message: string;
  grading: {
    student_answers: Record<string, number | null>;
    correct_count: number;
    wrong_count: number;
    blank_count: number;
    total_score: number;
    max_score: number;
    percentage: number;
    wrong_questions: number[];
  };
}

// 답안 검출 결과 타입
interface DetectionResult {
  success: boolean;
  message: string;
  detected_answers: Record<string, number | null>;
  statistics: {
    total_questions: number;
    answered: number;
    blank: number;
  };
}

// API 요청 함수
async function gradeExam(
  imageFile: File,
  answerKey: number[]
): Promise<GradingResult> {
  const formData = new FormData();
  formData.append('scan', imageFile);
  formData.append('answer_key', JSON.stringify(answerKey));

  const response = await fetch(`${BASE_URL}/api/grade`, {
    method: 'POST',
    headers: {
      'X-API-Key': API_KEY
    },
    body: formData
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}
```

---

## 에러 처리

**401 Unauthorized**
```json
{
  "success": false,
  "error": "유효하지 않은 API 키입니다",
  "detail": "올바른 API 키를 제공해주세요"
}
```

**400 Bad Request**
```json
{
  "success": false,
  "error": "입력 검증 오류",
  "detail": "scan 파라미터는 이미지 파일이어야 합니다"
}
```

**500 Internal Server Error**
```json
{
  "success": false,
  "error": "서버 내부 오류가 발생했습니다",
  "detail": "..."
}
```

---

## 파라미터 설명

### method (정렬 방식)
- `sift`: 높은 정확도, 느림 (기본값)
- `contour`: 빠른 속도, 깔끔한 배경 필요

### threshold (마킹 임계값)
- 범위: 0.0 ~ 1.0
- 기본값: 0.35
- 낮을수록 민감 (약한 마킹도 검출)
- 높을수록 둔감 (진한 마킹만 검출)

### enhance (품질 개선)
- `true`: CLAHE 및 노이즈 제거 적용
- `false`: 원본 이미지 사용

---

## 참고사항

1. **파일 크기**: 이미지는 10MB 이하 권장
2. **정답 배열**: 반드시 45개의 숫자 (1~5) 배열
3. **응답 시간**: 이미지당 약 2-5초 소요
4. **Free 플랜**: 첫 요청 시 슬립 모드 해제로 30초 정도 소요될 수 있음

---

## 추가 정보

**API 문서**: `https://your-app.onrender.com/docs`
**헬스체크**: `https://your-app.onrender.com/health`
**문의**: GitHub Issues
