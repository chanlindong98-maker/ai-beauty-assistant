"""
发型推荐 API
POST /api/ai/hairstyle
"""
import os
import json
import sys
import base64
from http.server import BaseHTTPRequestHandler
from supabase import create_client

# 导入共享工具模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _utils import get_config


def get_supabase():
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    return create_client(url, key)


def get_current_user(token: str):
    if not token:
        return None
    try:
        supabase = get_supabase()
        user_response = supabase.auth.get_user(token)
        if user_response and user_response.user:
            user_id = user_response.user.id
            profile = supabase.table("user_profiles").select("*").eq("id", user_id).single().execute()
            if profile.data:
                return {"id": user_id, **profile.data}
    except Exception:
        pass
    return None


def consume_credit(user_id: str, current_credits: int) -> bool:
    if current_credits <= 0:
        return False
    supabase = get_supabase()
    supabase.table("user_profiles").update({"credits": current_credits - 1}).eq("id", user_id).execute()
    return True


def extract_image(response) -> str:
    """从 Gemini 新版 SDK 响应中提取图像数据"""
    try:
        # 新版 SDK 响应格式：response.candidates[0].content.parts
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    img_data = part.inline_data.data
                    if isinstance(img_data, bytes):
                        img_data = base64.b64encode(img_data).decode('utf-8')
                    return img_data
    except Exception as e:
        print(f"[AI] Extract Image Error: {str(e)}")
    return ""


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_POST(self):
        try:
            # 验证用户
            auth_header = self.headers.get("Authorization", "")
            token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
            user = get_current_user(token)
            
            if not user:
                self._send_json({"success": False, "message": "未授权"}, 401)
                return

            if not consume_credit(user["id"], user["credits"]):
                self._send_json({"success": False, "message": "魔法值不足"}, 402)
                return

            # 解析请求
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body) if body else {}

            image = data.get("image", "")
            gender = data.get("gender", "女")
            age = data.get("age", 25)

            image_data = image.split(",")[1] if "," in image else image

            # 配置 Gemini (优先从数据库读取 API 密钥) - 使用新版 google-genai SDK
            api_key = get_config("gemini_api_key")
            if not api_key:
                self._send_json({"success": False, "message": "未配置 Gemini API 密钥，请在管理后台设置"}, 500)
                return
            
            from google import genai
            from google.genai import types
            
            client = genai.Client(api_key=api_key)
            print("[Hairstyle] Model Init")
            
            is_male = gender == "男"
            gender_term = "男士" if is_male else "女士"
            male_styles = "如：寸头、背头、纹理烫等"
            female_styles = "如：法式慵懒卷、波波头、大波浪等"
            style_guide = male_styles if is_male else female_styles

            # 分析脸型 (使用文本模型)
            analysis_prompt = f"""你是一位顶级发型设计师。请根据这张照片分析其脸型，并为这位【{age}岁】的【{gender_term}】推荐10种发型。
            发型款式应涵盖显著差异，{style_guide}。
            请按以下格式回复：
            1. 脸型分析
            2. 10种推荐发型列表
            3. 最优发型推荐及理由"""

            image_bytes = base64.b64decode(image_data)
            image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
            
            analysis_response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[image_part, analysis_prompt]
            )
            analysis_text = ""
            if analysis_response.candidates and analysis_response.candidates[0].content:
                for part in analysis_response.candidates[0].content.parts:
                    if hasattr(part, "text") and part.text:
                        analysis_text = part.text
                        break
            analysis_text = analysis_text or "未能生成分析"

            # 生成推荐发型图片 (使用支持图像生成的模型)
            rec_prompt = f"""生成一张高度写实的正面照片。
            必须使用原图中的人物面部，为这位{age}岁的人物换上一款完美的{gender_term}发型。
            背景简洁专业。"""
            
            # 关键配置：必须指定 response_modalities 包含 IMAGE 才能生成图像
            rec_response = client.models.generate_content(
                model="gemini-2.0-flash-exp-image-generation",
                contents=[image_part, rec_prompt],
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"]
                )
            )
            
            rec_image = extract_image(rec_response)
            
            # 生成发型目录
            cat_prompt = f"""生成一张{age}岁{gender_term}的发型参考画报。
            展示10种风格迥异的发型，整齐网格排版。"""
            
            cat_response = client.models.generate_content(
                model="gemini-2.0-flash-exp-image-generation",
                contents=[image_part, cat_prompt],
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"]
                )
            )
            
            cat_image = extract_image(cat_response)

            v_tag = "[20260130-V3]" # 2.0-flash 稳定版
            if not rec_image or not cat_image:
                f_reason = "Unknown"
                try: f_reason = str(rec_response.candidates[0].finish_reason)
                except: pass
                
                safety_msg = "None"
                try:
                    risks = [f"{r.category}:{r.probability}" for r in rec_response.candidates[0].safety_ratings if r.probability != "NEGLIGIBLE"]
                    if risks: safety_msg = ",".join(risks)
                except: pass

                self._send_json({
                    "success": False, 
                    "message": f"{v_tag} AI 未能生成发型图像 | 原因: {f_reason} | 风险: {safety_msg}",
                    "debug": "Extraction Failed"
                }, 500)
                return

            self._send_json({
                "success": True,
                "message": "推荐完成",
                "analysis": analysis_text,
                "recommended_image": f"data:image/jpeg;base64,{rec_image}",
                "catalog_image": f"data:image/jpeg;base64,{cat_image}"
            })
            print("[Hairstyle] Success")

        except Exception as e:
            msg = str(e)
            if "404" in msg:
                try:
                    models = [m.name for m in genai.list_models()]
                    msg += f" | Available models: {', '.join(models[:5])}"
                except: pass
            self._send_json({"success": False, "message": f"推荐失败: {msg}"}, 500)

    def _send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
