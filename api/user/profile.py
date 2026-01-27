"""
获取用户资料 API
GET /api/user/profile
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
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        try:
            # 获取 token
            auth_header = self.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                self._send_json({"success": False, "message": "未授权"}, 401)
                return

            token = auth_header[7:]
            supabase = get_supabase()

            # 验证 token
            user_response = supabase.auth.get_user(token)
            if not user_response or not user_response.user:
                self._send_json({"success": False, "message": "无效的令牌"}, 401)
                return

            user_id = user_response.user.id

            # 获取用户资料
            profile_result = supabase.table("user_profiles").select("*").eq("id", user_id).single().execute()

            if not profile_result.data:
                self._send_json({"success": False, "message": "用户资料不存在"}, 404)
                return

            profile = profile_result.data

            self._send_json({
                "success": True,
                "message": "获取成功",
                "data": {
                    "id": user_id,
                    "nickname": profile["nickname"],
                    "device_id": profile["device_id"],
                    "credits": profile["credits"],
                    "referrals_today": profile["referrals_today"],
                    "last_referral_date": profile["last_referral_date"]
                }
            })

        except Exception as e:
            self._send_json({"success": False, "message": f"获取失败: {str(e)}"}, 500)

    def _send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
