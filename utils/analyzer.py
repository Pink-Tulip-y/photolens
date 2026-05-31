"""
Professional Photography Scoring System
Based on PPA 12 Elements + 全国摄影艺术展览评审标准
Reference: https://www.ppa.com/the-12-elements-of-a-merit-image
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw
from skimage.filters import sobel


# ============================================================
# Dimension 1: 视觉冲击力 (Visual Impact) — PPA Element #1
# Composite of color vividness, tonal contrast, and edge energy.
# ============================================================
def analyze_impact(image_rgb):
    hsv = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)

    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    mean_sat = sat.mean()
    std_val = val.std()

    # Edge energy as proxy for visual dynamism
    edges = sobel(gray)
    edge_energy = edges.std()

    # Brightness range
    p5, p95 = np.percentile(val, (5, 95))
    brightness_range = p95 - p5

    # Score: reward high saturation, wide brightness range, strong edges
    score = 40 + mean_sat * 0.15 + min(30, edge_energy * 0.5) + min(20, brightness_range * 0.06)

    breakdown = [
        {"label": "色彩鲜活力", "value": f"{mean_sat:.0f}", "ok": mean_sat > 60, "detail": "饱和度均值，反映色彩冲击力"},
        {"label": "画面动感", "value": f"{edge_energy:.1f}", "ok": edge_energy > 20, "detail": "边缘能量，越高画面越有张力"},
        {"label": "明暗跨幅", "value": f"{brightness_range:.0f}", "ok": brightness_range > 100, "detail": "最亮与最暗区域的跨度"},
    ]

    if score >= 85:
        feedback = "画面极具冲击力，色彩与光影的运用令人过目难忘。"
    elif score >= 70:
        feedback = "视觉表现力良好，主体突出，能够抓住观众注意力。"
    elif score >= 55:
        feedback = "具有一定的视觉表现力，可尝试强化色彩或光影对比提升感染力。"
    else:
        feedback = "视觉冲击力较弱，建议从色彩对比或构图张力入手增强画面吸引力。"

    return round(min(100, max(15, score))), feedback, breakdown


# ============================================================
# Dimension 2: 曝光与光影 (Exposure & Lighting) — PPA #9
# Evaluates exposure accuracy and light quality.
# ============================================================
def analyze_exposure(image_rgb):
    gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
    hist_norm = hist / hist.sum()

    dark_pct = hist_norm[:40].sum() * 100
    bright_pct = hist_norm[240:].sum() * 100
    mid_pct = hist_norm[50:200].sum() * 100
    mean_brightness = gray.mean()

    # Detect highlight clipping
    highlight_clip = hist_norm[250:].sum() * 100
    shadow_clip = hist_norm[:10].sum() * 100

    breakdown = [
        {"label": "暗部占比", "value": f"{dark_pct:.0f}%", "ok": dark_pct < 25, "detail": "亮度<40的像素比例"},
        {"label": "高光占比", "value": f"{bright_pct:.0f}%", "ok": bright_pct < 10, "detail": "亮度>240的像素比例"},
        {"label": "中间调占比", "value": f"{mid_pct:.0f}%", "ok": mid_pct > 55, "detail": "丰富的中间调是好照片的基础"},
        {"label": "高光溢出", "value": f"{highlight_clip:.1f}%", "ok": highlight_clip < 2, "detail": "亮度>250的死白区域"},
        {"label": "暗部死黑", "value": f"{shadow_clip:.1f}%", "ok": shadow_clip < 3, "detail": "亮度<10的纯黑区域"},
    ]

    if dark_pct > 50:
        score = max(10, 50 - (dark_pct - 50) * 1.2)
        feedback = "严重欠曝。暗部丢失大量细节，建议增加曝光或后期提亮阴影。"
    elif bright_pct > 30:
        score = max(10, 55 - (bright_pct - 30) * 1.2)
        feedback = "高光溢出严重。建议降低曝光或使用渐变镜控制光比。"
    elif dark_pct > 25:
        score = 65 - (dark_pct - 25) * 0.7
        feedback = "暗部稍多。可适当提亮阴影区域以展现更多细节。"
    elif bright_pct > 12:
        score = 72 - (bright_pct - 12) * 0.8
        feedback = "高光区域略多。注意保留高光细节层次。"
    elif 50 < mean_brightness < 190 and mid_pct > 55:
        score = 88 + min(12, mid_pct * 0.1)
        feedback = "曝光精准，明暗分布均衡，光影层次丰富。"
    else:
        score = 72
        feedback = "曝光基本合理，可微调以优化光影表现。"

    return round(min(100, max(10, score))), feedback, breakdown


# ============================================================
# Dimension 3: 色彩表现 (Color Quality) — PPA #7
# Evaluates color harmony, saturation distribution, and balance.
# ============================================================
def analyze_color(image_rgb):
    hsv = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2HSV)
    saturation = hsv[:, :, 1]
    hue = hsv[:, :, 0].astype(float)

    mean_sat = saturation.mean()
    std_sat = saturation.std()

    # Color diversity: how spread out the hue distribution is
    hue_hist = cv2.calcHist([hsv], [0], None, [36], [0, 180]).flatten()
    hue_hist_norm = hue_hist / (hue_hist.sum() + 1e-8)
    hue_entropy = -np.sum(hue_hist_norm * np.log(hue_hist_norm + 1e-8))
    hue_diversity = hue_entropy / np.log(36) * 100  # Normalize

    # Color balance: LAB a/b channel offsets
    lab = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2LAB)
    a_shift = abs(lab[:, :, 1].astype(float).mean() - 128)
    b_shift = abs(lab[:, :, 2].astype(float).mean() - 128)
    color_cast = a_shift + b_shift

    breakdown = [
        {"label": "饱和度均值", "value": f"{mean_sat:.0f}", "ok": 50 < mean_sat < 180, "detail": "整体色彩鲜艳程度"},
        {"label": "色彩丰富度", "value": f"{hue_diversity:.0f}%", "ok": hue_diversity > 50, "detail": "色相分布的多样性"},
        {"label": "色彩偏色", "value": "轻微" if color_cast < 60 else "明显", "ok": color_cast < 60, "detail": "LAB空间的色偏程度"},
    ]

    if mean_sat < 25:
        score = max(10, 35 + mean_sat * 0.8)
        feedback = "色彩极度匮乏，画面接近灰度。建议增强色彩或考虑黑白处理。"
    elif mean_sat > 210:
        score = max(10, 70 - (mean_sat - 210) * 0.5)
        feedback = "饱和度过高，色彩失真。适当降低饱和度可获得更自然的观感。"
    elif color_cast > 60:
        score = max(30, 68 - (color_cast - 60) * 0.2)
        feedback = "存在可感知的偏色。建议校正白平衡以获得准确的色彩还原。"
    elif hue_diversity < 30:
        score = 55 + mean_sat * 0.1
        feedback = "色调较为单一。适度引入色彩对比可丰富画面表现力。"
    else:
        score = 78 + min(22, std_sat * 0.1 + hue_diversity * 0.1)
        feedback = "色彩表现优秀，和谐而有层次，色调处理专业到位。"

    return round(min(100, max(10, score))), feedback, breakdown


# ============================================================
# Dimension 4: 清晰度与质感 (Sharpness & Detail) — PPA #2, #11
# Evaluates image sharpness, focus accuracy, and texture quality.
# ============================================================
def analyze_sharpness(image_rgb):
    gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)

    # Laplacian variance — standard sharpness metric
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

    # Edge density: how much fine detail exists
    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    edge_mag = np.sqrt(sobel_x**2 + sobel_y**2)
    edge_density = (edge_mag > 20).sum() / gray.size * 100

    # Texture complexity: downscale then compute local contrast
    h, w = gray.shape
    small = cv2.resize(gray, (min(w, 200), min(h, 200)))
    # Simple texture: mean of local standard deviations using 5x5 blocks
    kernel = np.ones((5, 5), np.float32) / 25
    local_mean = cv2.filter2D(small.astype(np.float32), -1, kernel)
    local_sq_mean = cv2.filter2D((small.astype(np.float32))**2, -1, kernel)
    local_var = np.maximum(0, local_sq_mean - local_mean**2)
    texture_score = float(np.sqrt(local_var).mean())

    breakdown = [
        {"label": "边缘锐度", "value": f"{laplacian_var:.0f}", "ok": laplacian_var > 100, "detail": "Laplacian方差，越高越清晰"},
        {"label": "细节密度", "value": f"{edge_density:.1f}%", "ok": edge_density > 5, "detail": "可辨识边缘像素占比"},
        {"label": "纹理质感", "value": f"{texture_score:.1f}", "ok": texture_score > 8, "detail": "局部纹理丰富程度"},
    ]

    if laplacian_var < 30:
        score = max(5, laplacian_var * 1.2)
        feedback = "画面模糊。建议检查对焦准确性，使用三脚架或提高快门速度。"
    elif laplacian_var < 100:
        score = 35 + (laplacian_var - 30) * 0.6
        feedback = "清晰度偏低。可能轻微失焦或手抖，建议后期适当锐化。"
    elif laplacian_var < 400:
        score = 65 + (laplacian_var - 100) * 0.05
        feedback = "清晰度良好，对焦准确，细节表现可接受。"
    elif laplacian_var < 1500:
        score = 80 + (laplacian_var - 400) * 0.012
        feedback = "清晰度优秀，纹理细节丰富，画质表现出色。"
    else:
        score = 93
        feedback = "锐度极高，细节毕现，达到了专业级的画质水准。"

    return round(min(100, max(5, score))), feedback, breakdown


# ============================================================
# Dimension 5: 构图设计 (Composition & Design) — PPA #5, #8
# Evaluates rule-of-thirds adherence, balance, and center of interest.
# ============================================================
def analyze_composition(image_rgb):
    h, w = image_rgb.shape[:2]
    gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)

    edges = sobel(gray)
    thresh = np.percentile(edges, 90)
    edge_mask = edges > thresh

    third_x1, third_x2 = w // 3, 2 * w // 3
    third_y1, third_y2 = h // 3, 2 * h // 3

    # Third lines analysis
    if w > 0 and h > 0:
        left_third = edge_mask[:, third_x1-3:third_x1+3].sum()
        right_third = edge_mask[:, third_x2-3:third_x2+3].sum()
        top_third = edge_mask[third_y1-3:third_y1+3, :].sum()
        bottom_third = edge_mask[third_y2-3:third_y2+3, :].sum()
        center_region = edge_mask[third_y1:2*third_y2, third_x1:2*third_x2].sum()
        total_edges = edge_mask.sum() + 1e-8
        line_ratio = (left_third + right_third + top_third + bottom_third) / total_edges
        center_ratio = center_region / total_edges

        # Improved thirds score: reward edges on thirds, penalize everything in center
        thirds_adherence = min(100, 35 + line_ratio * 130 + max(0, 0.5 - center_ratio) * 120)
    else:
        thirds_adherence = 50
        center_ratio = 0.5

    # Symmetry / balance score
    left_half = gray[:, :w//2]
    right_half = gray[:, w//2:]
    right_flipped = cv2.flip(right_half, 1)
    min_cols = min(left_half.shape[1], right_flipped.shape[1])
    diff = np.abs(left_half[:, :min_cols].astype(float) - right_flipped[:, :min_cols].astype(float))
    balance_score = max(30, 100 - diff.mean() / 255 * 130)

    # Negative space ratio
    low_detail = (edge_mask == False).sum() / edge_mask.size * 100

    score = thirds_adherence * 0.5 + balance_score * 0.3
    # Reward some negative space but not too much
    if 30 < low_detail < 70:
        score += 5
    elif low_detail >= 80:
        score -= 5

    breakdown = [
        {"label": "三分法则", "value": f"{thirds_adherence:.0f}分", "ok": thirds_adherence > 55, "detail": "关键元素是否位于三分线附近"},
        {"label": "画面均衡", "value": f"{balance_score:.0f}分", "ok": balance_score > 50, "detail": "左右半画面的视觉重量平衡"},
        {"label": "留白空间", "value": f"{low_detail:.0f}%", "ok": 20 < low_detail < 70, "detail": "低细节区域占比（呼吸感）"},
        {"label": "主体聚焦", "value": "适中" if 0.3 < center_ratio < 0.6 else "分散/集中", "ok": 0.3 < center_ratio < 0.6, "detail": "主体是否在画面中占据合适比例"},
    ]

    if score >= 85:
        feedback = "构图精湛。视觉引导自然流畅，主体位置和画面平衡堪称典范。"
    elif score >= 70:
        feedback = "构图良好。主体突出，画面布局合理，建议关注三分法则的精细运用。"
    elif score >= 55:
        feedback = "构图可优化。尝试将主体置于三分线交点，适当留白增加呼吸感。"
    else:
        feedback = "构图需要加强。建议学习三分法则、引导线和正负空间等基本构图原理。"

    score = max(20, min(95, score))
    return round(score), feedback, breakdown


# ============================================================
# Dimension 6: 影调层次 (Tonal Range & Depth) — PPA #2, 国展 技术质量
# Evaluates dynamic range, tonal gradation, and contrast quality.
# ============================================================
def analyze_tonal_range(image_rgb):
    gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
    hist_norm = hist / hist.sum()

    # Key metrics
    cumulative = np.cumsum(hist_norm)
    p5 = np.searchsorted(cumulative, 0.05)
    p95 = np.searchsorted(cumulative, 0.95)
    dynamic_range = p95 - p5

    local_contrast = gray.std()

    # Tonal smoothness: histogram continuity
    hist_diff = np.abs(np.diff(hist_norm)).sum()
    tonal_smoothness = max(0, 100 - hist_diff * 200)

    # Three-quarter tone analysis
    quarter_pts = [np.searchsorted(cumulative, q * 0.25) for q in range(1, 4)]
    tonal_distribution = "均衡" if abs(quarter_pts[1] - 128) < 40 else "偏亮" if quarter_pts[1] > 170 else "偏暗"

    breakdown = [
        {"label": "动态范围", "value": f"{dynamic_range}", "ok": dynamic_range > 90, "detail": "5%-95%亮度跨度"},
        {"label": "影调分布", "value": tonal_distribution, "ok": tonal_distribution == "均衡", "detail": "各亮度区间的分布特征"},
        {"label": "局部对比", "value": f"{local_contrast:.1f}", "ok": local_contrast > 30, "detail": "像素间亮度差异（质感来源）"},
        {"label": "过渡平滑度", "value": f"{tonal_smoothness:.0f}%", "ok": tonal_smoothness > 80, "detail": "灰度过渡是否自然（无断层）"},
    ]

    if dynamic_range < 30:
        score = max(10, dynamic_range * 1.5)
        feedback = "影调层次严重缺失，画面灰雾感重。建议使用色阶工具重新定义黑白场。"
    elif dynamic_range < 70:
        score = 30 + (dynamic_range - 30) * 0.7
        feedback = "影调层次不足。建议通过曲线调整增强中间调的层次过渡。"
    elif local_contrast < 20:
        score = 55
        feedback = "整体影调偏平。可尝试局部对比度增强来提升立体感。"
    elif dynamic_range > 150 and local_contrast > 45:
        score = 92
        feedback = "影调层次极其丰富，从暗部到高光过渡细腻自然，媲美专业级作品。"
    else:
        score = 68 + dynamic_range * 0.1 + local_contrast * 0.2
        score = min(90, score)
        feedback = "影调层次表现良好，明暗过渡自然，画面具有较好的立体感。"

    return round(min(100, max(10, score))), feedback, breakdown


# ============================================================
# Dimension 7: 氛围营造 (Atmosphere & Mood) — PPA Impact + 国展 艺术表现
# Synthesizes lighting warmth, color temperature, and tonal mood.
# ============================================================
def analyze_atmosphere(image_rgb):
    lab = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2LAB)
    hsv = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2HSV)

    l_channel = lab[:, :, 0].astype(float)
    a_channel = lab[:, :, 1].astype(float) - 128
    b_channel = lab[:, :, 2].astype(float) - 128

    # Warmth: positive b = warm (yellow), negative b = cool (blue)
    warmth_score = b_channel.mean()
    # Tone consistency: low variance in a/b = coherent mood
    tone_variance = a_channel.std() + b_channel.std()

    # Brightness distribution shape
    l_hist = cv2.calcHist([l_channel.astype(np.uint8)], [0], None, [10], [0, 256]).flatten()
    l_hist_norm = l_hist / (l_hist.sum() + 1e-8)
    l_entropy = -np.sum(l_hist_norm * np.log(l_hist_norm + 1e-8))
    lighting_complexity = l_entropy / np.log(10) * 100

    # Atmosphere clarity: how intentional the lighting feels
    # Strong value variance with coherent color = strong atmosphere
    atmosphere_strength = min(100, l_channel.std() * 0.4 + (100 - min(100, tone_variance * 0.8)) * 0.5)

    breakdown = [
        {"label": "色调倾向", "value": "暖调" if warmth_score > 15 else "冷调" if warmth_score < -15 else "中性", "ok": abs(warmth_score) > 0, "detail": "LAB B通道均值（暖/冷色调倾向）"},
        {"label": "光影复杂度", "value": f"{lighting_complexity:.0f}%", "ok": lighting_complexity > 60, "detail": "亮度分布的多样性（光影变化程度）"},
        {"label": "色调统一性", "value": "统一" if tone_variance < 40 else "多样", "ok": tone_variance < 50, "detail": "AB通道标准差（色调是否协调统一）"},
    ]

    score = atmosphere_strength

    if score >= 80:
        feedback = "氛围感极强，光影与色调共同营造出独特而富有感染力的情绪空间。"
    elif score >= 65:
        feedback = "画面有较好的氛围感，色调与光影形成了可感知的情绪基调。"
    elif score >= 50:
        feedback = "氛围感适中。可尝试通过色调统一或光影强化来增强画面的情绪表达。"
    else:
        feedback = "氛围感较弱。画面缺少明确的情绪基调，建议从光线方向和色调统一入手。"

    return round(min(100, max(15, score))), feedback, breakdown


# ============================================================
# Dimension 8: 风格表现 (Style & Originality) — PPA #3, #4 + 国展 创新性
# Evaluates how distinctive and stylistically coherent the image is.
# ============================================================
def analyze_style(image_rgb):
    hsv = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2HSV)
    lab = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2LAB)

    # Style uniqueness: deviation from "average photo" characteristics
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]

    # High style = distinctive saturation profile + unique brightness distribution
    sat_uniqueness = min(100, abs(sat.mean() - 100) * 0.5 + sat.std() * 0.3)

    # Brightness style: high-key vs low-key vs balanced
    mean_val = val.mean()
    if mean_val > 170:
        brightness_style = "高调 (High Key)"
    elif mean_val < 70:
        brightness_style = "低调 (Low Key)"
    else:
        brightness_style = "中间调"

    # Tonemap style: whether the image has a distinctive look
    # Check for dominant color channel
    b, g, r = image_rgb[:, :, 0].mean(), image_rgb[:, :, 1].mean(), image_rgb[:, :, 2].mean()
    channel_spread = max(b, g, r) - min(b, g, r)
    color_stylization = min(100, channel_spread * 0.4)

    # Overall style score
    score = sat_uniqueness * 0.4 + color_stylization * 0.3 + 30
    if brightness_style != "中间调":
        score += 10  # Intentional high-key or low-key suggests style

    breakdown = [
        {"label": "亮度风格", "value": brightness_style, "ok": brightness_style != "中间调", "detail": "高调/低调/中间调——风格化的亮度选择"},
        {"label": "色彩风格化", "value": f"{color_stylization:.0f}%", "ok": color_stylization > 30, "detail": "色彩偏离中性灰的程度（风格化程度）"},
        {"label": "饱和度个性", "value": f"{sat_uniqueness:.0f}%", "ok": sat_uniqueness > 40, "detail": "饱和度分布是否具有独特个性"},
    ]

    if score >= 80:
        feedback = "风格鲜明独特，具有强烈的个人视觉语言和艺术辨识度。"
    elif score >= 65:
        feedback = "具有可辨识的风格特征，画面呈现出了一定的个性化表达。"
    elif score >= 50:
        feedback = "风格特征初显，建议进一步强化色彩或影调的个人化处理。"
    else:
        feedback = "风格特征不显著。可尝试定义自己的色彩偏好或影调风格来建立个人视觉标识。"

    return round(min(100, max(15, score))), feedback, breakdown


# ============================================================
# Professional Grading Scale (BIPP-inspired)
# 91-100: 金级 (Gold)     — 专业卓越
# 85-90:  银级 (Silver)   — 高度专业
# 80-84:  铜级 (Bronze)   — 优秀专业水准
# 70-79:  嘉奖 (Merit)     — 良好
# 55-69:  入围 (Selected)  — 有提升空间
# <55:    习作 (Study)     — 需改进
# ============================================================
def professional_grade(score):
    if score >= 91: return "金级", "#F5A623", "专业卓越 —— 技术与艺术兼优，具备竞赛获奖潜质"
    if score >= 85: return "银级", "#A0A0B0", "高度专业 —— 品质出众，在大多数维度表现亮眼"
    if score >= 80: return "铜级", "#CD7F32", "优秀水准 —— 达到专业入门水平，个别维度可继续打磨"
    if score >= 70: return "嘉奖", "#3b82f6", "良好 —— 照片质量不错，有明确的提升方向"
    if score >= 55: return "入围", "#f59e0b", "有潜力 —— 具备基本素质，部分维度需要重点关注"
    return "习作", "#ef4444", "需改进 —— 建议从基础技术开始系统提升"


# ============================================================
# Style Recommendation (unchanged logic, updated for 8 dims)
# ============================================================
def recommend_style(scores):
    exp = scores["exposure"]
    col = scores["color"]
    shr = scores["sharpness"]
    cmp = scores["composition"]
    atm = scores["atmosphere"]
    sty = scores["style"]

    if exp < 40:
        return {"style_key": "natural",
                "reason": "曝光存在明显问题，自然风格能先修正基础光影，是当前最需要的优化"}
    if col < 35:
        return {"style_key": "blackwhite",
                "reason": "色彩表现较弱，转为黑白可以扬长避短，突出光影和结构之美"}
    if col < 55:
        return {"style_key": "vivid",
                "reason": "色彩饱和度不足，鲜明风格可显著提升画面的色彩感染力"}
    if shr < 40:
        return {"style_key": "natural",
                "reason": "清晰度偏低，自然风格的锐化处理能有效增强细节表现力"}
    if atm >= 70 and cmp >= 60:
        return {"style_key": "cinematic",
                "reason": "氛围和构图有良好基础，电影感调色能进一步强化画面的叙事张力"}
    if sty >= 65:
        return {"style_key": "japan",
                "reason": "照片已有一定风格表现力，日系清新处理能增添通透的高级感"}
    if cmp >= 55 and col >= 55:
        return {"style_key": "cinematic",
                "reason": "构图和色彩基础不错，电影感调色能赋予画面更强的艺术氛围"}
    if exp >= 70 and col >= 65 and shr >= 60:
        return {"style_key": "retro",
                "reason": "照片技术底子扎实，复古胶片调色能赋予画面独特的叙事韵味"}

    return {"style_key": "natural",
            "reason": "综合评估后，自然风格是最适合当前照片的优化方案"}


# ============================================================
# Main Analysis Pipeline
# ============================================================

def run_all_analyses(image_rgb):
    """Run all 8 dimension analyses on an RGB image array. Returns raw scores dict."""
    impact_score, impact_fb, impact_bd = analyze_impact(image_rgb)
    exposure_score, exposure_fb, exposure_bd = analyze_exposure(image_rgb)
    color_score, color_fb, color_bd = analyze_color(image_rgb)
    sharpness_score, sharpness_fb, sharpness_bd = analyze_sharpness(image_rgb)
    composition_score, composition_fb, composition_bd = analyze_composition(image_rgb)
    tonal_score, tonal_fb, tonal_bd = analyze_tonal_range(image_rgb)
    atmosphere_score, atmosphere_fb, atmosphere_bd = analyze_atmosphere(image_rgb)
    style_score, style_fb, style_bd = analyze_style(image_rgb)

    return {
        "impact": (impact_score, impact_fb, impact_bd),
        "exposure": (exposure_score, exposure_fb, exposure_bd),
        "color": (color_score, color_fb, color_bd),
        "sharpness": (sharpness_score, sharpness_fb, sharpness_bd),
        "composition": (composition_score, composition_fb, composition_bd),
        "tonal": (tonal_score, tonal_fb, tonal_bd),
        "atmosphere": (atmosphere_score, atmosphere_fb, atmosphere_bd),
        "style": (style_score, style_fb, style_bd),
    }


def build_result(raw, weights):
    """Build the final result dict from raw analysis scores and weights."""
    overall = sum(raw[k][0] * weights[k] for k in weights)
    grade_label, grade_color, grade_desc = professional_grade(overall)

    if overall >= 85:
        summary = "这是一张具有专业水准的摄影作品。各维度表现均衡优异，具备参加摄影比赛的潜质。在后期处理上只需微调即可。"
    elif overall >= 70:
        summary = "这是一张质量不错的照片。在部分维度上表现出色，个别维度有明确的提升空间，建议关注下方的具体分析。"
    elif overall >= 55:
        summary = "照片具备基本素质，但多个维度需要针对性改进。下方详细分析将帮助您明确提升方向。"
    else:
        summary = "照片在技术层面存在较大提升空间。建议从曝光、对焦等基础技术开始系统练习，逐步提升各维度表现。"

    def to_native(bd):
        for b in bd:
            b["ok"] = bool(b["ok"])

    for _, fb, bd in raw.values():
        to_native(bd)

    score_map = {
        "exposure": raw["exposure"][0], "color": raw["color"][0],
        "sharpness": raw["sharpness"][0], "composition": raw["composition"][0],
        "atmosphere": raw["atmosphere"][0], "style": raw["style"][0],
    }
    recommendation = recommend_style(score_map)

    return {
        "overall": round(overall, 1),
        "overall_label": grade_label,
        "overall_color": grade_color,
        "overall_desc": grade_desc,
        "summary": summary,
        "recommended_style": recommendation["style_key"],
        "recommended_reason": recommendation["reason"],
        "dimensions": [
            {"name": "视觉冲击力", "key": "impact", "score": raw["impact"][0], "feedback": raw["impact"][1], "breakdown": raw["impact"][2], "weight": 17},
            {"name": "曝光与光影", "key": "exposure", "score": raw["exposure"][0], "feedback": raw["exposure"][1], "breakdown": raw["exposure"][2], "weight": 14},
            {"name": "色彩表现", "key": "color", "score": raw["color"][0], "feedback": raw["color"][1], "breakdown": raw["color"][2], "weight": 12},
            {"name": "清晰度与质感", "key": "sharpness", "score": raw["sharpness"][0], "feedback": raw["sharpness"][1], "breakdown": raw["sharpness"][2], "weight": 12},
            {"name": "构图设计", "key": "composition", "score": raw["composition"][0], "feedback": raw["composition"][1], "breakdown": raw["composition"][2], "weight": 14},
            {"name": "影调层次", "key": "tonal", "score": raw["tonal"][0], "feedback": raw["tonal"][1], "breakdown": raw["tonal"][2], "weight": 10},
            {"name": "氛围营造", "key": "atmosphere", "score": raw["atmosphere"][0], "feedback": raw["atmosphere"][1], "breakdown": raw["atmosphere"][2], "weight": 11},
            {"name": "风格表现", "key": "style", "score": raw["style"][0], "feedback": raw["style"][1], "breakdown": raw["style"][2], "weight": 10},
        ]
    }


def analyze_image(image_rgb):
    """Analyze an RGB image (numpy array) and return the full scoring result.
    This is the main entry point — wraps run_all_analyses + build_result."""
    weights = {
        "impact": 0.17, "exposure": 0.14, "color": 0.12, "sharpness": 0.12,
        "composition": 0.14, "tonal": 0.10, "atmosphere": 0.11, "style": 0.10,
    }
    raw = run_all_analyses(image_rgb)
    return build_result(raw, weights)


# ============================================================
# Histogram Generator
# ============================================================
def generate_histogram(image_rgb, save_path, width=320, height=200):
    """Generate an RGB histogram visualization from an RGB image array."""
    colors = [(220, 60, 60), (60, 180, 60), (60, 100, 220)]

    canvas = Image.new("RGBA", (width, height), (18, 20, 27, 255))
    draw = ImageDraw.Draw(canvas)

    for i in range(1, 5):
        y = int(height * (1 - i / 5))
        draw.line([(0, y), (width, y)], fill=(40, 44, 55, 255))
        draw.text((2, y - 8), str(i * 64), fill=(100, 105, 120), font_size=9)

    clip_zone = 15
    draw.rectangle([(0, 0), (clip_zone, height - 12)], fill=(239, 68, 68, 25))
    draw.rectangle([(width - clip_zone, 0), (width, height - 12)], fill=(239, 68, 68, 25))

    max_val = 0
    hist_data = []
    for ch in range(3):
        hist = cv2.calcHist([image_rgb], [ch], None, [256], [0, 256])
        hist_smooth = cv2.GaussianBlur(hist, (5, 1), 2).flatten()
        max_val = max(max_val, hist_smooth.max())
        hist_data.append(hist_smooth)

    scale = (height - 10) / max(max_val, 1)

    for ch in range(3):
        points = []
        for x in range(256):
            px = int(x / 255 * (width - 1))
            py = int(height - 12 - hist_data[ch][x] * scale)
            points.append((px, py))
        for i in range(1, len(points)):
            draw.line([points[i - 1], points[i]], fill=colors[ch], width=2)

        pts = points[:]
        pts.append((width - 1, height - 12))
        pts.append((0, height - 12))
        fill_color = (*colors[ch], 30)
        draw.polygon(pts, fill=fill_color)

    draw.text((2, height - 16), "0", fill=(100, 105, 120), font_size=9)
    draw.text((width - 24, height - 16), "255", fill=(100, 105, 120), font_size=9)

    for ch, label in enumerate(["R", "G", "B"]):
        x = 6 + ch * 24
        y = 4
        draw.rectangle([(x, y), (x + 12, y + 8)], fill=colors[ch])
        draw.text((x + 14, y - 2), label, fill=colors[ch], font_size=9)

    canvas.save(save_path, "PNG")
