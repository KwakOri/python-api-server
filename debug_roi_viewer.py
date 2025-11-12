"""
ROI 영역 시각화를 위한 Flask 디버그 서버
템플릿 이미지에 마킹 검출 영역을 표시하여 좌표 설정이 올바른지 확인
"""
from flask import Flask, send_file, render_template_string, request, jsonify
import cv2
import numpy as np
from app.core.omr_utils import get_bubble_roi, GRID_CONFIG, is_bubble_marked
from app.core.image_utils import align_with_sift
import io
from PIL import Image
import requests
import os

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# 템플릿 이미지 경로 (OMR 카드 기준 이미지)
TEMPLATE_PATH = "omr_card.jpg"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>OMR ROI 검출 영역 확인</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #333;
        }
        .container {
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .controls {
            margin: 20px 0;
        }
        button {
            background-color: #4CAF50;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            margin-right: 10px;
        }
        button:hover {
            background-color: #45a049;
        }
        button.secondary {
            background-color: #2196F3;
        }
        button.secondary:hover {
            background-color: #0b7dda;
        }
        input {
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            margin-right: 10px;
        }
        input[type="file"] {
            padding: 5px;
        }
        img {
            max-width: 100%;
            border: 1px solid #ddd;
            margin-top: 20px;
        }
        .info {
            background-color: #e7f3ff;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
        }
        .warning {
            background-color: #fff3cd;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
            border-left: 4px solid #ffc107;
        }
        .legend {
            margin-top: 20px;
        }
        .legend-item {
            display: inline-block;
            margin-right: 20px;
        }
        .color-box {
            display: inline-block;
            width: 20px;
            height: 20px;
            margin-right: 5px;
            vertical-align: middle;
            border: 1px solid #000;
        }
        .upload-section {
            background-color: #f9f9f9;
            padding: 20px;
            border-radius: 4px;
            border: 2px dashed #ddd;
        }
        #loading {
            display: none;
            text-align: center;
            padding: 20px;
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #3498db;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 OMR 마킹 검출 영역 확인</h1>

        <div class="info">
            <strong>📋 설명:</strong> 템플릿 이미지에 45개 문제의 마킹 검출 영역(ROI)을 표시합니다.<br>
            각 사각형이 실제 버블 위치와 일치하는지 확인하세요.
        </div>

        <div class="controls">
            <h3>전체 보기</h3>
            <button onclick="location.href='/roi/all'">전체 ROI 보기</button>
            <button onclick="location.href='/roi/all?show_numbers=true'">전체 ROI + 번호 보기</button>
        </div>

        <div class="controls">
            <h3>문제별 보기</h3>
            <label>문제 번호 (1-45): </label>
            <input type="number" id="question" min="1" max="45" value="1">
            <button onclick="viewQuestion()">해당 문제 ROI 보기</button>
        </div>

        <div class="controls">
            <h3>열별 보기</h3>
            <button onclick="location.href='/roi/column/1'">1열 (1-20번)</button>
            <button onclick="location.href='/roi/column/2'">2열 (21-34번)</button>
            <button onclick="location.href='/roi/column/3'">3열 (35-45번)</button>
        </div>

        <div class="legend">
            <h3>범례</h3>
            <div class="legend-item">
                <span class="color-box" style="background-color: rgba(0, 255, 0, 0.3);"></span>
                <span>ROI 영역</span>
            </div>
            <div class="legend-item">
                <span class="color-box" style="background-color: rgba(255, 0, 0, 0.5);"></span>
                <span>문제 번호</span>
            </div>
            <div class="legend-item">
                <span class="color-box" style="background-color: rgba(0, 0, 255, 0.5);"></span>
                <span>선택지 번호 (1-5)</span>
            </div>
        </div>

        <hr>
        <h3>Grid 설정 정보</h3>
        <pre>{{ grid_config }}</pre>
    </div>

    <div class="container">
        <h2>📤 OMR 이미지 정렬 및 검출 테스트</h2>

        <div class="warning">
            <strong>⚠️ 주의:</strong> 이 기능을 사용하려면 FastAPI 서버(포트 8080)가 실행 중이어야 합니다.<br>
            <code>python main.py</code> 명령으로 서버를 먼저 실행하세요.
        </div>

        <div class="upload-section">
            <h3>이미지 업로드 및 정렬 확인</h3>
            <p>스캔된 OMR 카드 이미지를 업로드하면 자동으로 정렬하고 마킹 검출 영역을 표시합니다.</p>

            <form id="uploadForm" enctype="multipart/form-data">
                <input type="file" id="imageFile" name="image" accept="image/*" required>
                <br><br>
                <label>
                    <input type="checkbox" id="showDensity" checked>
                    어두움 비율 표시
                </label>
                <label style="margin-left: 20px;">
                    <input type="checkbox" id="showNumbers" checked>
                    문제/선택지 번호 표시
                </label>
                <br><br>
                <button type="button" class="secondary" onclick="uploadAndAlign()">업로드 및 정렬 확인</button>
            </form>

            <div id="loading">
                <div class="spinner"></div>
                <p>이미지를 정렬하고 분석 중입니다...</p>
            </div>

            <div id="result"></div>
        </div>
    </div>

    <script>
        function viewQuestion() {
            const question = document.getElementById('question').value;
            location.href = '/roi/question/' + question;
        }

        async function uploadAndAlign() {
            const fileInput = document.getElementById('imageFile');
            const showDensity = document.getElementById('showDensity').checked;
            const showNumbers = document.getElementById('showNumbers').checked;
            const loading = document.getElementById('loading');
            const result = document.getElementById('result');

            if (!fileInput.files[0]) {
                alert('이미지 파일을 선택해주세요.');
                return;
            }

            const formData = new FormData();
            formData.append('image', fileInput.files[0]);
            formData.append('show_density', showDensity);
            formData.append('show_numbers', showNumbers);

            loading.style.display = 'block';
            result.innerHTML = '';

            try {
                const response = await fetch('/align-and-analyze', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.error || '서버 오류가 발생했습니다.');
                }

                const blob = await response.blob();
                const imageUrl = URL.createObjectURL(blob);

                result.innerHTML = '<h3>✅ 정렬 및 분석 결과</h3><img src="' + imageUrl + '" alt="분석 결과">';
            } catch (error) {
                result.innerHTML = '<div class="warning"><strong>❌ 오류:</strong> ' + error.message + '</div>';
            } finally {
                loading.style.display = 'none';
            }
        }
    </script>
</body>
</html>
"""


def load_template():
    """템플릿 이미지 로드"""
    img = cv2.imread(TEMPLATE_PATH)
    if img is None:
        # 템플릿이 없으면 더미 이미지 생성
        img = np.ones((3508, 2480, 3), dtype=np.uint8) * 255
        cv2.putText(img, "Template image not found", (50, 100),
                   cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 0, 0), 3)
        cv2.putText(img, f"Expected path: {TEMPLATE_PATH}", (50, 200),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    return img


def draw_roi_on_template(questions=None, show_numbers=False, show_densities=False):
    """
    템플릿 이미지에 ROI를 그림

    Args:
        questions: 표시할 문제 번호 리스트 (None이면 전체)
        show_numbers: 문제/선택지 번호 표시 여부
        show_densities: 어두움 비율 표시 여부 (실제 스캔 이미지 필요)
    """
    img = load_template()
    img_height, img_width = img.shape[:2]

    if questions is None:
        questions = range(1, 46)

    for question in questions:
        for option in range(1, 6):
            try:
                x, y, width, height = get_bubble_roi(img_height, img_width, question, option)

                # ROI 사각형 그리기 (초록색, 반투명)
                overlay = img.copy()
                cv2.rectangle(overlay, (x, y), (x + width, y + height), (0, 255, 0), 2)
                cv2.rectangle(overlay, (x, y), (x + width, y + height), (0, 255, 0), -1)
                img = cv2.addWeighted(overlay, 0.2, img, 0.8, 0)
                cv2.rectangle(img, (x, y), (x + width, y + height), (0, 255, 0), 2)

                if show_numbers:
                    # 문제 번호 표시 (빨간색)
                    if option == 1:
                        cv2.putText(img, f"Q{question}", (x - 30, y + height // 2),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

                    # 선택지 번호 표시 (파란색)
                    cv2.putText(img, str(option), (x + width // 3, y + height // 2),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)

            except Exception as e:
                print(f"Error drawing ROI for Q{question} Option{option}: {e}")

    return img


def numpy_to_bytes(img):
    """NumPy 이미지를 bytes로 변환"""
    # BGR to RGB
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb)
    img_io = io.BytesIO()
    pil_img.save(img_io, 'PNG')
    img_io.seek(0)
    return img_io


@app.route('/')
def index():
    """메인 페이지"""
    import json
    grid_info = json.dumps(GRID_CONFIG, indent=2, ensure_ascii=False)
    return render_template_string(HTML_TEMPLATE, grid_config=grid_info)


@app.route('/roi/all')
def show_all_rois():
    """모든 ROI 표시"""
    from flask import request
    show_numbers = request.args.get('show_numbers', 'false').lower() == 'true'

    img = draw_roi_on_template(show_numbers=show_numbers)
    img_bytes = numpy_to_bytes(img)
    return send_file(img_bytes, mimetype='image/png')


@app.route('/roi/question/<int:question_num>')
def show_question_roi(question_num):
    """특정 문제의 ROI만 표시"""
    if not (1 <= question_num <= 45):
        return "문제 번호는 1-45 사이여야 합니다.", 400

    img = draw_roi_on_template(questions=[question_num], show_numbers=True)
    img_bytes = numpy_to_bytes(img)
    return send_file(img_bytes, mimetype='image/png')


@app.route('/roi/column/<int:column_num>')
def show_column_roi(column_num):
    """특정 열의 ROI 표시"""
    if not (1 <= column_num <= 3):
        return "열 번호는 1-3 사이여야 합니다.", 400

    column_config = GRID_CONFIG["columns"][column_num - 1]
    questions = range(column_config["start"], column_config["end"] + 1)

    img = draw_roi_on_template(questions=questions, show_numbers=True)
    img_bytes = numpy_to_bytes(img)
    return send_file(img_bytes, mimetype='image/png')


@app.route('/roi/analyze/<path:image_path>')
def analyze_image(image_path):
    """
    실제 스캔 이미지의 ROI 분석 (어두움 비율 표시)
    예: /roi/analyze/path/to/scan.png
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            return f"이미지를 불러올 수 없습니다: {image_path}", 400

        img_height, img_width = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

        from app.core.omr_utils import is_bubble_marked

        for question in range(1, 46):
            for option in range(1, 6):
                x, y, width, height = get_bubble_roi(img_height, img_width, question, option)
                is_marked, density = is_bubble_marked(gray, x, y, width, height, threshold=0.45)

                # ROI 사각형 (마킹된 것은 빨간색, 아닌 것은 초록색)
                color = (0, 0, 255) if is_marked else (0, 255, 0)
                cv2.rectangle(img, (x, y), (x + width, y + height), color, 2)

                # 어두움 비율 표시
                cv2.putText(img, f"{density:.2f}", (x, y - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.3, color, 1)

        img_bytes = numpy_to_bytes(img)
        return send_file(img_bytes, mimetype='image/png')

    except Exception as e:
        return f"오류 발생: {str(e)}", 500


@app.route('/align-and-analyze', methods=['POST'])
def align_and_analyze():
    """
    업로드된 이미지를 정렬하고 ROI 분석 수행
    FastAPI 서버(/api/align/)를 호출하여 정렬 수행
    """
    try:
        # 파일 확인
        if 'image' not in request.files:
            return jsonify({'error': '이미지 파일이 없습니다.'}), 400

        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': '파일이 선택되지 않았습니다.'}), 400

        # 옵션 가져오기
        show_density = request.form.get('show_density', 'true').lower() == 'true'
        show_numbers = request.form.get('show_numbers', 'true').lower() == 'true'

        # FastAPI 서버에 정렬 요청
        print(f"FastAPI 서버에 정렬 요청 - 파일: {file.filename}")

        # 파일을 다시 읽기 위해 시작 위치로 이동
        file.seek(0)

        # FastAPI 서버 호출
        files = {'scan': (file.filename, file.read(), file.content_type)}
        data = {
            'method': 'sift',
            'enhance': 'true',
            'return_image': 'true'
        }

        response = requests.post(
            'http://localhost:8080/api/align/',
            files=files,
            data=data,
            timeout=30
        )

        if response.status_code != 200:
            error_msg = f'FastAPI 서버 오류 (HTTP {response.status_code})'
            try:
                error_detail = response.json().get('detail', '')
                if error_detail:
                    error_msg += f': {error_detail}'
            except:
                pass
            return jsonify({'error': error_msg}), 400

        # 정렬된 이미지 디코딩
        aligned_bytes = np.frombuffer(response.content, np.uint8)
        aligned_img = cv2.imdecode(aligned_bytes, cv2.IMREAD_COLOR)

        if aligned_img is None:
            return jsonify({'error': '정렬된 이미지를 디코딩할 수 없습니다.'}), 400

        # 헤더에서 메타데이터 확인
        alignment_success = response.headers.get('X-Alignment-Success', 'False')
        alignment_method = response.headers.get('X-Alignment-Method', 'unknown')

        print(f"이미지 정렬 완료 - 성공: {alignment_success}, 방식: {alignment_method}, 크기: {aligned_img.shape}")

        # 그레이스케일 변환
        gray = cv2.cvtColor(aligned_img, cv2.COLOR_BGR2GRAY) if len(aligned_img.shape) == 3 else aligned_img
        img_height, img_width = gray.shape

        # ROI 그리기
        for question in range(1, 46):
            for option in range(1, 6):
                try:
                    x, y, width, height = get_bubble_roi(img_height, img_width, question, option)
                    is_marked, density = is_bubble_marked(gray, x, y, width, height, threshold=0.45)

                    # ROI 사각형 (마킹된 것은 빨간색, 아닌 것은 초록색)
                    color = (0, 0, 255) if is_marked else (0, 255, 0)
                    thickness = 3 if is_marked else 2

                    # 반투명 배경
                    overlay = aligned_img.copy()
                    cv2.rectangle(overlay, (x, y), (x + width, y + height), color, -1)
                    cv2.addWeighted(overlay, 0.2, aligned_img, 0.8, 0, aligned_img)

                    # 테두리
                    cv2.rectangle(aligned_img, (x, y), (x + width, y + height), color, thickness)

                    # 어두움 비율 표시
                    if show_density:
                        text = f"{density:.3f}"
                        font_scale = 0.35
                        font_thickness = 1

                        # 텍스트 배경 (가독성 향상)
                        (text_width, text_height), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_thickness)
                        cv2.rectangle(aligned_img, (x, y - text_height - 5), (x + text_width, y - 2), (255, 255, 255), -1)

                        cv2.putText(aligned_img, text, (x, y - 5),
                                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, font_thickness)

                    # 문제/선택지 번호 표시
                    if show_numbers:
                        if option == 1:
                            # 문제 번호
                            cv2.putText(aligned_img, f"Q{question}", (x - 40, y + height // 2),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 2)

                        # 선택지 번호
                        cv2.putText(aligned_img, str(option), (x + width // 3, y + height // 2 + 5),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)

                except Exception as e:
                    print(f"문제 {question}, 선택지 {option} 처리 중 오류: {e}")

        # 이미지를 바이트로 변환하여 반환
        img_bytes = numpy_to_bytes(aligned_img)
        return send_file(img_bytes, mimetype='image/png')

    except Exception as e:
        print(f"오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'서버 오류: {str(e)}'}), 500


if __name__ == '__main__':
    import sys

    # 템플릿 경로를 인자로 받을 수 있음
    if len(sys.argv) > 1:
        TEMPLATE_PATH = sys.argv[1]

    print("=" * 60)
    print("🔍 OMR ROI 검출 영역 시각화 서버")
    print("=" * 60)
    print(f"📁 템플릿 이미지 경로: {TEMPLATE_PATH}")
    print(f"🌐 서버 주소: http://localhost:5001")
    print("=" * 60)
    print("\n브라우저에서 http://localhost:5001 을 열어주세요.\n")

    app.run(debug=True, host='0.0.0.0', port=5001)
