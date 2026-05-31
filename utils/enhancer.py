import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


def enhance_natural(image_rgb):
    """Natural enhancement: auto white balance, subtle exposure correction, gentle sharpening."""
    img = image_rgb.copy()

    # White balance (Gray World assumption)
    lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    a_mean = a.astype(np.float32).mean()
    b_mean = b.astype(np.float32).mean()
    a_corr = np.clip(a.astype(np.float32) + (128 - a_mean) * 0.4, 0, 255).astype(np.uint8)
    b_corr = np.clip(b.astype(np.float32) + (128 - b_mean) * 0.4, 0, 255).astype(np.uint8)
    lab_corr = cv2.merge([l, a_corr, b_corr])
    img = cv2.cvtColor(lab_corr, cv2.COLOR_LAB2RGB)

    # Exposure: adjust gamma for brightness
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    mean_brightness = gray.mean()
    if mean_brightness < 90:
        gamma = 1.25
    elif mean_brightness > 170:
        gamma = 0.85
    else:
        gamma = 1.0
    if gamma != 1.0:
        inv_gamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype(np.uint8)
        img = cv2.LUT(img, table)

    # Convert to PIL for further processing
    pil_img = Image.fromarray(img)

    # Subtle saturation boost
    enhancer = ImageEnhance.Color(pil_img)
    pil_img = enhancer.enhance(1.1)

    # Gentle contrast
    enhancer = ImageEnhance.Contrast(pil_img)
    pil_img = enhancer.enhance(1.08)

    # Sharpening
    pil_img = pil_img.filter(ImageFilter.UnsharpMask(radius=1, percent=40, threshold=3))

    return np.array(pil_img)


def enhance_vivid(image_rgb):
    """Vivid enhancement: boosted saturation, contrast, clarity for a punchy look."""
    img = image_rgb.copy()

    # Auto tone adjustment
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    p2, p98 = np.percentile(gray, (2, 98))
    if p2 < p98:
        img = np.clip((img.astype(float) - p2) / (p98 - p2) * 255, 0, 255).astype(np.uint8)

    pil_img = Image.fromarray(img)

    # Strong saturation
    enhancer = ImageEnhance.Color(pil_img)
    pil_img = enhancer.enhance(1.35)

    # Strong contrast
    enhancer = ImageEnhance.Contrast(pil_img)
    pil_img = enhancer.enhance(1.25)

    # Brightness adjust
    enhancer = ImageEnhance.Brightness(pil_img)
    pil_img = enhancer.enhance(1.05)

    # Clarity via sharpening
    pil_img = pil_img.filter(ImageFilter.UnsharpMask(radius=2, percent=80, threshold=2))

    # Slight warmth
    result = np.array(pil_img).astype(float)
    result[:, :, 0] = np.clip(result[:, :, 0] * 1.04, 0, 255)  # Red channel
    result[:, :, 1] = np.clip(result[:, :, 1] * 1.02, 0, 255)  # Green
    result[:, :, 2] = np.clip(result[:, :, 2] * 0.96, 0, 255)  # Blue
    result = result.astype(np.uint8)

    return result


def enhance_cinematic(image_rgb):
    """Cinematic enhancement: teal/orange color grading, vignette, film grain, soft highlight rolloff."""
    img = image_rgb.copy()

    pil_img = Image.fromarray(img)
    enhancer = ImageEnhance.Contrast(pil_img)
    pil_img = enhancer.enhance(1.15)
    result = np.array(pil_img).astype(np.float32)

    # Teal & Orange color grading
    r, g, b = result[:, :, 0].copy(), result[:, :, 1].copy(), result[:, :, 2].copy()

    # Boost orange in highlights (warm skin tones)
    highlight_mask = (r + g + b) / 3 > 128
    result[:, :, 0][highlight_mask] = np.clip(r[highlight_mask] * 1.10, 0, 255)
    result[:, :, 1][highlight_mask] = np.clip(g[highlight_mask] * 1.03, 0, 255)
    result[:, :, 2][highlight_mask] = np.clip(b[highlight_mask] * 0.85, 0, 255)

    # Boost teal in shadows (cool dark tones)
    shadow_mask = (r + g + b) / 3 <= 128
    result[:, :, 0][shadow_mask] = np.clip(r[shadow_mask] * 0.85, 0, 255)
    result[:, :, 1][shadow_mask] = np.clip(g[shadow_mask] * 1.05, 0, 255)
    result[:, :, 2][shadow_mask] = np.clip(b[shadow_mask] * 1.10, 0, 255)

    result = result.astype(np.uint8)

    # Vignette
    h, w = result.shape[:2]
    y, x = np.ogrid[:h, :w]
    cx, cy = w // 2, h // 2
    dist = np.sqrt(((x - cx) / (w / 2)) ** 2 + ((y - cy) / (h / 2)) ** 2)
    vignette = np.clip(1 - dist * 0.35, 0.3, 1.0)
    vignette = np.dstack([vignette, vignette, vignette])
    result = (result * vignette).astype(np.uint8)

    # Subtle film grain
    noise = np.random.normal(0, 4, result.shape).astype(np.int16)
    result = np.clip(result.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    # Soft blur overlay for highlight rolloff
    pil_result = Image.fromarray(result)
    pil_result = pil_result.filter(ImageFilter.UnsharpMask(radius=1, percent=60, threshold=4))
    final = np.array(pil_result)

    return final


def enhance_blackwhite(image_rgb):
    """Black & White: grayscale with contrast curves, strong sharpening, subtle warm tone."""
    gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)

    # Channel-weighted grayscale for richer B&W
    b, g, r = image_rgb[:, :, 0].astype(float), image_rgb[:, :, 1].astype(float), image_rgb[:, :, 2].astype(float)
    gray_weighted = (0.21 * r + 0.72 * g + 0.07 * b).astype(np.uint8)

    # Contrast stretch
    p2, p98 = np.percentile(gray_weighted, (2, 98))
    if p2 < p98:
        gray_weighted = np.clip((gray_weighted.astype(float) - p2) / (p98 - p2) * 255, 0, 255).astype(np.uint8)

    # S-curve for film-like contrast
    mid = 128
    gray_float = gray_weighted.astype(float) / 255.0
    gray_curved = np.where(gray_float <= 0.5,
                           gray_float * 1.2,
                           1 - (1 - gray_float) * 1.15)
    gray_curved = np.clip(gray_curved, 0, 1)
    result_gray = (gray_curved * 255).astype(np.uint8)

    # Convert back to RGB with subtle sepia warmth
    result = cv2.cvtColor(result_gray, cv2.COLOR_GRAY2RGB).astype(float)
    result[:, :, 0] = np.clip(result[:, :, 0] * 1.02, 0, 255)
    result[:, :, 1] = np.clip(result[:, :, 1] * 0.98, 0, 255)
    result[:, :, 2] = np.clip(result[:, :, 2] * 0.90, 0, 255)
    result = result.astype(np.uint8)

    # Light film grain
    noise = np.random.normal(0, 3, result.shape).astype(np.int16)
    result = np.clip(result.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    return result


def enhance_japan(image_rgb):
    """Japanese Fresh: slightly overexposed, desaturated, cool-green tint, lifted blacks."""
    pil_img = Image.fromarray(image_rgb)

    # Slight overexposure
    enhancer = ImageEnhance.Brightness(pil_img)
    pil_img = enhancer.enhance(1.12)

    # Desaturate
    enhancer = ImageEnhance.Color(pil_img)
    pil_img = enhancer.enhance(0.7)

    # Low contrast — lifted blacks
    enhancer = ImageEnhance.Contrast(pil_img)
    pil_img = enhancer.enhance(0.85)

    result = np.array(pil_img).astype(float)

    # Cool tint: boost blue, slight green
    result[:, :, 1] = np.clip(result[:, :, 1] * 1.03, 0, 255)
    result[:, :, 2] = np.clip(result[:, :, 2] * 1.08, 0, 255)
    result[:, :, 0] = np.clip(result[:, :, 0] * 0.95, 0, 255)

    # Lifted blacks — add base level of gray to shadows
    gray = result.mean(axis=2)
    shadow_mask = gray < 80
    result[shadow_mask] = np.clip(result[shadow_mask] + 25, 0, 255)

    result = result.astype(np.uint8)

    # Soft blur overlay
    pil_result = Image.fromarray(result)
    soft = pil_result.filter(ImageFilter.GaussianBlur(radius=3))
    soft_arr = np.array(soft).astype(float)
    blend = (result.astype(float) * 0.88 + soft_arr * 0.12).astype(np.uint8)

    return blend


def enhance_retro(image_rgb):
    """Retro Film: warm tones, raised blacks, slight magenta cast, heavy grain, soft glow."""
    pil_img = Image.fromarray(image_rgb)

    # Slight fade / raised blacks
    enhancer = ImageEnhance.Contrast(pil_img)
    pil_img = enhancer.enhance(0.9)
    enhancer = ImageEnhance.Brightness(pil_img)
    pil_img = enhancer.enhance(1.06)

    result = np.array(pil_img).astype(float)

    # Warm tone: boost red, reduce blue
    result[:, :, 0] = np.clip(result[:, :, 0] * 1.10, 0, 255)
    result[:, :, 1] = np.clip(result[:, :, 1] * 1.02, 0, 255)
    result[:, :, 2] = np.clip(result[:, :, 2] * 0.82, 0, 255)

    # Magenta tone in highlights
    r, g, b = result[:, :, 0], result[:, :, 1], result[:, :, 2]
    highlight = (r + g + b) / 3 > 140
    result[:, :, 0][highlight] = np.clip(r[highlight] * 1.04, 0, 255)
    result[:, :, 2][highlight] = np.clip(b[highlight] * 1.05, 0, 255)

    # Vignette
    h, w = result.shape[:2]
    y, x = np.ogrid[:h, :w]
    cx, cy = w // 2, h // 2
    dist = np.sqrt(((x - cx) / (w / 2)) ** 2 + ((y - cy) / (h / 2)) ** 2)
    vignette = np.clip(1 - dist * 0.3, 0.2, 1.0)
    vignette = np.dstack([vignette, vignette, vignette])
    result = (result * vignette).astype(float)

    # Heavy film grain
    noise = np.random.normal(0, 8, result.shape)
    result = np.clip(result + noise, 0, 255).astype(np.uint8)

    # Soft glow
    pil_result = Image.fromarray(result)
    soft = pil_result.filter(ImageFilter.GaussianBlur(radius=5))
    soft_arr = np.array(soft).astype(float)
    final = (result.astype(float) * 0.82 + soft_arr * 0.18).astype(np.uint8)

    return final


STYLES = {
    "natural": {
        "name": "自然",
        "description": "自动白平衡 + 微妙曝光修正 + 温和锐化。适合绝大多数照片的快速美化。",
        "fn": enhance_natural,
    },
    "vivid": {
        "name": "鲜明",
        "description": "增强饱和度和对比度，让色彩更鲜艳动人。适合风光、美食和旅行照片。",
        "fn": enhance_vivid,
    },
    "cinematic": {
        "name": "电影感",
        "description": "青橙色调 + 暗角 + 胶片颗粒。营造电影画面氛围。适合街拍和人像。",
        "fn": enhance_cinematic,
    },
    "blackwhite": {
        "name": "黑白",
        "description": "经典黑白转换 + 胶片颗粒 + 暖调暗部。突出光影和结构。适合人文纪实和建筑。",
        "fn": enhance_blackwhite,
    },
    "japan": {
        "name": "日系清新",
        "description": "轻过曝 + 低饱和 + 冷色调 + 柔焦。清新通透感。适合人像、日常和旅行记录。",
        "fn": enhance_japan,
    },
    "retro": {
        "name": "复古胶片",
        "description": "暖色调 + 褪色暗部 + 胶片颗粒 + 柔光。怀旧氛围。适合生活随拍和情绪表达。",
        "fn": enhance_retro,
    },
}


def apply_style(image_path, style_key, output_path, intensity=1.0):
    """Apply an enhancement style to an image and save the result.
    intensity: 0.0 = original, 0.5 = half strength, 1.0 = full effect.
    """
    if style_key not in STYLES:
        raise ValueError(f"未知风格: {style_key}。可用风格: {list(STYLES.keys())}")

    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"无法读取图片: {image_path}")

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    enhanced = STYLES[style_key]["fn"](img_rgb)

    # Blend with original based on intensity
    if intensity < 1.0:
        intensity = max(0.1, min(1.0, intensity))
        enhanced = (img_rgb.astype(float) * (1 - intensity) + enhanced.astype(float) * intensity).astype(np.uint8)

    cv2.imwrite(output_path, cv2.cvtColor(enhanced, cv2.COLOR_RGB2BGR))
    return STYLES[style_key]


def get_styles():
    """Return available enhancement styles."""
    return [
        {"key": key, "name": info["name"], "description": info["description"]}
        for key, info in STYLES.items()
    ]
