"""
PhotoLens — Production App
Usage: python app.py (dev) | gunicorn app:app (prod)
"""

import os
import uuid
import time
import math
import traceback

import cv2
from flask import Flask, render_template, request, jsonify, send_file, make_response

from utils.analyzer import analyze_image, generate_histogram
from utils.enhancer import apply_style, get_styles
from utils.entertainment import analyze_mbti, analyze_audience, analyze_mood

app = Flask(__name__)
_secret = os.environ.get("SECRET_KEY")
if not _secret:
    print("[WARNING] SECRET_KEY not set — using random key. Sessions will be lost on restart.", flush=True)
app.secret_key = _secret or uuid.uuid4().hex

# ----- Config -----
MAX_IMAGE_PIXELS = 2000  # Long edge will be resized to this
MAX_UPLOAD_MB = 20
FILE_TTL_SECONDS = 3600  # 1 hour auto-cleanup
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024
app.config["UPLOAD_FOLDER"] = os.path.join(BASE_DIR, "static", "uploads")
app.config["ENHANCED_FOLDER"] = os.path.join(BASE_DIR, "static", "enhanced")
app.config["HISTOGRAM_FOLDER"] = os.path.join(BASE_DIR, "static", "histograms")

for folder in [app.config["UPLOAD_FOLDER"], app.config["ENHANCED_FOLDER"],
               app.config["HISTOGRAM_FOLDER"]]:
    os.makedirs(folder, exist_ok=True)


# ----- Helpers -----

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def sanitize_filename(filename):
    """Reject path traversal attempts. Returns True if safe."""
    if not filename or "/" in filename or "\\" in filename or ".." in filename:
        return False
    return True


def validate_image_magic(filepath):
    """Check file magic bytes to ensure it's a real image, not just renamed extension.
    Returns True if the file header matches JPG/PNG/WebP."""
    try:
        with open(filepath, "rb") as f:
            header = f.read(12)
        # JPG: FF D8 FF
        if header[:3] == b"\xff\xd8\xff":
            return True
        # PNG: 89 50 4E 47 0D 0A 1A 0A
        if header[:8] == b"\x89PNG\r\n\x1a\n":
            return True
        # WebP: RIFF....WEBP
        if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
            return True
        return False
    except OSError:
        return False


# ----- Simple In-Memory Rate Limiter -----
_rate_limit_store = {}  # {ip: [timestamps]}


def check_rate_limit(ip, max_requests=10, window=60):
    """Return True if request is allowed, False if rate limited."""
    now = time.time()
    if ip not in _rate_limit_store:
        _rate_limit_store[ip] = []
    # Purge old entries
    _rate_limit_store[ip] = [t for t in _rate_limit_store[ip] if now - t < window]
    if len(_rate_limit_store[ip]) >= max_requests:
        return False
    _rate_limit_store[ip].append(now)
    return True


def cleanup_old_files(folder, max_age_seconds=FILE_TTL_SECONDS):
    """Remove files older than max_age_seconds. Best-effort, never fails."""
    try:
        now = time.time()
        for f in os.listdir(folder):
            fp = os.path.join(folder, f)
            try:
                if os.path.isfile(fp) and now - os.path.getmtime(fp) > max_age_seconds:
                    os.remove(fp)
            except OSError as e:
                print(f"[WARN] cleanup: cannot remove {fp}: {e}", flush=True)
    except Exception as e:
        print(f"[WARN] cleanup: cannot list {folder}: {e}", flush=True)


def resize_if_needed(filepath):
    """Downscale image if long edge exceeds MAX_IMAGE_PIXELS. Writes to temp first for safety."""
    try:
        img = cv2.imread(filepath)
        if img is None:
            return
        h, w = img.shape[:2]
        long_edge = max(h, w)
        if long_edge > MAX_IMAGE_PIXELS:
            scale = MAX_IMAGE_PIXELS / long_edge
            new_w, new_h = int(w * scale), int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
            # Write to temp file first, then atomically replace
            import tempfile
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg", dir=os.path.dirname(filepath))
            try:
                cv2.imwrite(tmp.name, img, [cv2.IMWRITE_JPEG_QUALITY, 90])
                os.replace(tmp.name, filepath)
            finally:
                if os.path.exists(tmp.name):
                    os.remove(tmp.name)
    except Exception as e:
        print(f"[WARN] resize: cannot process {filepath}: {e}", flush=True)


def add_cache_headers(response, max_age=3600):
    """Add Cache-Control header to static file responses."""
    response.headers["Cache-Control"] = f"public, max-age={max_age}"
    return response


def log_error(context, exc):
    """Log structured error for debugging (stdout in prod, visible in Railway/Render logs)."""
    print(f"[ERROR] {context}: {exc}", flush=True)
    traceback.print_exc()


# ----- Routes -----

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    """Upload and analyze a photo. Returns 8-dimension scores, MBTI, audience, and mood."""
    # --- Rate limit ---
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown")
    if not check_rate_limit(client_ip):
        return jsonify({"error": "请求太频繁，请稍后再试", "type": "rate_limit"}), 429

    # --- Validate input ---
    if "file" not in request.files:
        return jsonify({"error": "未选择文件", "type": "no_file"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "未选择文件", "type": "no_file"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": f"仅支持 {', '.join(ALLOWED_EXTENSIONS).upper()} 格式",
                        "type": "bad_format"}), 400

    # --- Save file ---
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    # --- Validate magic bytes ---
    if not validate_image_magic(filepath):
        os.remove(filepath)
        return jsonify({"error": "文件不是有效的图片，请上传真实的 JPG/PNG/WebP 图片",
                        "type": "bad_file"}), 400

    # --- Auto-cleanup old files (best-effort, never blocks) ---
    cleanup_old_files(app.config["UPLOAD_FOLDER"])
    cleanup_old_files(app.config["ENHANCED_FOLDER"])
    cleanup_old_files(app.config["HISTOGRAM_FOLDER"])

    # --- Resize large images ---
    resize_if_needed(filepath)

    # --- Read image once, reuse for all analysis ---
    img_raw = cv2.imread(filepath)
    if img_raw is None:
        os.remove(filepath)
        return jsonify({"error": "无法解码图片文件，文件可能已损坏", "type": "decode"}), 400
    img_rgb = cv2.cvtColor(img_raw, cv2.COLOR_BGR2RGB)

    # --- Analyze ---
    try:
        result = analyze_image(img_rgb)
        # Generate histogram
        hist_name = f"hist_{filename.rsplit('.', 1)[0]}.png"
        hist_path = os.path.join(app.config["HISTOGRAM_FOLDER"], hist_name)
        generate_histogram(img_rgb, hist_path)
        result["histogram_url"] = f"/static/histograms/{hist_name}"

        # Entertainment analysis
        score_map = {d["key"]: d["score"] for d in result["dimensions"]}
        result["mbti"] = analyze_mbti(score_map, img_rgb)
        result["audience"] = analyze_audience(score_map, img_rgb, result["mbti"])
        result["mood"] = analyze_mood(score_map, img_rgb)

    except MemoryError:
        log_error("analyze", "MemoryError")
        return jsonify({"error": "图片过大导致内存不足，请上传 20MB 以内的图片",
                        "type": "memory"}), 413
    except ValueError as e:
        log_error("analyze", str(e))
        return jsonify({"error": f"图片分析失败: {str(e)}", "type": "decode"}), 400
    except Exception as e:
        log_error("analyze", str(e))
        return jsonify({"error": f"分析失败，请重试或更换图片", "type": "internal"}), 500

    result["filename"] = filename
    result["styles"] = get_styles()
    return jsonify(result)


@app.route("/api/enhance", methods=["POST"])
def enhance():
    """Apply an enhancement style to a previously uploaded image."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "无效请求", "type": "bad_json"}), 400

    filename = data.get("filename", "").strip()
    style_key = data.get("style", "").strip()
    intensity = float(data.get("intensity", 1.0))

    if not filename or not style_key:
        return jsonify({"error": "缺少必要参数", "type": "missing_param"}), 400

    # Prevent path traversal
    if "/" in filename or "\\" in filename or ".." in filename:
        return jsonify({"error": "无效文件名", "type": "bad_filename"}), 400

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if not os.path.isfile(filepath):
        return jsonify({"error": "原图已过期或不存在，请重新上传", "type": "expired"}), 404

    intensity_label = f"_i{int(intensity * 100)}" if intensity < 1.0 else ""
    enhanced_name = f"{style_key}{intensity_label}_{filename}"
    enhanced_path = os.path.join(app.config["ENHANCED_FOLDER"], enhanced_name)

    try:
        style_info = apply_style(filepath, style_key, enhanced_path, intensity)
        # Generate histogram from the enhanced image (needs array, not path)
        enhanced_img = cv2.imread(enhanced_path)
        hist_name = f"hist_{enhanced_name.rsplit('.', 1)[0]}.png"
        hist_path = os.path.join(app.config["HISTOGRAM_FOLDER"], hist_name)
        if enhanced_img is not None:
            generate_histogram(cv2.cvtColor(enhanced_img, cv2.COLOR_BGR2RGB), hist_path)
    except ValueError as e:
        log_error("enhance", str(e))
        return jsonify({"error": str(e), "type": "bad_style"}), 400
    except Exception as e:
        log_error("enhance", str(e))
        return jsonify({"error": "增强处理失败，请重试", "type": "internal"}), 500

    return jsonify({
        "enhanced_filename": enhanced_name,
        "style_name": style_info["name"],
        "histogram_url": f"/static/histograms/{hist_name}",
    })


# ----- Static file serving (with caching) -----

@app.route("/static/uploads/<filename>")
def uploaded_file(filename):
    if not sanitize_filename(filename):
        return jsonify({"error": "无效文件名"}), 400
    resp = make_response(send_file(os.path.join(app.config["UPLOAD_FOLDER"], filename)))
    return add_cache_headers(resp, max_age=1800)


@app.route("/static/enhanced/<filename>")
def enhanced_file(filename):
    if not sanitize_filename(filename):
        return jsonify({"error": "无效文件名"}), 400
    resp = make_response(send_file(os.path.join(app.config["ENHANCED_FOLDER"], filename)))
    return add_cache_headers(resp, max_age=1800)


@app.route("/static/histograms/<filename>")
def histogram_file(filename):
    if not sanitize_filename(filename):
        return jsonify({"error": "无效文件名"}), 400
    resp = make_response(send_file(os.path.join(app.config["HISTOGRAM_FOLDER"], filename)))
    return add_cache_headers(resp, max_age=600)


@app.route("/api/download/<filename>")
def download_file(filename):
    if not sanitize_filename(filename):
        return jsonify({"error": "无效文件名", "type": "bad_filename"}), 400
    filepath = os.path.join(app.config["ENHANCED_FOLDER"], filename)
    if not os.path.isfile(filepath):
        return jsonify({"error": "文件不存在或已过期", "type": "expired"}), 404
    return send_file(filepath, as_attachment=True, download_name=filename)


# ----- Health Check -----

@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "timestamp": int(time.time())})


# ----- Share Links -----

SHARE_FOLDER = os.path.join(BASE_DIR, "static", "shares")

@app.route("/api/share", methods=["POST"])
def create_share():
    """Save analysis result and return a shareable link."""
    os.makedirs(SHARE_FOLDER, exist_ok=True)
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "无效请求"}), 400

    share_id = uuid.uuid4().hex[:8]
    share_data = {
        "id": share_id,
        "overall": data.get("overall"),
        "overall_label": data.get("overall_label"),
        "overall_color": data.get("overall_color"),
        "overall_desc": data.get("overall_desc"),
        "summary": data.get("summary"),
        "recommended_style": data.get("recommended_style"),
        "recommended_reason": data.get("recommended_reason"),
        "mbti": data.get("mbti"),
        "mood": data.get("mood"),
        "dimensions": data.get("dimensions"),
        "filename": data.get("filename"),
        "histogram_url": data.get("histogram_url"),
        "created_at": int(time.time()),
    }
    share_path = os.path.join(SHARE_FOLDER, f"{share_id}.json")
    import json
    with open(share_path, "w", encoding="utf-8") as f:
        json.dump(share_data, f, ensure_ascii=False)

    return jsonify({"share_url": f"/share/{share_id}"})


@app.route("/share/<share_id>")
def view_share(share_id):
    """Render a shared analysis result page."""
    if "/" in share_id or "\\" in share_id:
        return "Invalid ID", 400
    share_path = os.path.join(SHARE_FOLDER, f"{share_id}.json")
    if not os.path.isfile(share_path):
        return render_template("share_expired.html"), 404

    import json
    with open(share_path, "r", encoding="utf-8") as f:
        share_data = json.load(f)
    return render_template("share.html", data=share_data)


# ----- Entry -----

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug, host="0.0.0.0", port=port)
