"""
云试衣 / 耳饰试戴 API
POST /api/ai/try-on
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
    """验证token并获取用户信息"""
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
    """扣减魔法值"""
    if current_credits <= 0:
        return False
    supabase = get_supabase()
    supabase.table("user_profiles").update({"credits": current_credits - 1}).eq("id", user_id).execute()
    return True


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

            # 检查并扣减魔法值
            if not consume_credit(user["id"], user["credits"]):
                self._send_json({"success": False, "message": "魔法值不足"}, 402)
                return

            # 解析请求
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body) if body else {}

            face_image = data.get("face_image", "")
            item_image = data.get("item_image", "")
            try_on_type = data.get("try_on_type", "clothing")
            height = data.get("height", 165)
            body_type = data.get("body_type", "标准")

            # 提取 base64 数据
            face_data = face_image.split(",")[1] if "," in face_image else face_image
            item_data = item_image.split(",")[1] if "," in item_image else item_image

            # 配置 Gemini (优先从数据库读取 API 密钥)
            api_key = get_config("gemini_api_key")
            if not api_key:
                self._send_json({"success": False, "message": "未配置 Gemini API 密钥，请在管理后台设置"}, 500)
                return
            genai.configure(api_key=api_key, transport='rest')
            
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
                要求：将这款耳饰自然地戴在图中人的耳朵上。
                耳饰的细节（材质、反光、吊坠）应清晰可见。保持五官特征和肤色真实。
                输出必须是戴上耳饰后的效果图。"""

            # 调用 Gemini (使用支持图像生成的模型)
            model = genai.GenerativeModel("gemini-2.0-flash-exp-image-generation")
            print(f"[Try-On] Model: gemini-2.0-flash-exp-image-generation")
            
            # 极致放宽安全限制，防止误拦截
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
            face_part = {"inline_data": {"mime_type": "image/jpeg", "data": face_data}}
            item_part = {"inline_data": {"mime_type": "image/jpeg", "data": item_data}}
            
            # 关键配置：必须指定 response_modalities 包含 IMAGE 才能生成图像
            generation_config = {
                "response_modalities": ["TEXT", "IMAGE"]
            }
            
            response = model.generate_content(
                contents=[face_part, item_part, prompt],
                safety_settings=safety_settings,
                generation_config=generation_config
            )

            # 提取图片
            result_image = None
            debug_log = []
            v_time = "20260130-0035" # 数据解码修复版
            model_text = ""
            
            try:
                # 检查 parts 是否存在
                if not hasattr(response, 'parts') or not response.parts:
                    debug_log.append("EmptyParts")
                else:
                    for i, part in enumerate(response.parts):
                        if hasattr(part, "text") and part.text:
                            model_text = part.text
                            debug_log.append(f"T{i}")
                        if hasattr(part, "inline_data") and part.inline_data:
                            # 关键修复：处理 bytes 和 string 两种情况
                            img_data = part.inline_data.data
                            if isinstance(img_data, bytes):
                                import base64
                                img_data = base64.b64encode(img_data).decode('utf-8')
                            result_image = f"data:image/jpeg;base64,{img_data}"
                            debug_log.append(f"I{i}")
                            break
                
                if not result_image:
                    f_reason = "Unknown"
                    try: f_reason = str(response.candidates[0].finish_reason)
                    except: pass
                    
                    safety_info = []
                    try:
                        for rating in response.candidates[0].safety_ratings:
                            # 修正枚举比较
                            if hasattr(rating.probability, "name"):
                                p_name = rating.probability.name
                            else:
                                p_name = str(rating.probability)
                                
                            if p_name != "NEGLIGIBLE":
                                safety_info.append(f"{rating.category}:{p_name}")
                    except: pass
                    
                    err_msg = f"[{v_time}] AI 未能生成图像 | 原因: {f_reason} | 风险: {','.join(safety_info) if safety_info else 'None'}"
                    if model_text:
                        err_msg += f" | AI解释: {model_text[:50]}"
                        
                    self._send_json({
                        "success": False, 
                        "message": err_msg,
                        "debug": "/".join(debug_log)
                    }, 500)
                    return
            except Exception as pe:
                self._send_json({"success": False, "message": f"[{v_time}] 解析崩溃: {str(pe)}"}, 500)
                return

            self._send_json({
                "success": True,
                "message": "生成成功",
                "image": result_image
            })

        except Exception as e:
            msg = str(e)
            if "404" in msg:
                try:
                    models = [m.name for m in genai.list_models()]
                    msg += f" | Available models: {', '.join(models[:5])}"
                except: pass
            self._send_json({"success": False, "message": f"生成失败: {msg}"}, 500)

    def _send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
