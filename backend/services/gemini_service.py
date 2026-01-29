"""
Gemini AI 服务模块

封装所有与 Google Gemini API 的交互逻辑
"""
import google.generativeai as genai
import base64
import asyncio
from google.api_core import exceptions
from config import get_settings
from services.config_service import get_config


def get_gemini_client():
    """初始化并返回 Gemini 客户端"""
    # 优先从数据库动态配置获取 API Key
    api_key = get_config("gemini_api_key")
    genai.configure(api_key=api_key)
    return genai


async def call_gemini_with_retry(model, contents, generation_config=None, max_retries=3):
    """
    带重试机制的 Gemini API 调用
    支持指数退避处理 429 错误
    """
    for attempt in range(max_retries):
        try:
            if generation_config:
                return await asyncio.to_thread(
                    model.generate_content,
                    contents=contents,
                    generation_config=generation_config
                )
            else:
                return await asyncio.to_thread(
                    model.generate_content,
                    contents=contents
                )
        except exceptions.ResourceExhausted:
            if attempt == max_retries - 1:
                raise
            wait_time = (attempt + 1) * 2  # 2s, 4s
            print(f"Gemini API 429 频率受限，{wait_time}秒后重试第 {attempt + 1} 次...")
            await asyncio.sleep(wait_time)
        except Exception as e:
            # 其他错误不重试，直接抛出
            raise e


async def generate_try_on_image(
    face_image_base64: str,
    item_image_base64: str,
    height: int | None = None,
    body_type: str | None = None,
    try_on_type: str = "clothing"
) -> str:
    """
    生成试穿/试戴效果图
    
    Args:
        face_image_base64: 人物照片的 base64 编码
        item_image_base64: 服装/配饰照片的 base64 编码
        height: 身高（仅云试衣需要）
        body_type: 体型（仅云试衣需要）
        try_on_type: 类型，"clothing" 或 "accessory"
    
    Returns:
        生成图片的 base64 编码
    """
    get_gemini_client()
    
    # 构建图片部分
    face_part = {
        "inline_data": {
            "mime_type": "image/jpeg",
            "data": face_image_base64
        }
    }
    
    item_part = {
        "inline_data": {
            "mime_type": "image/jpeg",
            "data": item_image_base64
        }
    }
    
    # 构建提示词
    if try_on_type == "clothing":
        prompt = f"""生成一张高度写实的全身或半身照片。
        参考第一张图中的人脸和肤色，参考第二张图中的服装款式、颜色和纹理。
        要求：这个人身高约为 {height}cm，体型为 {body_type}。
        将这件衣服完美地穿在图中的人身上。保持背景简洁自然，光影和谐。
        输出必须是穿着该衣服的效果图。"""
    else:
        prompt = """生成一张高度写实的人脸近照。
        参考第一张图中的人脸，参考第二张图中的耳饰。
        要求：
        1. 将这款耳饰自然地戴在图中人的耳朵上。
        2. 如果第一张图是正面照，请确保【左右两只耳朵】都佩戴上这款耳饰，并保持对称自然。
        3. 耳饰的细节（材质、反光、吊坠）应清晰可见，与环境光影和谐。
        保持五官特征和肤色真实。输出必须是佩戴耳饰后的效果图。"""
    
    # 调用 Gemini API
    model = genai.GenerativeModel("gemini-2.5-flash-image")
    response = await call_gemini_with_retry(
        model=model,
        contents=[face_part, item_part, prompt]
    )
    
    # 提取图片
    for part in response.parts:
        if hasattr(part, "inline_data") and part.inline_data:
            data = part.inline_data.data
            if isinstance(data, bytes):
                return base64.b64encode(data).decode('utf-8')
            return str(data)
    
    raise ValueError("AI 未能生成有效的图像")


async def analyze_tcm(
    image_base64: str,
    analysis_type: str
) -> str:
    """
    中医/面相分析
    
    Args:
        image_base64: 图片的 base64 编码
        analysis_type: 分析类型 - "tongue", "face-analysis", "face-reading"
    
    Returns:
        分析结果文本
    """
    get_gemini_client()
    
    image_part = {
        "inline_data": {
            "mime_type": "image/jpeg",
            "data": image_base64
        }
    }
    
    # 根据类型构建系统指令和提示词
    system_instruction = "你是一位拥有深厚底蕴的中医及传统文化学者。"
    
    if analysis_type == "tongue":
        system_instruction += "你拥有30年中医临床经验，擅长舌诊。"
        prompt = """请根据这张舌头照片进行中医分析：
        1. 观察舌质：包括颜色（淡红、红、绛、青紫等）、形态（胖大、瘦小、有无齿痕、裂纹）。
        2. 观察舌苔：包括颜色（白、黄、灰、黑）、厚薄、润燥。
        3. 综合判断：结合舌象推断可能的脏腑状况、气血阴阳平衡情况（如气虚、湿热、阴虚等）。
        4. 调理建议：给出饮食、作息、情志及简单穴位按摩的建议。
        请用中文分段回复，语言通俗易懂但不失专业性。"""
    elif analysis_type == "face-analysis":
        system_instruction += "你拥有30年中医临床经验，擅长面诊。"
        prompt = """请根据这张人脸照片进行中医面诊分析：
        1. 面色分析：观察面色（如红润、萎黄、苍白、晦暗、青紫等）及其分布，对应五脏健康状况。
        2. 气色神态：分析眼神、皮肤光泽度所体现的精气神。
        3. 身体状况推断：基于中医"五色入五脏"理论，推断身体可能的虚实状况。
        4. 调理建议：给出针对性的健康调理方案，包括饮食调整和生活习惯建议。
        请用中文分段回复，语言温暖贴心。"""
    else:  # face-reading
        system_instruction += "你是一位精通中国传统相术（面相学）的大师。你的分析应结合五官（眼、耳、鼻、口、眉）及面部轮廓。"
        prompt = """请根据这张正面人脸照片，运用中国传统面相学理论进行详细分析：
        1. 性格分析：通过眼神、眉形、面部轮廓等分析其内在性格特征（如果敢、温婉、聪慧等）。
        2. 健康运势：通过人中、地阁、面色润泽度等分析其基本健康素质。
        3. 财运事业：通过准头（鼻翼）、天庭（额头）等分析其职业发展潜力及财富聚集能力。
        4. 命运总括：结合整体面部比例，对其人生大势给出一个富有哲学智慧的总结，并给出一些正向的人生指导建议。
        请用中文分段回复，语气庄重、富有智慧，且需明确说明分析仅供参考。"""
    
    model = genai.GenerativeModel(
        "gemini-2.0-flash",
        system_instruction=system_instruction
    )
    
    response = await call_gemini_with_retry(
        model=model,
        contents=[image_part, prompt],
        generation_config={"temperature": 0.7}
    )
    
    return response.text or "AI 暂时无法给出分析结果，请稍后再试。"


async def generate_hairstyle(
    image_base64: str,
    gender: str,
    age: int
) -> dict:
    """
    发型推荐
    
    Args:
        image_base64: 人物照片的 base64 编码
        gender: 性别 - "男" 或 "女"
        age: 年龄
    
    Returns:
        包含分析文本和生成图片的字典
    """
    get_gemini_client()
    
    image_part = {
        "inline_data": {
            "mime_type": "image/jpeg",
            "data": image_base64
        }
    }
    
    is_male = gender == "男"
    gender_term = "男士" if is_male else "女士"
    
    # 性别特定的发型风格
    male_styles = "如：寸头、背头、纹理烫、侧分Undercut、渣男锡纸烫、狼尾发型、中分碎发、美式渐变等"
    female_styles = "如：法式慵懒卷、波波头、初恋头、羊羔毛卷、大波浪长发、八字刘海中长发、锁骨发、公主切、齐耳短发等"
    style_guide = male_styles if is_male else female_styles
    
    # 1. 分析脸型并推荐发型
    analysis_prompt = f"""你是一位顶级发型设计师。请根据这张照片分析其脸型，并为这位【{age}岁】的【{gender_term}】推荐10种款式截然不同的发型。
    
    **严格质量要求**：
    1. **年龄与性别匹配**：推荐的发型必须高度契合【{age}岁】的年龄气质与【{gender_term}】的性别特征。
    2. **款式差异**：这10款发型必须涵盖显著差异，{style_guide}。
    3. **严禁重复**：10款发型在视觉和结构上必须完全不同。
    
    请按以下格式回复：
    1. 脸型分析：[分析结果]
    2. 10种针对{age}岁{gender_term}的独一无二推荐发型列表：[列表]
    3. 最优发型推荐：[发型名称] 及针对该年龄段的推荐理由。
    语言要专业且富有亲和力。"""
    
    analysis_model = genai.GenerativeModel("gemini-2.0-flash")
    analysis_response = await call_gemini_with_retry(
        model=analysis_model,
        contents=[image_part, analysis_prompt]
    )
    analysis_text = analysis_response.text or "未能生成分析。"
    
    # 2. 生成推荐发型图片
    rec_prompt = f"""生成一张高度写实的【正面视角】照片。
    **核心要求**：
    - 必须使用原图中的人物面部，确保五官特征与原图【完全一致】。
    - 为图中这位【{age}岁】的人物换上一款完美的【{gender_term}发型】（最优推荐款）。
    - 发型必须符合该年龄段的审美，如果是男士，严禁出现长发。
    - 背景简洁专业。"""
    
    image_model = genai.GenerativeModel("gemini-2.5-flash-image")
    rec_response = await call_gemini_with_retry(
        model=image_model,
        contents=[image_part, rec_prompt]
    )
    
    # 3. 生成发型目录图
    cat_prompt = f"""生成一张专业的【{age}岁】【{gender_term}】正面发型参考画报。
    **关键核心要求**：
    1. **视角统一**：全部为【正面照】。
    2. **人脸一致性**：人脸与原图【完全一致】。
    3. **年龄段契合度**：发型风格应适合【{age}岁】的人群。
    4. **多样性**：10种风格迥异的{gender_term}发型，绝不重复。
    5. **排版**：整齐网格排版。"""
    
    cat_response = await call_gemini_with_retry(
        model=image_model,
        contents=[image_part, cat_prompt]
    )
    
    def extract_image(response) -> str:
        """从响应中提取图片 base64"""
        for part in response.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                data = part.inline_data.data
                # 如果是 bytes，转换为 base64 字符串
                if isinstance(data, bytes):
                    return base64.b64encode(data).decode('utf-8')
                return str(data)
        return ""
    
    return {
        "analysis": analysis_text,
        "recommendedImage": extract_image(rec_response),
        "catalogImage": extract_image(cat_response)
    }
