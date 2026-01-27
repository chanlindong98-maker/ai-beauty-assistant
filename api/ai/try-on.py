"""
云试衣 / 耳饰试戴 API
POST /api/ai/try-on
"""
import os
import json
from http.server import BaseHTTPRequestHandler
from supabase import create_client
import google.generativeai as genai


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

            # 配置 Gemini
            genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
            
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

            # 调用 Gemini
            model = genai.GenerativeModel("gemini-2.0-flash-exp-image-generation")
            
            face_part = {"inline_data": {"mime_type": "image/jpeg", "data": face_data}}
            item_part = {"inline_data": {"mime_type": "image/jpeg", "data": item_data}}
            
            response = model.generate_content(
                contents=[face_part, item_part, prompt],
                generation_config={"response_mime_type": "image/png"}
            )

            # 提取图片
            result_image = None
            for part in response.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    result_image = f"data:image/png;base64,{part.inline_data.data}"
                    break

            if not result_image:
                self._send_json({"success": False, "message": "AI 未能生成图像"}, 500)
                return

            self._send_json({
                "success": True,
                "message": "生成成功",
                "image": result_image
            })

        except Exception as e:
            self._send_json({"success": False, "message": f"生成失败: {str(e)}"}, 500)

    def _send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
