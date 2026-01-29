from http.server import BaseHTTPRequestHandler
import json
from api._utils import get_auth_token, get_admin_user, send_json, get_supabase_client
from urllib.parse import urlparse, parse_qs

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        token = get_auth_token(self)
        admin = get_admin_user(token)
        if not admin:
            send_json(self, {"success": False, "message": "需要管理员权限"}, 403)
            return

        try:
            # 解析查询参数
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            query = query_params.get("query", [None])[0]

            supabase = get_supabase_client()
            builder = supabase.table("user_profiles").select("*")
            
            if query:
                builder = builder.ilike("nickname", f"%{query}%")
            
            res = builder.order("id").limit(100).execute()
            
            users = []
            for item in res.data:
                users.append({
                    "id": item["id"],
                    "nickname": item["nickname"],
                    "email": None,
                    "credits": item["credits"],
                    "is_admin": item.get("is_admin", False)
                })
            
            send_json(self, users)

        except Exception as e:
            send_json(self, {"success": False, "message": f"获取用户列表失败: {str(e)}"}, 500)
