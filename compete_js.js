/* ===== PhotoLens v4 - MBTI + 受众版 ===== */

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const dropZone = $("#drop-zone");
const fileInput = $("#file-input");
const uploadPreview = $("#upload-preview");
const previewImg = $("#preview-img");
const uploadSection = $("#upload-section");
const loadingSection = $("#loading-section");
const resultsSection = $("#results-section");
const errorSection = $("#error-section");
const errorMessage = $("#error-message");

let currentFilename = null;
let currentEnhancedFilename = null;
let currentFile = null;
let currentHistogramUrl = null;

// ===== 维度图标 =====
const dimIcons = {
  "曝光与影调": '<circle cx="12" cy="12" r="4" stroke="currentColor" stroke-width="2"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
  "色彩与白平衡": '<circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="12" r="5" stroke="currentColor" stroke-width="2" stroke-dasharray="3 3"/>',
  "清晰度与细节": '<circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1" stroke-dasharray="2 2"/><path d="M12 2v20M2 12h20" stroke="currentColor" stroke-width="1" stroke-dasharray="2 2"/>',
  "构图与设计": '<rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" stroke-width="2"/><path d="M9 3v18M15 3v18M3 9h18M3 15h18" stroke="currentColor" stroke-width="1" stroke-dasharray="3 3"/>',
  "视觉元素运用": '<polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5" stroke="currentColor" stroke-width="2"/><line x1="12" y1="22" x2="12" y2="15.5" stroke="currentColor" stroke-width="1"/>',
  "情感与故事性": '<path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" stroke="currentColor" stroke-width="2" fill="none"/>',
  "整体完成度": '<circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/><path d="M12 2a10 10 0 0 1 7 17M12 22a10 10 0 0 1-7-17" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>',
};

// ===== 上传处理 =====
dropZone.addEventListener("click", () => fileInput.click());
dropZone.addEventListener("dragover", (e) => { e.preventDefault(); dropZone.classList.add("drag-over"); });
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
dropZone.addEventListener("drop", (e) => {
  e.preventDefault(); dropZone.classList.remove("drag-over");
  if (e.dataTransfer.files.length > 0) handleFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener("change", () => { if (fileInput.files.length > 0) handleFile(fileInput.files[0]); });
$("#reupload-btn").addEventListener("click", resetUpload);

function handleFile(file) {
  if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) return showError("仅支持 JPG、PNG、WebP 格式");
  if (file.size > 20 * 1024 * 1024) return showError("文件大小不能超过 20MB");
  currentFile = file;
  const reader = new FileReader();
  reader.onload = (e) => { previewImg.src = e.target.result; dropZone.style.display = "none"; uploadPreview.classList.remove("hidden"); };
  reader.readAsDataURL(file);
}

function resetUpload() {
  dropZone.style.display = ""; uploadPreview.classList.add("hidden");
  fileInput.value = ""; currentFilename = null; currentEnhancedFilename = null; currentFile = null;
  hideAll(); uploadSection.classList.remove("hidden");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// ===== 分析 =====
$("#analyze-btn").addEventListener("click", analyzePhoto);

async function analyzePhoto() {
  const file = currentFile || (fileInput.files.length > 0 ? fileInput.files[0] : null);
  if (!file) return;
  uploadSection.classList.add("hidden"); errorSection.classList.add("hidden");
  loadingSection.classList.remove("hidden"); resultsSection.classList.add("hidden");
  window.scrollTo({ top: loadingSection.offsetTop - 80, behavior: "smooth" });

  const fd = new FormData(); fd.append("file", file);
  try {
    const res = await fetch("/api/analyze", { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "分析失败");
    currentFilename = data.filename;
    currentHistogramUrl = data.histogram_url;
    renderResults(data);
    loadingSection.classList.add("hidden"); resultsSection.classList.remove("hidden");
    setTimeout(() => $("#results-section").scrollIntoView({ behavior: "smooth", block: "start" }), 150);
    const recStyle = data.recommended_style || (data.styles.length > 0 ? data.styles[0].key : null);
    if (recStyle) {
      const style = data.styles.find((s) => s.key === recStyle);
      await applyStyle(recStyle, style ? style.description : "");
    }
  } catch (err) { loadingSection.classList.add("hidden"); showError(err.message); }
}

// ===== 渲染 =====
function renderResults(data) {
  // --- 综合评分环 ---
  const circ = 2 * Math.PI * 52;
  const ring = $("#ring-progress");
  ring.style.strokeDashoffset = circ * (1 - data.overall / 100);
  ring.style.stroke = data.overall_color;
  const scoreEl = $("#overall-score");
  scoreEl.textContent = data.overall;
  scoreEl.style.color = data.overall_color;
  $("#overall-label").textContent = data.overall_label;
  $("#overall-summary").textContent = data.summary;

  const goodDims = data.dimensions.filter(d => d.score >= 82);
  $("#score-badges").innerHTML = goodDims.slice(0, 3).map(d =>
    `<span class="score-badge badge-excellent">${d.name.split("与")[0]}: ${d.score}分</span>`
  ).join("");

  $("#original-img").src = `/uploads/${data.filename}`;
  $("#comparison-original").src = `/uploads/${data.filename}`;
  if (data.histogram_url) {
    $("#original-histogram").src = data.histogram_url;
    $("#compare-hist-original").src = data.histogram_url;
  }

  const img = new Image();
  img.onload = () => {
    const meta = $(".image-meta");
    if (meta) meta.innerHTML = `
      <div class="image-meta-item"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/></svg>${img.naturalWidth} × ${img.naturalHeight}</div>
      <div class="image-meta-item"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>${fmtSize(currentFile?.size || 0)}</div>`;
  };
  img.src = `/uploads/${data.filename}`;

  // --- 7维评分 ---
  const dimsContainer = $("#dimensions-container");
  dimsContainer.innerHTML = data.dimensions.map((d, i) => {
    const color = d.score >= 85 ? "var(--green)" : d.score >= 70 ? "var(--blue)" : d.score >= 55 ? "var(--amber)" : "var(--red)";
    const icon = dimIcons[d.name] || "";
    return `<div class="dimension-item" style="animation: fadeInUp 0.4s ease ${i * 0.05}s both;">
      <div class="dimension-header">
        <span class="dim-name"><svg class="dim-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" style="color:${color}">${icon}</svg>${d.name}</span>
        <div class="dim-score-wrap"><span class="dim-score" style="color:${color}">${d.score}</span><span class="dim-score-max">/100</span></div>
      </div>
      <div class="dim-bar-bg"><div class="dim-bar-fill" style="width:${d.score}%;background:${color};"></div></div>
      <p class="dim-feedback">${d.feedback}</p>
    </div>`;
  }).join("");

  // --- MBTI 卡片 ---
  if (data.mbti) {
    renderMBTI(data.mbti);
  }

  // --- 受众卡片 ---
  if (data.audience) {
    renderAudience(data.audience);
  }

  // --- 风格标签 ---
  const tabs = $("#style-tabs");
  const rec = data.recommended_style;
  tabs.innerHTML = data.styles.map(s =>
    `<button class="style-tab${s.key === rec ? " recommended" : ""}" data-style="${s.key}" onclick="applyStyle('${s.key}', '${esc(s.description)}')">${s.name}${s.key === rec ? '<span class="rec-badge">推荐</span>' : ""}</button>`
  ).join("");

  if (data.recommended_reason) $("#style-desc").textContent = data.recommended_reason;
  $("#download-btn").onclick = () => {
    if (currentEnhancedFilename) window.open(`/api/download/${currentEnhancedFilename}`, "_blank");
  };
}

// ===== MBTI 渲染 =====
function renderMBTI(mbti) {
  const el = $("#mbti-section");
  if (!el) return;
  el.classList.remove("hidden");

  const dimColors = {
    E: "#ff6b6b", I: "#4ecdc4",
    S: "#45b7d1", N: "#a29bfe",
    T: "#6366f1", F: "#e84393",
    J: "#fdcb6e", P: "#00b894",
  };

  const letters = mbti.type.split("");
  const dims = [
    { key: "IE", left: "E", right: "I", label: "专注方式" },
    { key: "SN", left: "S", right: "N", label: "认知方式" },
    { key: "TF", left: "T", right: "F", label: "决策方式" },
    { key: "JP", left: "J", right: "P", label: "生活方式" },
  ];

  // 维度条
  const barsHtml = dims.map(d => {
    const dim = mbti.dimensions[d.key];
    const leftPct = dim.direction === d.left ? Math.round(50 + dim.score * 0.56) : Math.round(50 - Math.abs(dim.score) * 0.56);
    const activeLetter = dim.direction;
    const activeColor = dimColors[activeLetter];
    return `
      <div class="mbti-dim-row">
        <span class="mbti-dim-label">${d.label}</span>
        <div class="mbti-dim-bar-wrap">
          <div class="mbti-dim-bar">
            <div class="mbti-dim-fill" style="width:${leftPct}%;background:${activeColor}"></div>
          </div>
          <div class="mbti-dim-labels">
            <span class="${dim.direction === d.left ? 'mbti-active' : ''}" style="color:${dim.direction === d.left ? activeColor : 'var(--text3)'}">${d.left}</span>
            <span class="${dim.direction === d.right ? 'mbti-active' : ''}" style="color:${dim.direction === d.right ? activeColor : 'var(--text3)'}">${d.right}</span>
          </div>
        </div>
      </div>`;
  }).join("");

  // 性格标签
  const traitsHtml = (mbti.traits || []).map(t => `<span class="mbti-trait-tag">${t}</span>`).join("");

  el.innerHTML = `
    <h3 class="panel-title">
      <svg class="panel-icon" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="4"/><path d="M5 20c0-4 3.1-7 7-7s7 3 7 7"/></svg>
      照片人格 · MBTI 推测
    </h3>
    <div class="mbti-main">
      <div class="mbti-type-large">
        ${letters.map((l, i) => 
          `<span class="mbti-letter-box" style="background:${dimColors[l]}20;border-color:${dimColors[l]};color:${dimColors[l]};animation: scaleIn 0.3s ease ${0.15 + i * 0.1}s both;">${l}</span>`
        ).join("")}
      </div>
      <div class="mbti-confidence">推测置信度 <strong>${mbti.confidence}%</strong></div>
    </div>
    <div class="mbti-dims">${barsHtml}</div>
    <div class="mbti-traits">${traitsHtml}</div>
    <p class="mbti-desc">${mbti.description}</p>
  `;
}

// ===== 受众渲染 =====
function renderAudience(audience) {
  const el = $("#audience-section");
  if (!el) return;
  el.classList.remove("hidden");

  const topList = audience.topAudiences || [];
  const audienceHtml = topList.map((a, i) => `
    <div class="audience-item" style="animation: fadeInUp 0.4s ease ${0.2 + i * 0.1}s both;">
      <div class="audience-header">
        <span class="audience-emoji">${a.emoji}</span>
        <span class="audience-label">${a.label}</span>
        <span class="audience-pct">${a.pct}%</span>
      </div>
      <div class="audience-bar"><div class="audience-bar-fill" style="width:${a.pct}%"></div></div>
      <p class="audience-desc">${a.desc}</p>
    </div>
  `).join("");

  el.innerHTML = `
    <h3 class="panel-title">
      <svg class="panel-icon" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="9" cy="7" r="4"/><circle cx="17" cy="8" r="3"/><path d="M2 20c0-4 2.7-7 7-7s7 3 7 7"/><path d="M13 20c0-3 2-5 4-5s4 2 4 5"/></svg>
      谁会喜欢这张照片？
    </h3>
    <div class="audience-list">${audienceHtml}</div>
    <div class="audience-age">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
      ${audience.ageGroup}
    </div>
    <p class="audience-summary">${audience.summary}</p>
  `;
}

// ===== 增强 =====
async function applyStyle(key, desc) {
  if (!currentFilename) return;
  $$(".style-tab").forEach(t => t.classList.remove("active"));
  const tab = $(`[data-style="${key}"]`);
  if (tab) tab.classList.add("active");
  $("#style-desc").textContent = desc;
  const area = $("#enhanced-area");
  area.classList.add("loading");
  try {
    const res = await fetch("/api/enhance", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ filename: currentFilename, style: key }) });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "增强失败");
    currentEnhancedFilename = data.enhanced_filename;
    $("#comparison-enhanced").src = `/enhanced/${data.enhanced_filename}?t=${Date.now()}`;
    if (currentHistogramUrl) $("#compare-hist-original").src = currentHistogramUrl;
    if (data.histogram_url) $("#compare-hist-enhanced").src = data.histogram_url + `?t=${Date.now()}`;
  } catch (err) { showError(err.message); } finally { area.classList.remove("loading"); }
}

// ===== 错误 =====
function showError(msg) {
  errorMessage.textContent = msg;
  uploadSection.classList.add("hidden"); loadingSection.classList.add("hidden");
  resultsSection.classList.add("hidden"); errorSection.classList.remove("hidden");
}
$("#retry-btn").addEventListener("click", resetUpload);
function hideAll() { [uploadSection, loadingSection, resultsSection, errorSection].forEach(s => s.classList.add("hidden")); }

// ===== 工具函数 =====
function esc(s) { return s.replace(/'/g, "\\'").replace(/"/g, "&quot;"); }
function fmtSize(b) {
  if (!b) return "0 B";
  const u = ["B", "KB", "MB"]; let i = 0, s = b;
  while (s >= 1024 && i < u.length - 1) { s /= 1024; i++; }
  return s.toFixed(i > 0 ? 1 : 0) + " " + u[i];
}

// Ctrl+V 粘贴
document.addEventListener("keydown", (e) => {
  if (e.ctrlKey && e.key === "v") {
    const items = e.clipboardData?.items;
    if (items) for (const item of items) { if (item.type.startsWith("image/")) { e.preventDefault(); handleFile(item.getAsFile()); break; } }
  }
  if (e.key === "Escape" && !resultsSection.classList.contains("hidden")) resetUpload();
});

const ss = document.createElement("style");
ss.textContent = `@keyframes fadeInUp { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: translateY(0); } } @keyframes scaleIn { from { opacity: 0; transform: scale(0.85); } to { opacity: 1; transform: scale(1); } }`;
document.head.appendChild(ss);
