import os
import uuid
import json
from datetime import date
from http.server import BaseHTTPRequestHandler

def get_supabase():
    """安全获取 Supabase 客户端"""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not key:
        raise ValueError("缺少 Supabase 环境变量 (SUPABASE_URL 或 SUPABASE_SERVICE_ROLE_KEY)")
        
    try:
        from supabase import create_client
        return create_client(url, key)
    except ImportError:
        raise ImportError("无法在环境中找到 'supabase' 库，请确保 api/requirements.txt 已正确安装")

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
                self._send_json({"success": False, "message": "注册信息不完整哦 🍭"}, 400)
                return

            supabase = get_supabase()
            email = f"{username}@happy-beauty.local"

            # 创建用户
            auth_response = supabase.auth.sign_up({
                "email": email,
                "password": password,
            })

            if not auth_response.user:
                self._send_json({"success": False, "message": "哎呀，注册通道拥挤，请稍后再试"}, 400)
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

            # 推荐逻辑
            if referrer_id:
                try:
                    referrer_result = supabase.table("user_profiles").select("*").eq("device_id", referrer_id).execute()
                    if referrer_result.data:
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
                except:
                    pass # 推荐失败不影响主流程

            supabase.table("user_profiles").insert(profile_data).execute()

            self._send_json({
                "success": True,
                "message": "注册成功！✨",
                "user": {
                    "nickname": nickname,
                    "device_id": device_id,
                    "credits": 3,
                    "isAdmin": False
                },
                "access_token": auth_response.session.access_token if auth_response.session else None
            })

        except Exception as e:
            error_msg = str(e)
            status_code = 500
            user_msg = f"服务器内部错误: {error_msg}"
            
            if "already registered" in error_msg.lower():
                user_msg = "该用户名已经有人用了哦，换一个吧 🍬"
                status_code = 400
            elif "Supabase 环境变量" in error_msg:
                user_msg = "配置错误：请在 Vercel 检查 SUPABASE_URL 环境变量"
                status_code = 500
                
            self._send_json({"success": False, "message": user_msg, "detail": error_msg}, status_code)

    def _send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
