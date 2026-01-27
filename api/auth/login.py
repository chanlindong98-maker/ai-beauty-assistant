"""
用户登录 API
POST /api/auth/login
"""
import os
import json
from http.server import BaseHTTPRequestHandler
from supabase import create_client


def get_supabase():
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    return create_client(url, key)


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
                self._send_json({"success": False, "message": "请输入用户名和密码"}, 400)
                return

            supabase = get_supabase()
            email = f"{username}@happy-beauty.local"

            auth_response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password,
            })

            if not auth_response.user:
                self._send_json({"success": False, "message": "用户名或密码错误"}, 401)
                return

            user_id = auth_response.user.id

            # 获取用户资料
            profile_result = supabase.table("user_profiles").select("*").eq("id", user_id).single().execute()

            if not profile_result.data:
                self._send_json({"success": False, "message": "用户资料不存在"}, 404)
                return

            profile = profile_result.data

            self._send_json({
                "success": True,
                "message": "欢迎回来！",
                "user": {
                    "id": user_id,
                    "username": username,
                    "nickname": profile["nickname"],
                    "device_id": profile["device_id"],
                    "credits": profile["credits"],
                    "referrals_today": profile["referrals_today"],
                    "last_referral_date": profile["last_referral_date"]
                },
                "access_token": auth_response.session.access_token if auth_response.session else None
            })

        except Exception as e:
            error_msg = str(e)
            if "invalid" in error_msg.lower():
                self._send_json({"success": False, "message": "用户名或密码错误"}, 401)
            else:
                self._send_json({"success": False, "message": f"登录失败: {error_msg}"}, 500)

    def _send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
