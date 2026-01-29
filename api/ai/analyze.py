"""
中医分析 / 面相分析 API
POST /api/ai/analyze
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
            analysis_type = data.get("analysis_type", "tongue")

            image_data = image.split(",")[1] if "," in image else image

            # 配置 Gemini
            genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
            
            # 构建提示词
            system_instruction = "你是一位拥有深厚底蕴的中医及传统文化学者。"
            
            if analysis_type == "tongue":
                system_instruction += "你拥有30年中医临床经验，擅长舌诊。"
                prompt = """请根据这张舌头照片进行中医分析：
                1. 观察舌质：包括颜色（淡红、红、绛、青紫等）、形态（胖大、瘦小、有无齿痕、裂纹）。
                2. 观察舌苔：包括颜色（白、黄、灰、黑）、厚薄、润燥。
                3. 综合判断：结合舌象推断可能的脏腑状况、气血阴阳平衡情况。
                4. 调理建议：给出饮食、作息、情志及简单穴位按摩的建议。
                请用中文分段回复。"""
            elif analysis_type == "face-analysis":
                system_instruction += "你拥有30年中医临床经验，擅长面诊。"
                prompt = """请根据这张人脸照片进行中医面诊分析：
                1. 面色分析：观察面色及其分布，对应五脏健康状况。
                2. 气色神态：分析眼神、皮肤光泽度所体现的精气神。
                3. 身体状况推断：基于中医理论推断身体状况。
                4. 调理建议：给出针对性的健康调理方案。
                请用中文分段回复。"""
            else:  # face-reading
                system_instruction += "你是一位精通中国传统相术的大师。"
                prompt = """请根据这张正面人脸照片进行面相分析：
                1. 性格分析：通过眼神、眉形等分析性格特征。
                2. 健康运势：分析健康素质。
                3. 财运事业：分析职业发展潜力。
                4. 命运总括：给出富有智慧的总结和建议。
                请用中文分段回复，需说明仅供参考。"""

            model = genai.GenerativeModel(
                "gemini-1.5-flash",
                system_instruction=system_instruction
            )
            
            image_part = {"inline_data": {"mime_type": "image/jpeg", "data": image_data}}
            
            response = model.generate_content(
                contents=[image_part, prompt],
                generation_config={"temperature": 0.7}
            )

            result_text = response.text or "AI 暂时无法给出分析结果"

            self._send_json({
                "success": True,
                "message": "分析完成",
                "text": result_text
            })

        except Exception as e:
            self._send_json({"success": False, "message": f"分析失败: {str(e)}"}, 500)

    def _send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
