"""
Entertainment Analysis: MBTI Personality, Audience Profile, and Photo Mood
基于照片视觉特征进行趣味人格、受众和情绪分析。
仅供娱乐，不具备心理学诊断意义。
"""

import cv2
import numpy as np

# ============================================================
# MBTI Photographer Personas
# 16 distinct profiles with creative descriptions
# ============================================================

MBTI_PROFILES = {
    "INTJ": {
        "name": "建筑师的凝视",
        "desc": "你的画面冷静、克制、结构分明。每一根引导线都经过精密计算，每一处留白都恰到好处。你像建筑师一样思考画面——理性、前瞻、自成体系。你不追逐流行，你定义秩序。",
        "match": "安塞尔·亚当斯 (Ansel Adams) — 区域曝光法的奠基者，同样痴迷于画面的精密控制",
        "style": "偏好几何构图、极简黑白、高反差影调",
    },
    "INTP": {
        "name": "实验者的实验室",
        "desc": "你对影像充满好奇心，喜欢打破常规探索未知。抽象、解构、重组——你乐于把照片当作思维实验的素材。你不太在意'应该怎么拍'，你只想看看'还可以怎么拍'。",
        "match": "曼·雷 (Man Ray) — 达达主义摄影先驱，用实验精神拓展摄影的边界",
        "style": "偏好抽象构图、多重曝光、实验性色彩处理",
    },
    "INFJ": {
        "name": "诗人的取景框",
        "desc": "你的镜头总能在平凡中捕捉诗意。你不记录世界的样子，你记录世界应有的情绪。安静、深邃、富有洞察力——你的每张照片都是一首无字的诗。",
        "match": "索尔·雷特 (Saul Leiter) — 用雨雾和反射描绘城市诗意的大师",
        "style": "偏好柔焦、反射、雨雾氛围、低饱和色调",
    },
    "INFP": {
        "name": "梦想家的日记",
        "desc": "你的画面是内心世界的投射。梦幻、温暖、带着淡淡的怀旧——你通过镜头讲述自己理解世界的方式。与其说你在拍照，不如说你在收集梦境。",
        "match": "蒂姆·沃克 (Tim Walker) — 用镜头营造超现实童话世界的造梦者",
        "style": "偏好柔和光线、梦幻色调、叙事性场景、留白",
    },
    "ISTJ": {
        "name": "档案员的底片",
        "desc": "你的镜头如实地记录着世界的纹理。扎实、可靠、一丝不苟——你相信最好的照片来自于耐心的等待和精准的执行。你不追求花哨，你追求永恒。",
        "match": "奥古斯特·桑德 (August Sander) — 用客观冷静的镜头为时代编目的记录者",
        "style": "偏好清晰锐利、纪实风格、正面构图、自然光",
    },
    "ISFJ": {
        "name": "守护者的温情",
        "desc": "你的镜头温柔而细腻，总是关注着生活中最质朴的美好。你不需要宏大的场景，阳光洒在桌上的光斑、奶奶织毛衣的手——这些细节就是你创作的源泉。",
        "match": "川内伦子 (Rinko Kawauchi) — 在日常细微处发现诗意与温暖的日本摄影师",
        "style": "偏好浅景深、温暖色调、日常碎片、微距视角",
    },
    "ISTP": {
        "name": "匠人的暗房",
        "desc": "你与器材之间有着本能的默契。技术参数对你来说不是负担而是玩具——你享受调试每一个变量带来的微妙变化。安静而专注，你的影像里藏着匠人的执着。",
        "match": "石内都 (Miyako Ishiuchi) — 对质感与时间痕迹有着偏执般敏感的记录者",
        "style": "偏好极致锐度、质感特写、黑白高反差、技术精准",
    },
    "ISFP": {
        "name": "艺术家的调色盘",
        "desc": "你不需要语言来解释自己的作品——画面本身就是全部。你的镜头感性、直觉、充满即兴的美感。拍什么不重要，拍成什么样才重要。你的色彩就是你的签名。",
        "match": "威廉·埃格尔斯顿 (William Eggleston) — 将日常之物赋予非凡色彩魔力的色彩大师",
        "style": "偏好大胆色彩、日常主题、感性构图、情绪先行",
    },
    "ENTJ": {
        "name": "导演的监视器",
        "desc": "你的画面充满掌控力和目的性。每一个元素都在为你要讲的故事服务——光线是演员，构图是舞台，色彩是台词。你天生就是影像的导演。",
        "match": "斯坦利·库布里克 (Stanley Kubrick) — 对画面每一寸都有精确要求的电影视觉大师",
        "style": "偏好对称构图、戏剧性光影、强烈视觉叙事、精确控制",
    },
    "ENTP": {
        "name": "革新者的快门",
        "desc": "你对规则说'不'。传统构图？打破它。常规后期？颠覆它。你的创作充满意外和机智，每一张照片都在挑战观众的既定认知。你不拍照，你发表观点。",
        "match": "辛迪·舍曼 (Cindy Sherman) — 不断颠覆身份与视觉叙事的观念摄影先驱",
        "style": "偏好观念摄影、非常规构图、戏谑元素、反传统",
    },
    "ENFJ": {
        "name": "讲故事的布道者",
        "desc": "你的镜头自带温度。你天生有连接人心的能力，画面里流动着对人性的理解和关怀。你拍照不是为了自己，是为了让观者感受到某种共鸣和力量。",
        "match": "史蒂夫·麦凯瑞 (Steve McCurry) — 用镜头连接世界人心的《国家地理》传奇",
        "style": "偏好人物肖像、人文纪实、富有感染力的瞬间、温暖光线",
    },
    "ENFP": {
        "name": "探险家的万花筒",
        "desc": "你的镜头永远在路上。好奇、热情、充满可能性——对你来说每一次按下快门都是一场微型冒险。你的画面色彩斑斓、角度新奇，像万花筒一样折射着世界的精彩。",
        "match": "薇薇安·迈尔 (Vivian Maier) — 带着相机走遍街头的秘密冒险家",
        "style": "偏好街头摄影、新奇角度、丰富色彩、意外瞬间",
    },
    "ESTJ": {
        "name": "主编的版面",
        "desc": "你的画面干净利落，主次分明，每一张都可以直接上版。你有天生的编辑思维——你知道什么该留、什么该舍。效率、品质、一致性，是你的三原则。",
        "match": "玛格丽特·伯克-怀特 (Margaret Bourke-White) — 首位女性战地记者，《生活》杂志首席摄影师",
        "style": "偏好新闻纪实、清晰叙事、结构分明、有说服力的画面",
    },
    "ESFJ": {
        "name": "分享者的相册",
        "desc": "你拍照是为了分享——分享快乐、分享感动、分享生活中值得被记住的瞬间。你的照片充满了烟火气和人情味，它们是记忆的容器，是朋友圈里最受欢迎的存在。",
        "match": "荒木经惟 (Nobuyoshi Araki) — 将生活与情感毫无保留注入影像的分享者",
        "style": "偏好生活记录、温暖人情、丰富场景、有故事的快照",
    },
    "ESTP": {
        "name": "猎人的捕捉器",
        "desc": "你的反应比快门更快。你善于在瞬息万变的场景中精准捕捉决定性瞬间。街头、运动、突发事件——你享受在混乱中找到秩序、在一秒内做出所有判断的快感。",
        "match": "布列松 (Henri Cartier-Bresson) — 决定性瞬间理论的提出者和践行者",
        "style": "偏好决定性瞬间、街头抓拍、动感画面、精准时机",
    },
    "ESFP": {
        "name": "表演者的舞台",
        "desc": "你天生就是视觉表演者。你不仅是在拍照，你是在创造一场视觉秀。色彩要最炫的、角度要最酷的、效果要最惊艳的——你不想让观众只是看看，你要让他们'哇'出声。",
        "match": "大卫·拉切贝尔 (David LaChapelle) — 将流行文化与超现实主义推向极致的视觉表演者",
        "style": "偏好极致色彩、戏剧化场景、流行文化元素、视觉冲击力优先",
    },
}


def analyze_mbti(scores, image_rgb):
    """Infer MBTI personality type from photo characteristics."""
    hsv = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)

    sat = hsv[:, :, 1]
    mean_sat = float(sat.mean())
    mean_val = float(hsv[:, :, 2].mean())

    # Edge density (Canny returns 0 and 255, divide by 255 to get pixel count)
    edges = cv2.Canny(gray, 50, 150)
    edge_pct = float((edges > 0).sum()) / gray.size * 100

    # Color diversity
    small = cv2.resize(image_rgb, (80, int(80 * image_rgb.shape[0] / image_rgb.shape[1])))
    unique_colors = len(np.unique(small.reshape(-1, 3), axis=0)) / 100

    # Get scores
    impact = scores.get("impact", 50)
    color_score = scores.get("color", 50)
    sharpness = scores.get("sharpness", 50)
    composition = scores.get("composition", 50)
    atmosphere = scores.get("atmosphere", 50)
    style_score = scores.get("style", 50)

    # === E/I: Extraversion vs Introversion ===
    # E needs: bright, busy, high impact, large color diversity
    # I needs: dim, calm, high atmosphere, subdued colors
    e_raw = (mean_val / 255 * 18 + mean_sat / 255 * 10 + edge_pct * 1.2
             + impact * 0.10 + unique_colors * 4 - atmosphere * 0.25 - style_score * 0.15)
    is_e = e_raw > 44

    # === S/N: Sensing vs Intuition ===
    # S: sharp, detailed, concrete → high sharpness, high edge density
    # N: atmospheric, dreamy, abstract → high atmosphere, high style, low sharpness
    s_raw = sharpness * 0.30 + edge_pct * 3 - atmosphere * 0.4 - style_score * 0.30
    is_s = s_raw > 35

    # === T/F: Thinking vs Feeling ===
    # T: precise, technical, structured → high composition, high sharpness, good exposure
    # F: emotional, warm → high atmosphere, high color, high impact
    t_raw = composition * 0.2 + sharpness * 0.25 - atmosphere * 0.35 - color_score * 0.15 - impact * 0.15
    is_t = t_raw > 0

    # === J/P: Judging vs Perceiving ===
    # J: planned, orderly, structured → high composition, clean lines, intentional
    # P: spontaneous, free → high unique_colors, organic layout, rule-breaking
    j_raw = composition * 0.4 - unique_colors * 6 - (100 - composition) * 0.15 + style_score * 0.1
    is_j = j_raw > 12

    # Assemble MBTI
    ei = "E" if is_e else "I"
    sn = "S" if is_s else "N"
    tf = "T" if is_t else "F"
    jp = "J" if is_j else "P"
    mbti = ei + sn + tf + jp

    # Dimension explanations
    dimensions = [
        {
            "letter": ei, "name": "外向/内向",
            "choice": "外向(E)" if is_e else "内向(I)",
            "pct": min(95, max(5, int(e_raw / 70 * 100))) if is_e else min(95, max(5, int((70 - e_raw) / 70 * 100))),
            "desc": "充满活力与能量，明亮的光线和张扬的色彩暗示着乐于与外界互动的创作者。" if is_e
            else "沉静内敛，在静谧中捕捉诗意，柔和的光影和克制的色调表明你更享受独处的观察与思考。",
        },
        {
            "letter": sn, "name": "实感/直觉",
            "choice": "实感(S)" if is_s else "直觉(N)",
            "pct": min(95, max(5, int(s_raw / 80 * 100))) if is_s else min(95, max(5, int((80 - s_raw) / 80 * 100))),
            "desc": "注重眼前的具体细节，扎实的质感和清晰的形态是你对现实的精准观察和忠实记录。" if is_s
            else "充满想象力和抽象美感，比起精确记录，你更在意氛围和感觉的传达，擅长从平凡中发现诗意。",
        },
        {
            "letter": tf, "name": "思考/情感",
            "choice": "思考(T)" if is_t else "情感(F)",
            "pct": min(95, max(5, int((t_raw + 40) / 80 * 100))) if is_t else min(95, max(5, int((40 - t_raw) / 80 * 100))),
            "desc": "严谨的技术思维，曝光精准、构图周密，你享受控制每个参数，用理性眼光审视每一帧。" if is_t
            else "镜头首先是感受的容器，比起技术参数，你更在意画面传递的情绪和故事。",
        },
        {
            "letter": jp, "name": "判断/感知",
            "choice": "判断(J)" if is_j else "感知(P)",
            "pct": min(95, max(5, int(j_raw / 60 * 100))) if is_j else min(95, max(5, int((60 - j_raw) / 60 * 100))),
            "desc": "构图讲究秩序与平衡，画面中能感受到精心的安排，你追求和谐与完整。" if is_j
            else "不拘泥于传统法则，更相信当下的直觉和即兴，画面的生动感和自由气息来自灵活开放的态度。",
        },
    ]

    profile = MBTI_PROFILES.get(mbti, MBTI_PROFILES["ISFP"])

    return {
        "mbti": mbti,
        "persona": profile["name"],
        "persona_desc": profile["desc"],
        "match_photographer": profile["match"],
        "style_preference": profile["style"],
        "dimensions": dimensions,
        "summary": f"你的摄影人格是 {mbti}「{profile['name']}」。{profile['desc'][:80]}...",
    }


# ============================================================
# Audience Profiles — 10 distinct categories
# ============================================================

AUDIENCE_PROFILES = [
    {
        "id": "art_gallery",
        "category": "画廊级艺术品",
        "age_range": "25–45岁",
        "gender_leaning": "男女均衡",
        "traits": "审美成熟、注重品质、有独立艺术判断",
        "interests": ["当代艺术", "画册收藏", "建筑师事务所", "独立出版物", "设计买手店"],
        "platforms": ["Instagram艺术社区", "小红书设计号", "Pinterest"],
        "use_case": "装裱成限量版画挂在家中空白的墙面上",
        "desc": "具备较高的艺术鉴赏力，会被精妙的构图和独特的个人风格所打动。他们愿意为好的视觉作品付费。",
    },
    {
        "id": "social_media",
        "category": "社交爆款",
        "age_range": "16–28岁",
        "gender_leaning": "偏女性",
        "traits": "热爱生活、追求美感、社交活跃、乐于分享",
        "interests": ["Instagram美学", "穿搭OOTD", "探店打卡", "手机摄影", "Vlog创作"],
        "platforms": ["小红书", "Instagram", "抖音"],
        "use_case": "第一时间设为手机壁纸并发到朋友圈配一句心情语录",
        "desc": "对高颜值画面毫无抵抗力，看到好看的照片就像看到好看的衣服一样兴奋。他们是你照片最积极的点赞和转发者。",
    },
    {
        "id": "mood_seeker",
        "category": "情绪自留地",
        "age_range": "20–35岁",
        "gender_leaning": "偏女性",
        "traits": "感性、内省、注重情绪体验、偏爱小众",
        "interests": ["独立音乐", "深夜电台", "文艺电影", "手写书信", "雨天散步"],
        "platforms": ["网易云音乐评论区", "豆瓣", "即刻"],
        "use_case": "在深夜情绪翻涌时翻出来反复观看，从中找到某种难以言说的共鸣",
        "desc": "他们不追求视觉冲击，而是追求情绪的共振。一张氛围感强的照片对他们来说胜过千言万语。",
    },
    {
        "id": "dark_aesthetic",
        "category": "暗调信徒",
        "age_range": "20–35岁",
        "gender_leaning": "偏男性",
        "traits": "沉稳内敛、偏爱小众、追求质感与深度",
        "interests": ["黑胶唱片", "独立电影", "极简设计", "古着文化", "威士忌品鉴"],
        "platforms": ["VSCO", "Flickr", "Tumblr"],
        "use_case": "收藏进个人的'暗调灵感'Pinterest画板，作为自己的创作参考",
        "desc": "对低调而有深度的表达情有独钟。他们对画面中的暗部层次有着近乎偏执的欣赏。",
    },
    {
        "id": "adventure",
        "category": "冒险家档案",
        "age_range": "18–30岁",
        "gender_leaning": "偏男性",
        "traits": "充满活力、敢于尝试、拥抱未知",
        "interests": ["户外探险", "极限运动", "公路旅行", "无人机航拍", "野营"],
        "platforms": ["B站户外区", "小红书旅行", "500px"],
        "use_case": "保存进'下次一定要去'的旅行收藏夹，成为计划下一次冒险的灵感来源",
        "desc": "看到震撼的风景照就走不动路。他们追求视觉冲击和宏大叙事，热爱用镜头记录每一次冒险。",
    },
    {
        "id": "nostalgia",
        "category": "怀旧收藏家",
        "age_range": "22–38岁",
        "gender_leaning": "男女均衡",
        "traits": "念旧、细腻、珍视回忆、有文艺情怀",
        "interests": ["胶片相机", "旧物收藏", "手账日记", "慢生活", "老城漫步"],
        "platforms": ["豆瓣", "小宇宙播客", "NOMO相机"],
        "use_case": "冲印成6寸照片夹在手账本里，旁边用钢笔写上拍照时的心情",
        "desc": "每一张照片对他们来说都是一段时光的切片。他们不追求完美，追求真实和有温度的记忆。",
    },
    {
        "id": "tech_geek",
        "category": "器材党的屏保",
        "age_range": "22–40岁",
        "gender_leaning": "偏男性",
        "traits": "技术控、细节偏执、理性思维、追求极致",
        "interests": ["相机评测", "镜头数据", "后期技术", "打印输出", "色彩管理"],
        "platforms": ["B站测评区", "CHIPHELL论坛", "DPReview"],
        "use_case": "放大到100%像素级别仔细研究焦内锐度和焦外虚化，然后默默收藏为自己的技术标杆",
        "desc": "他们对技术参数如数家珍。一张曝光精准、焦点锐利、细节丰富的照片能让他们心生敬意。",
    },
    {
        "id": "healing",
        "category": "治愈避难所",
        "age_range": "18–35岁",
        "gender_leaning": "偏女性",
        "traits": "温柔、内向、需要被治愈、享受独处",
        "interests": ["治愈系插画", "猫咪日常", "植物养护", "冥想", "温暖绘本"],
        "platforms": ["小红书治愈区", "Pinterest", "mood board"],
        "use_case": "在压力大的时候翻出来看一看，让画面里的安静和美好缓缓抚平心里的焦虑",
        "desc": "他们在寻找能让内心平静下来的画面。柔和的色调、温暖的阳光、安静的氛围，是他们最好的心灵药剂。",
    },
    {
        "id": "street_culture",
        "category": "街头潮流志",
        "age_range": "15–25岁",
        "gender_leaning": "偏男性",
        "traits": "个性张扬、敢于表达、追逐潮流前沿",
        "interests": ["街头文化", "潮流品牌", "说唱音乐", "滑板运动", "涂鸦艺术"],
        "platforms": ["得物", "小红书潮流", "抖音"],
        "use_case": "截取最有态度的局部设为头像，宣告自己的审美立场",
        "desc": "他们不满足于平庸的视觉体验，追求有态度、有性格的画面。一张酷的照片对他们来说是身份的标识。",
    },
    {
        "id": "nature_lover",
        "category": "自然观察笔记",
        "age_range": "25–50岁",
        "gender_leaning": "男女均衡",
        "traits": "沉稳、热爱自然、有耐心、懂得欣赏细节",
        "interests": ["鸟类观察", "植物图鉴", "国家地理", "徒步登山", "生态保护"],
        "platforms": ["国家地理APP", "iNaturalist", "微博鸟类摄影圈"],
        "use_case": "仔细研究画面中的每一个自然细节，从羽毛纹理到叶脉走向，沉浸在自然的精妙之中",
        "desc": "他们欣赏自然之美，对光影、纹理和生命形态有着天然的敏感。一张好的自然照片能让他们感受到与地球的深层连接。",
    },
]


def analyze_audience(scores, image_rgb, mbti_result):
    """Determine which audience segment would most appreciate this photo."""
    impact = scores.get("impact", 50)
    atmosphere = scores.get("atmosphere", 50)
    color_score = scores.get("color", 50)
    style_score = scores.get("style", 50)
    composition = scores.get("composition", 50)
    sharpness = scores.get("sharpness", 50)

    hsv = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2HSV)
    mean_val = float(hsv[:, :, 2].mean())

    # Score each audience profile against the photo
    scored = []

    for profile in AUDIENCE_PROFILES:
        pid = profile["id"]
        match = 0

        if pid == "art_gallery":
            match = composition * 0.4 + style_score * 0.4 + sharpness * 0.2
        elif pid == "social_media":
            match = color_score * 0.35 + impact * 0.35 + (mean_val / 255 * 15) + (100 - atmosphere) * 0.05
        elif pid == "mood_seeker":
            match = atmosphere * 0.55 + style_score * 0.25 + (100 - impact) * 0.2 + (100 - mean_val / 255 * 20)
        elif pid == "dark_aesthetic":
            match = (255 - mean_val) / 255 * 45 + style_score * 0.3 + atmosphere * 0.25
        elif pid == "adventure":
            match = impact * 0.55 + (mean_val / 255 * 15) + sharpness * 0.3
        elif pid == "nostalgia":
            match = atmosphere * 0.45 + style_score * 0.35 + (100 - sharpness) * 0.2
        elif pid == "tech_geek":
            match = sharpness * 0.45 + composition * 0.35 + (100 - atmosphere) * 0.2
        elif pid == "healing":
            match = atmosphere * 0.4 + (100 - impact) * 0.3 + color_score * 0.15 + (mean_val / 255 * 15)
        elif pid == "street_culture":
            match = impact * 0.45 + (100 - composition) * 0.3 + color_score * 0.25
        elif pid == "nature_lover":
            match = atmosphere * 0.4 + sharpness * 0.3 + (100 - impact) * 0.15 + composition * 0.15

        scored.append((profile, match))

    scored.sort(key=lambda x: x[1], reverse=True)

    # Return top 2 matches
    primary = scored[0][0]
    secondary = scored[1][0]

    return {
        "category": primary["category"],
        "age_range": primary["age_range"],
        "gender_leaning": primary["gender_leaning"],
        "traits": primary["traits"],
        "interests": primary["interests"],
        "platforms": primary["platforms"],
        "use_case": primary["use_case"],
        "description": primary["desc"],
        "also_matches": secondary["category"],
        "summary": f"{primary['age_range']}的{primary['gender_leaning']}群体，{primary['traits']}。{primary['desc']}",
    }


# ============================================================
# Photo Mood / Emotion Analysis
# ============================================================

MOOD_PALETTES = [
    {
        "mood": "宁静治愈",
        "emoji": "🌿",
        "colors": "柔和的蓝绿色调主导，低对比度",
        "phrase": "适合在一个安静的午后，配一杯热茶慢慢看",
        "music": "指弹吉他、氛围电子、Lo-Fi Beats",
        "trigger": lambda s, v: s["atmosphere"] > 60 and s["impact"] < 65 and v["mean_val"] > 100,
    },
    {
        "mood": "热烈奔放",
        "emoji": "🔥",
        "colors": "高饱和暖色系，强烈的视觉张力",
        "phrase": "像夏天的第一口冰汽水，充满能量和生命力",
        "music": "拉丁流行、放克、摇滚",
        "trigger": lambda s, v: s["impact"] > 65 and s["color"] > 70 and v["mean_val"] > 130,
    },
    {
        "mood": "忧郁深沉",
        "emoji": "🌧️",
        "colors": "暗调、低饱和、冷色倾向",
        "phrase": "像雨天的爵士酒吧，有一种说不清的吸引力",
        "music": "爵士、后摇、Trip-Hop",
        "trigger": lambda s, v: v["mean_val"] < 100 and s["atmosphere"] > 55 and s["color"] < 60,
    },
    {
        "mood": "神秘梦幻",
        "emoji": "✨",
        "colors": "柔焦、雾化效果、非现实色彩",
        "phrase": "仿佛从梦中截取的一帧，让人分不清是真实还是幻想",
        "music": "梦幻流行、合成器浪潮、环境音乐",
        "trigger": lambda s, v: s["style"] > 55 and s["atmosphere"] > 65 and s["sharpness"] < 60,
    },
    {
        "mood": "纯真清新",
        "emoji": "🌸",
        "colors": "高明度、低饱和、柔和粉彩色调",
        "phrase": "像春天早晨透过窗帘的第一缕阳光，温柔而充满希望",
        "music": "独立民谣、原声吉他、钢琴独奏",
        "trigger": lambda s, v: v["mean_val"] > 160 and s["color"] > 55 and s["impact"] < 60,
    },
    {
        "mood": "冷峻克制",
        "emoji": "🏛️",
        "colors": "灰度倾向、结构分明、高反差",
        "phrase": "精确得像一张建筑图纸，理性而充满力量感",
        "music": "极简古典、工业电子、前卫爵士",
        "trigger": lambda s, v: s["composition"] > 65 and s["sharpness"] > 70 and s["atmosphere"] < 55,
    },
    {
        "mood": "温暖怀旧",
        "emoji": "📷",
        "colors": "暖色调、褪色感、胶片颗粒质感",
        "phrase": "翻开旧相册的感觉——模糊的细节里藏着最清晰的回忆",
        "music": "City Pop、复古灵魂乐、磁带Lo-Fi",
        "trigger": lambda s, v: s["style"] > 50 and v["warmth"] > 10 and s["sharpness"] < 70,
    },
    {
        "mood": "浪漫柔情",
        "emoji": "🌅",
        "colors": "金色时刻光线、柔和的橙粉色调",
        "phrase": "适合在黄昏时分与喜欢的人一起看着，什么话都不用说",
        "music": "R&B、轻柔流行、弦乐四重奏",
        "trigger": lambda s, v: v["golden_hour"] and s["atmosphere"] > 50 and s["color"] > 55,
    },
    {
        "mood": "孤独空旷",
        "emoji": "🏜️",
        "colors": "大面积留白、极简构图、低饱和度",
        "phrase": "一个人站在广阔天地间——不是寂寞，是自由的呼吸",
        "music": "后摇、氛围音乐、极简钢琴",
        "trigger": lambda s, v: s["composition"] < 50 and s["impact"] < 55 and v["mean_val"] > 90,
    },
    {
        "mood": "充满故事感",
        "emoji": "🎬",
        "colors": "电影感调色、戏剧性光影、场景感强",
        "phrase": "每一帧都像电影截图，让人想按下播放键看接下来发生什么",
        "music": "电影原声、管弦乐、叙事民谣",
        "trigger": lambda s, v: s["atmosphere"] > 55 and s["style"] > 50 and s["composition"] > 55,
    },
]


def analyze_mood(scores, image_rgb):
    """Determine the dominant emotional mood of the photo."""
    hsv = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)
    lab = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2LAB)

    mean_val = float(hsv[:, :, 2].mean())

    # Warmth: LAB B channel
    warmth = float(lab[:, :, 2].mean() - 128)

    # Detect golden hour: warm + medium-high brightness
    golden_hour = warmth > 15 and 100 < mean_val < 200

    context = {
        "mean_val": mean_val,
        "warmth": warmth,
        "golden_hour": golden_hour,
    }

    best = None
    best_score = -1
    for mood in MOOD_PALETTES:
        if mood["trigger"](scores, context):
            score = sum([
                abs(scores.get("atmosphere", 50) - 50),
                abs(scores.get("color", 50) - 50),
                abs(scores.get("impact", 50) - 50),
            ])
            if score > best_score:
                best_score = score
                best = mood

    if best is None:
        best = MOOD_PALETTES[7]  # Default to 浪漫柔情

    return {
        "mood": best["mood"],
        "emoji": best["emoji"],
        "colors": best["colors"],
        "phrase": best["phrase"],
        "music": best["music"],
        "summary": f"{best['emoji']} 这张照片的情绪基调是「{best['mood']}」。{best['phrase']}。适合搭配的音乐：{best['music']}。",
    }
