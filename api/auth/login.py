import os
import json
from http.server import BaseHTTPRequestHandler

from api._utils import get_supabase_client

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body) if body else {}

            username = data.get("username", "")
            password = data.get("password", "")

            if not username or not password:
                self._send_json({"success": False, "message": "请输入用户名和密码哦 🍬"}, 400)
                return

            supabase = get_supabase_client()
            email = f"{username}@happy-beauty.local"

            # 登录
            auth_response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password,
            })

            if not auth_response.user:
                self._send_json({"success": False, "message": "用户名或密码不对哦，再试一次吧"}, 400)
                return

            user_id = auth_response.user.id
            
            # 获取用户资料
            profile_result = supabase.table("user_profiles").select("*").eq("id", user_id).single().execute()
            
            if not profile_result.data:
                self._send_json({"success": False, "message": "找不到您的魔法档案，请重新注册"}, 404)
                return
                
            profile = profile_result.data

            self._send_json({
                "success": True,
                "message": "欢迎回来！✨",
                "user": {
                    "nickname": profile["nickname"],
                    "device_id": profile["device_id"],
                    "credits": profile["credits"],
                    "isAdmin": profile.get("is_admin", False)
                },
                "access_token": auth_response.session.access_token if auth_response.session else None
            })

        except Exception as e:
            error_msg = str(e)
            status_code = 500
            user_msg = f"登录失败: {error_msg}"
            
            if "credentials" in error_msg.lower() or "invalid" in error_msg.lower():
                user_msg = "用户名或密码不对哦 🍭"
                status_code = 401
            elif "Supabase 环境变量" in error_msg:
                user_msg = "配置错误：请检查环境变量设置"
                
            self._send_json({"success": False, "message": user_msg, "detail": error_msg}, status_code)

    def _send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
