from http.server import BaseHTTPRequestHandler
import json
from api._utils import get_auth_token, get_admin_user, send_json, get_supabase_client, parse_body

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        send_json(self, {})

    def do_POST(self):
        token = get_auth_token(self)
        admin = get_admin_user(token)
        if not admin:
            send_json(self, {"success": False, "message": "需要管理员权限"}, 403)
            return

        try:
            data = parse_body(self)
            user_id = data.get("user_id")
            credits = data.get("credits", 0)
            mode = data.get("mode", "set") # add or set

            if not user_id:
                send_json(self, {"success": False, "message": "缺少用户 ID"}, 400)
                return

            supabase = get_supabase_client()
            
            if mode == "add":
                # 获取当前值
                res = supabase.table("user_profiles").select("credits").eq("id", user_id).single().execute()
                if not res.data:
                    send_json(self, {"success": False, "message": "用户不存在"}, 404)
                    return
                new_credits = res.data["credits"] + credits
            else:
                new_credits = credits
                
            if new_credits < 0:
                new_credits = 0
                
            supabase.table("user_profiles")\
                .update({"credits": new_credits})\
                .eq("id", user_id)\
                .execute()
                
            send_json(self, {"success": True, "message": f"成功更新为 {new_credits} 次", "new_credits": new_credits})

        except Exception as e:
            send_json(self, {"success": False, "message": f"更新魔法值失败: {str(e)}"}, 500)
