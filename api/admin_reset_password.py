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
            new_pwd = data.get("new_password")
            if not new_pwd or len(new_pwd) < 6:
                send_json(self, {"success": False, "message": "新密码长度至少为 6 位"}, 400)
                return
                
            supabase = get_supabase_client()
            # 使用超级权限修改用户密码
            supabase.auth.admin.update_user_by_id(
                admin["id"],
                {"password": new_pwd}
            )
            
            send_json(self, {"success": True, "message": "密码修改成功！"})

        except Exception as e:
            send_json(self, {"success": False, "message": f"修改密码失败: {str(e)}"}, 500)
