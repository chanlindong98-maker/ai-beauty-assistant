"""
用户注册 API
POST /api/auth/register
"""
import os
import uuid
from datetime import date
from http.server import BaseHTTPRequestHandler
from supabase import create_client
import json


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
            nickname = data.get("nickname", "")
            referrer_id = data.get("referrer_id")

            if not username or not password or not nickname:
                self._send_json({"success": False, "message": "信息不完整"}, 400)
                return

            supabase = get_supabase()
            email = f"{username}@happy-beauty.local"

            # 创建用户
            auth_response = supabase.auth.sign_up({
                "email": email,
                "password": password,
            })

            if not auth_response.user:
                self._send_json({"success": False, "message": "注册失败"}, 400)
                return

            user_id = auth_response.user.id
            device_id = uuid.uuid4().hex[:12]

            # 创建用户资料
            profile_data = {
                "id": user_id,
                "nickname": nickname,
                "device_id": device_id,
                "credits": 3,
                "referrals_today": 0,
                "last_referral_date": str(date.today()),
                "referrer_id": None
            }

            # 处理推荐逻辑
            if referrer_id:
                referrer_result = supabase.table("user_profiles").select("*").eq("device_id", referrer_id).execute()
                if referrer_result.data and len(referrer_result.data) > 0:
                    referrer = referrer_result.data[0]
                    today = str(date.today())
                    current_referrals = referrer["referrals_today"] if referrer["last_referral_date"] == today else 0
                    
                    if current_referrals < 5:
                        supabase.table("user_profiles").update({
                            "credits": referrer["credits"] + 1,
                            "referrals_today": current_referrals + 1,
                            "last_referral_date": today
                        }).eq("id", referrer["id"]).execute()
                        profile_data["referrer_id"] = referrer["id"]

            supabase.table("user_profiles").insert(profile_data).execute()

            self._send_json({
                "success": True,
                "message": "注册成功！",
                "user": {
                    "id": user_id,
                    "username": username,
                    "nickname": nickname,
                    "device_id": device_id,
                    "credits": 3,
                    "referrals_today": 0,
                    "last_referral_date": str(date.today())
                },
                "access_token": auth_response.session.access_token if auth_response.session else None
            })

        except Exception as e:
            error_msg = str(e)
            if "already registered" in error_msg.lower():
                self._send_json({"success": False, "message": "用户名已被注册"}, 400)
            else:
                self._send_json({"success": False, "message": f"注册失败: {error_msg}"}, 500)

    def _send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
