"""
发型推荐 API
POST /api/ai/hairstyle
"""
import os
import json
import sys
from http.server import BaseHTTPRequestHandler
from supabase import create_client
import google.generativeai as genai

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
    """从 Gemini 响应中提取图像数据，兼容 bytes 和 string 格式"""
    import base64
    try:
        for part in response.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                img_data = part.inline_data.data
                # 关键修复：处理 bytes 和 string 两种情况
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

            # 配置 Gemini (优先从数据库读取 API 密钥)
            api_key = get_config("gemini_api_key")
            if not api_key:
                self._send_json({"success": False, "message": "未配置 Gemini API 密钥，请在管理后台设置"}, 500)
                return
            genai.configure(api_key=api_key, transport='rest')
            print("[Hairstyle] Model Init")
            
            is_male = gender == "男"
            gender_term = "男士" if is_male else "女士"
            male_styles = "如：寸头、背头、纹理烫等"
            female_styles = "如：法式慵懒卷、波波头、大波浪等"
            style_guide = male_styles if is_male else female_styles

            # 分析脸型
            analysis_prompt = f"""你是一位顶级发型设计师。请根据这张照片分析其脸型，并为这位【{age}岁】的【{gender_term}】推荐10种发型。
            发型款式应涵盖显著差异，{style_guide}。
            请按以下格式回复：
            1. 脸型分析
            2. 10种推荐发型列表
            3. 最优发型推荐及理由"""

            text_model = genai.GenerativeModel("gemini-2.0-flash")
            image_part = {"inline_data": {"mime_type": "image/jpeg", "data": image_data}}
            
            analysis_response = text_model.generate_content(contents=[image_part, analysis_prompt])
            analysis_text = analysis_response.text or "未能生成分析"

            # 生成推荐发型图片 (使用支持图像生成的实验性模型)
            image_model = genai.GenerativeModel("gemini-2.0-flash-exp")
            
            rec_prompt = f"""生成一张高度写实的正面照片。
            必须使用原图中的人物面部，为这位{age}岁的人物换上一款完美的{gender_term}发型。
            背景简洁专业。"""
            
            # 放宽安全限制
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]

            rec_response = image_model.generate_content(
                contents=[image_part, rec_prompt],
                safety_settings=safety_settings
            )
            
            rec_image = extract_image(rec_response)
            
            # 生成发型目录
            cat_prompt = f"""生成一张{age}岁{gender_term}的发型参考画报。
            展示10种风格迥异的发型，整齐网格排版。"""
            
            cat_response = image_model.generate_content(
                contents=[image_part, cat_prompt],
                safety_settings=safety_settings
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
