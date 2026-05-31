// ===== DOM Elements =====
const dropZone = document.getElementById("drop-zone");
const fileInput = document.getElementById("file-input");
const uploadPreview = document.getElementById("upload-preview");
const previewImg = document.getElementById("preview-img");
const uploadSection = document.getElementById("upload-section");
const loadingSection = document.getElementById("loading-section");
const resultsSection = document.getElementById("results-section");
const errorSection = document.getElementById("error-section");
const errorMessage = document.getElementById("error-message");
const errorDetail = document.getElementById("error-detail");

// ===== Centralized Application State =====
const AppState = {
    currentFilename: null,
    currentEnhancedFilename: null,
    currentFile: null,
    currentHistogramUrl: null,
    currentStyle: null,
    lastResult: null,  // Full analyze() response cached for share
};

// ===== Upload Handlers =====
dropZone.addEventListener("click", () => fileInput.click());

dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("drag-over");
});

dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("drag-over");
});

dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
    const files = e.dataTransfer.files;
    if (files.length > 0) handleFile(files[0]);
});

fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) handleFile(fileInput.files[0]);
});

// Ctrl+V paste
document.addEventListener("paste", (e) => {
    const items = e.clipboardData?.items;
    if (items) {
        for (const item of items) {
            if (item.type.startsWith("image/")) {
                e.preventDefault();
                handleFile(item.getAsFile());
                break;
            }
        }
    }
});

// Escape to reset
document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !resultsSection.classList.contains("hidden")) resetUpload();
});

document.getElementById("reupload-btn").addEventListener("click", resetUpload);

function handleFile(file) {
    const allowed = ["image/jpeg", "image/png", "image/webp"];
    if (!allowed.includes(file.type)) {
        showError("格式不支持", "仅支持 JPG、PNG、WebP 格式，请选择其他图片");
        return;
    }
    if (file.size > 20 * 1024 * 1024) {
        showError("文件过大", `当前文件 ${(file.size/1024/1024).toFixed(1)}MB，最大支持 20MB`);
        return;
    }

    AppState.currentFile = file;
    const reader = new FileReader();
    reader.onload = (e) => {
        previewImg.src = e.target.result;
        dropZone.style.display = "none";
        uploadPreview.classList.remove("hidden");
    };
    reader.readAsDataURL(file);
}

function resetUpload() {
    dropZone.style.display = "";
    uploadPreview.classList.add("hidden");
    fileInput.value = "";
    AppState.currentFilename = null;
    AppState.currentFile = null;
    AppState.currentEnhancedFilename = null;
    AppState.currentHistogramUrl = null;
    AppState.currentStyle = null;
    AppState.lastResult = null;
    hideAllSections();
    uploadSection.classList.remove("hidden");
}

// ===== Analyze (Progressive Loading) =====
document.getElementById("analyze-btn").addEventListener("click", analyzePhoto);

async function analyzePhoto() {
    const file = AppState.currentFile || (fileInput.files.length > 0 ? fileInput.files[0] : null);
    if (!file) return;

    uploadSection.classList.add("hidden");
    errorSection.classList.add("hidden");
    loadingSection.classList.remove("hidden");
    resultsSection.classList.add("hidden");

    // Progressive step indicators
    const stepScore = document.getElementById("step-score");
    const stepEnhance = document.getElementById("step-enhance");
    const stepDone = document.getElementById("step-done");
    [stepScore, stepEnhance, stepDone].forEach(s => { s.classList.remove("active", "done"); });
    stepScore.classList.add("active");

    const formData = new FormData();
    formData.append("file", file);

    try {
        // Step 1: Analyze
        document.getElementById("loading-text").textContent = "正在分析照片...";
        const res = await fetch("/api/analyze", { method: "POST", body: formData });
        const data = await res.json();

        if (!res.ok) throw { type: "server", message: data.error || "分析失败", detail: `服务器返回 ${res.status}` };

        AppState.currentFilename = data.filename;
        AppState.currentHistogramUrl = data.histogram_url || null;
        AppState.currentStyle = data.recommended_style;
        AppState.lastResult = data;  // Cache full result for sharing
        stepScore.classList.remove("active");
        stepScore.classList.add("done");
        stepEnhance.classList.add("active");

        // Render scores immediately (progressive)
        renderScores(data);
        loadingSection.classList.add("hidden");
        resultsSection.classList.remove("hidden");
        setTimeout(() => resultsSection.scrollIntoView({ behavior: "smooth", block: "start" }), 100);

        // Step 2: Apply recommended style
        document.getElementById("loading-text").textContent = "正在生成增强效果...";
        const recStyle = data.recommended_style || (data.styles.length > 0 ? data.styles[0].key : null);
        if (recStyle) {
            const styleInfo = data.styles.find(s => s.key === recStyle);
            await applyStyle(recStyle, styleInfo ? styleInfo.description : "", 1.0, data.styles, data.recommended_style);
        }
        stepEnhance.classList.remove("active");
        stepEnhance.classList.add("done");
        stepDone.classList.add("done");

    } catch (err) {
        loadingSection.classList.add("hidden");
        if (err.type === "server") {
            showError(err.message, err.detail);
        } else if (err.name === "TypeError" && err.message.includes("fetch")) {
            showError("网络连接失败", "无法连接服务器，请确认服务已启动（运行 启动PhotoLens.bat）");
        } else {
            showError("分析失败", err.message || "未知错误，请重试");
        }
    }
}

// ===== Render Scores =====
function renderScores(data) {
    // Score ring — color interpolates from red through amber to green
    const circleLen = 2 * Math.PI * 52;
    const score = data.overall;
    const offset = circleLen * (1 - score / 100);
    const ring = document.getElementById("ring-progress");
    ring.style.strokeDashoffset = offset;

    // Interpolate: 0→red, 40→amber, 75→green
    function lerpColor(a, b, t) { return Math.round(a + (b - a) * t); }
    function colorAt(pct) {
        const stops = [[0, 255, 59, 48], [40, 255, 159, 10], [75, 52, 199, 89], [100, 48, 209, 88]];
        let lo = stops[0], hi = stops[stops.length - 1];
        for (let i = 0; i < stops.length - 1; i++) {
            if (pct >= stops[i][0] && pct <= stops[i + 1][0]) { lo = stops[i]; hi = stops[i + 1]; break; }
        }
        const t = (pct - lo[0]) / (hi[0] - lo[0]);
        return `rgb(${lerpColor(lo[1], hi[1], t)},${lerpColor(lo[2], hi[2], t)},${lerpColor(lo[3], hi[3], t)})`;
    }
    ring.style.stroke = colorAt(score);

    const scoreColor = data.overall_color || (score >= 85 ? "#34c759" : score >= 70 ? "#0071e3" : score >= 50 ? "#ff9f0a" : "#ff3b30");
    document.getElementById("overall-score").textContent = data.overall;
    document.getElementById("overall-score").style.color = scoreColor;
    document.getElementById("overall-label").textContent = data.overall_label;
    document.getElementById("overall-summary").textContent = data.overall_desc || data.summary;

    // Recommendation banner
    if (data.recommended_reason) {
        document.getElementById("rec-text").textContent = `推荐方案：${data.recommended_reason}`;
        document.getElementById("rec-banner").style.display = "flex";
    }

    // Set original image for slider
    document.getElementById("compare-before").src = `/static/uploads/${data.filename}`;

    // Dimensions with breakdowns (professional 8-dimension system)
    const container = document.getElementById("dimensions-container");
    container.innerHTML = data.dimensions.map((d, i) => {
        const color = d.score >= 85 ? "#34c759" : d.score >= 70 ? "#0071e3" : d.score >= 55 ? "#ff9f0a" : "#ff3b30";
        const level = d.score >= 85 ? "优异" : d.score >= 70 ? "良好" : d.score >= 55 ? "一般" : "不足";
        const breakdownHtml = d.breakdown ? d.breakdown.map(b => {
            const icon = b.ok ? '<span class="bd-ok">OK</span>' : '<span class="bd-warn">!</span>';
            return `<div class="breakdown-item">
                <span class="bd-label">${b.label} ${icon}</span>
                <span class="bd-value" style="color:${b.ok ? 'var(--green)' : 'var(--amber)'}">${b.value}</span>
                <span class="bd-detail">${b.detail || ''}</span>
            </div>`;
        }).join("") : "";

        return `
            <div class="dimension-item" style="animation-delay:${i * 0.06}s;">
                <div class="dimension-header">
                    <div class="dim-name-group">
                        <span class="dim-name">${d.name}</span>
                        <span class="dim-level" style="color:${color}">${level}</span>
                        <span class="dim-weight">权重 ${d.weight || 12}%</span>
                    </div>
                    <span class="dim-score" style="color:${color}">${d.score}</span>
                </div>
                <div class="dim-bar-bg">
                    <div class="dim-bar-fill" style="width:${d.score}%;background:${color};"></div>
                </div>
                <p class="dim-feedback">${d.feedback}</p>
                ${breakdownHtml ? `<button class="dim-breakdown-toggle" onclick="this.nextElementSibling.classList.toggle('open');this.textContent=this.nextElementSibling.classList.contains('open')?'收起评估详情 ▲':'展开评估详情 ▼'">展开评估详情 ▼</button><div class="dim-breakdown">${breakdownHtml}</div>` : ''}
            </div>
        `;
    }).join("");

    // Entertainment: MBTI + Audience
    if (data.mbti) {
        renderEntertainment(data);
    }

    // Set histogram
    if (data.histogram_url) {
        document.getElementById("compare-hist-original").src = data.histogram_url;
    }

    // Style tabs
    renderStyleTabs(data.styles, data.recommended_style);

    // Post-render hooks (radar chart, history, etc.)
    afterRender(data);
}


function renderStyleTabs(styles, recommended) {
    const tabs = document.getElementById("style-tabs");
    tabs.innerHTML = styles.map(s =>
        `<button class="style-tab${s.key === recommended ? ' recommended' : ''}" data-style="${s.key}" onclick="switchStyle('${s.key}')">${s.name}${s.key === recommended ? '<span class="rec-badge">推荐</span>' : ''}</button>`
    ).join("");

    if (recommended) {
        const style = styles.find(s => s.key === recommended);
        document.getElementById("style-desc").textContent = style ? style.description : "";
    }
}

// ===== Entertainment =====
function renderEntertainment(data) {
    const section = document.getElementById("entertainment-section");
    section.classList.remove("hidden");

    const mbti = data.mbti;
    const audience = data.audience;
    const mood = data.mood;

    // Mood
    if (mood) {
        document.getElementById("mood-emoji").textContent = mood.emoji;
        document.getElementById("mood-name").textContent = mood.mood;
        document.getElementById("mood-music").textContent = "🎵 " + mood.music;
        document.getElementById("mood-phrase").textContent = mood.phrase;
    }

    // MBTI
    document.getElementById("mbti-type").textContent = mbti.mbti;
    document.getElementById("mbti-persona").textContent = mbti.persona;
    document.getElementById("mbti-desc").textContent = mbti.persona_desc;

    const dims = document.getElementById("mbti-dims");
    dims.innerHTML = mbti.dimensions.map(d => `
        <div class="mbti-dim-item">
            <span class="mbti-dim-letter">${d.letter}</span>
            <span class="mbti-dim-name">${d.name}</span>
            <div class="mbti-dim-bar-bg"><div class="mbti-dim-bar-fill" style="width:${d.pct || 50}%"></div></div>
            <span class="mbti-dim-choice">${d.choice}</span>
        </div>
    `).join("");

    if (mbti.match_photographer) {
        document.getElementById("mbti-match").innerHTML = `🎞️ <strong>灵魂共鸣的摄影师：</strong>${mbti.match_photographer}<br>📸 <strong>摄影风格：</strong>${mbti.style_preference || ''}`;
    }

    // Audience
    document.getElementById("audience-category").textContent = audience.category;
    document.getElementById("audience-meta").textContent = audience.age_range + " · " + (audience.gender_leaning || "");
    document.getElementById("audience-traits").textContent = audience.traits;
    document.getElementById("audience-interests").innerHTML = audience.interests.map(i =>
        `<span class="audience-interest-tag">${i}</span>`
    ).join("");
    document.getElementById("audience-usecase").textContent = audience.use_case || "";
    if (audience.also_matches) {
        document.getElementById("audience-also").textContent = "也适合：" + audience.also_matches;
    }
}

// ===== Apply Style =====
async function applyStyle(styleKey, description, intensity, styles, recommended) {
    if (!AppState.currentFilename) return;

    document.querySelectorAll(".style-tab").forEach(t => {
        t.classList.remove("active");
        if (t.dataset.style === styleKey) t.classList.add("active");
    });
    document.getElementById("style-desc").textContent = description;
    document.getElementById("intensity-slider").value = Math.round(intensity * 100);
    document.getElementById("intensity-value").textContent = Math.round(intensity * 100) + "%";

    await fetchEnhanced(styleKey, intensity);
}

async function switchStyle(styleKey) {
    if (!AppState.currentFilename) return;
    AppState.currentStyle = styleKey;

    document.querySelectorAll(".style-tab").forEach(t => t.classList.remove("active"));
    const tab = document.querySelector(`[data-style="${styleKey}"]`);
    if (tab) tab.classList.add("active");

    // Get style description from tabs
    const desc = document.getElementById("style-desc");
    const intensity = parseInt(document.getElementById("intensity-slider").value) / 100;

    await fetchEnhanced(styleKey, intensity);
}

async function fetchEnhanced(styleKey, intensity) {
    try {
        const res = await fetch("/api/enhance", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ filename: AppState.currentFilename, style: styleKey, intensity }),
        });
        const data = await res.json();
        if (!res.ok) throw { type: "server", message: data.error || "增强失败" };

        AppState.currentEnhancedFilename = data.enhanced_filename;
        document.getElementById("compare-after").src = `/static/enhanced/${data.enhanced_filename}?t=${Date.now()}`;

        if (data.histogram_url) {
            document.getElementById("compare-hist-enhanced").src = data.histogram_url + `?t=${Date.now()}`;
        }

        // Reset slider to center
        document.getElementById("slider-clip").style.width = "50%";
        document.getElementById("slider-handle").style.left = "50%";
    } catch (err) {
        if (err.type === "server") {
            showError(err.message, "");
        } else if (err.name === "TypeError") {
            showError("网络连接失败", "请检查服务是否正常运行");
        } else {
            showError("增强失败", err.message || "");
        }
    }
}

// ===== Intensity Slider =====
const intensitySlider = document.getElementById("intensity-slider");
let intensityTimeout = null;

intensitySlider.addEventListener("input", () => {
    const val = parseInt(intensitySlider.value);
    document.getElementById("intensity-value").textContent = val + "%";

    // Debounced re-fetch
    if (intensityTimeout) clearTimeout(intensityTimeout);
    intensityTimeout = setTimeout(() => {
        if (AppState.currentStyle) {
            fetchEnhanced(AppState.currentStyle, val / 100);
        }
    }, 300);
});

// ===== Before/After Slider =====
const sliderCompare = document.getElementById("slider-compare");
const sliderHandle = document.getElementById("slider-handle");
const sliderClip = document.getElementById("slider-clip");
let sliderDragging = false;

function getSliderPercent(e) {
    const rect = sliderCompare.getBoundingClientRect();
    const x = (e.touches ? e.touches[0].clientX : e.clientX) - rect.left;
    return Math.max(5, Math.min(95, (x / rect.width) * 100));
}

sliderHandle.addEventListener("mousedown", (e) => {
    e.preventDefault();
    sliderDragging = true;
});
sliderHandle.addEventListener("touchstart", (e) => {
    e.preventDefault();
    sliderDragging = true;
});

document.addEventListener("mousemove", (e) => {
    if (!sliderDragging) return;
    const pct = getSliderPercent(e);
    sliderClip.style.width = pct + "%";
    sliderHandle.style.left = pct + "%";
});
document.addEventListener("touchmove", (e) => {
    if (!sliderDragging) return;
    const pct = getSliderPercent(e);
    sliderClip.style.width = pct + "%";
    sliderHandle.style.left = pct + "%";
});

document.addEventListener("mouseup", () => { sliderDragging = false; });
document.addEventListener("touchend", () => { sliderDragging = false; });

// Click on slider area to jump
sliderCompare.addEventListener("click", (e) => {
    if (e.target === sliderHandle || sliderHandle.contains(e.target)) return;
    const pct = getSliderPercent(e);
    sliderClip.style.width = pct + "%";
    sliderHandle.style.left = pct + "%";
});

// ===== Download =====
document.getElementById("download-btn").addEventListener("click", () => {
    if (AppState.currentEnhancedFilename) {
        window.open(`/api/download/${AppState.currentEnhancedFilename}`, "_blank");
    }
});

// ===== Error Handling =====
function showError(msg, detail) {
    errorMessage.textContent = msg;
    errorDetail.textContent = detail || "";
    uploadSection.classList.add("hidden");
    loadingSection.classList.add("hidden");
    resultsSection.classList.add("hidden");
    errorSection.classList.remove("hidden");

    if (msg.includes("网络")) {
        document.getElementById("error-icon").textContent = "⚡";
    } else if (msg.includes("格式") || msg.includes("过大")) {
        document.getElementById("error-icon").textContent = "📷";
    } else {
        document.getElementById("error-icon").textContent = "!";
    }
}

document.getElementById("retry-btn").addEventListener("click", resetUpload);
document.getElementById("new-photo-btn").addEventListener("click", resetUpload);
document.getElementById("share-btn").addEventListener("click", shareResult);

// ===== Share =====
async function shareResult() {
    const shareBtn = document.getElementById("share-btn");
    shareBtn.textContent = "生成中...";
    shareBtn.disabled = true;

    try {
        // Use cached full result for complete share data
        const r = AppState.lastResult;
        if (!r) {
            shareBtn.textContent = "无可分享数据";
            shareBtn.disabled = false;
            return;
        }

        const res = await fetch("/api/share", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                overall: r.overall,
                overall_label: r.overall_label,
                overall_color: r.overall_color,
                overall_desc: r.overall_desc,
                summary: r.summary,
                recommended_style: r.recommended_style,
                recommended_reason: r.recommended_reason,
                dimensions: r.dimensions,
                filename: AppState.currentFilename,
                histogram_url: AppState.currentHistogramUrl,
                mbti: r.mbti,
                mood: r.mood,
            }),
        });
        const data = await res.json();
        const shareUrl = window.location.origin + data.share_url;

        await navigator.clipboard.writeText(shareUrl);
        shareBtn.textContent = "已复制链接!";
        shareBtn.style.background = "var(--green)";
        shareBtn.style.color = "#fff";
        shareBtn.style.borderColor = "var(--green)";
        setTimeout(() => { shareBtn.textContent = "分享结果"; shareBtn.disabled = false; shareBtn.style = ""; }, 2000);
    } catch (err) {
        shareBtn.textContent = "分享失败";
        shareBtn.disabled = false;
        setTimeout(() => { shareBtn.textContent = "分享结果"; }, 2000);
    }
}

// ===== History =====
const HISTORY_KEY = "photolens_history";
const MAX_HISTORY = 10;

function saveHistory(data) {
    try {
        let history = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
        // Remove duplicate if same filename
        history = history.filter(h => h.filename !== data.filename);
        history.unshift({
            overall: data.overall,
            overall_label: data.overall_label,
            overall_color: data.overall_color,
            filename: data.filename,
            mbti: data.mbti?.mbti || "----",
            mood: data.mood?.mood || "",
            dimensions: data.dimensions.map(d => ({ name: d.name, score: d.score })),
            time: Date.now(),
        });
        if (history.length > MAX_HISTORY) history = history.slice(0, MAX_HISTORY);
        localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
        renderHistoryButton();
    } catch(e) { /* localStorage might be full */ }
}

function renderHistoryButton() {
    let btn = document.getElementById("history-btn");
    if (!btn) {
        btn = document.createElement("button");
        btn.id = "history-btn";
        btn.className = "btn btn-outline btn-sm";
        btn.textContent = "历史记录";
        btn.onclick = showHistory;
        const toolbar = document.querySelector(".result-toolbar");
        if (toolbar) toolbar.prepend(btn);
    }
    const history = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
    btn.style.display = history.length > 0 ? "" : "none";
}

function showHistory() {
    const history = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
    if (!history.length) return;

    let html = '<div class="history-overlay" onclick="this.remove()"><div class="history-panel card" onclick="event.stopPropagation()">';
    html += '<h3 style="margin-bottom:12px">最近分析记录</h3>';
    history.forEach((h, i) => {
        const time = new Date(h.time);
        const timeStr = `${time.getMonth()+1}/${time.getDate()} ${time.getHours()}:${String(time.getMinutes()).padStart(2,'0')}`;
        html += `<div class="history-item" onclick="document.querySelector('.history-overlay').remove()" style="display:flex;align-items:center;gap:12px;padding:8px;border-radius:8px;cursor:pointer;margin-bottom:4px;background:var(--bg-alt)">
            <span style="font-size:28px;font-weight:800;color:${h.overall_color}" onclick="event.stopPropagation()">${h.overall}</span>
            <div style="flex:1"><div style="font-size:13px;font-weight:600">${h.overall_label} · ${h.mbti} · ${h.mood}</div>
            <div style="font-size:11px;color:var(--text-tertiary)">${timeStr}</div></div></div>`;
    });
    html += '<button class="btn btn-outline btn-sm" style="margin-top:8px;width:100%" onclick="localStorage.removeItem(\''+HISTORY_KEY+'\');document.querySelector(\'.history-overlay\').remove();renderHistoryButton()">清除记录</button>';
    html += '</div></div>';
    document.body.insertAdjacentHTML("beforeend", html);
}

// ===== SVG Radar Chart =====
function renderRadarChart(dimensions) {
    const container = document.getElementById("radar-chart");
    if (!container) return;

    const cx = 140, cy = 140, r = 110;
    const n = dimensions.length;
    const angleStep = (Math.PI * 2) / n;
    const levels = 4;

    let svg = `<svg viewBox="0 0 280 280" style="width:100%;max-width:300px;display:block;margin:0 auto 16px">`;

    // Grid rings
    for (let l = 1; l <= levels; l++) {
        const pts = [];
        for (let i = 0; i < n; i++) {
            const a = angleStep * i - Math.PI / 2;
            const rr = (r / levels) * l;
            pts.push(`${cx + Math.cos(a) * rr},${cy + Math.sin(a) * rr}`);
        }
        svg += `<polygon points="${pts.join(' ')}" fill="none" stroke="var(--border-light)" stroke-width="1"/>`;
    }

    // Axis lines
    for (let i = 0; i < n; i++) {
        const a = angleStep * i - Math.PI / 2;
        svg += `<line x1="${cx}" y1="${cy}" x2="${cx + Math.cos(a) * r}" y2="${cy + Math.sin(a) * r}" stroke="var(--border-light)" stroke-width="1"/>`;
    }

    // Data polygon
    const dataPts = [];
    for (let i = 0; i < n; i++) {
        const a = angleStep * i - Math.PI / 2;
        const rr = (dimensions[i].score / 100) * r;
        dataPts.push(`${cx + Math.cos(a) * rr},${cy + Math.sin(a) * rr}`);
    }
    svg += `<polygon points="${dataPts.join(' ')}" fill="rgba(0,113,227,0.12)" stroke="var(--blue)" stroke-width="2" stroke-linejoin="round"/>`;

    // Data points
    for (let i = 0; i < n; i++) {
        const a = angleStep * i - Math.PI / 2;
        const rr = (dimensions[i].score / 100) * r;
        svg += `<circle cx="${cx + Math.cos(a) * rr}" cy="${cy + Math.sin(a) * rr}" r="4" fill="var(--blue)" stroke="#fff" stroke-width="2"/>`;
    }

    // Labels
    for (let i = 0; i < n; i++) {
        const a = angleStep * i - Math.PI / 2;
        const labelR = r + 22;
        const x = cx + Math.cos(a) * labelR;
        const y = cy + Math.sin(a) * labelR;
        const name = dimensions[i].name.length > 4 ? dimensions[i].name.substring(0, 4) : dimensions[i].name;
        svg += `<text x="${x}" y="${y}" text-anchor="middle" dominant-baseline="central" font-size="10" fill="var(--text-secondary)" font-weight="500">${name}</text>`;
    }

    svg += '</svg>';
    container.innerHTML = svg;
}

// Called after renderScores completes — hook in radar chart, history, etc.
function afterRender(data) {
    renderRadarChart(data.dimensions);
    saveHistory(data);
    renderHistoryButton();
}

// SVG gradient helper
function addStop(gradient, offset, color) {
    const stop = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
    stop.setAttribute('offset', offset);
    stop.setAttribute('stop-color', color);
    gradient.appendChild(stop);
}

function hideAllSections() {
    [uploadSection, loadingSection, resultsSection, errorSection].forEach(s => s.classList.add("hidden"));
    const entSection = document.getElementById("entertainment-section");
    if (entSection) entSection.classList.add("hidden");
}
