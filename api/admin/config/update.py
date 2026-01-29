from http.server import BaseHTTPRequestHandler
import json
from api._utils import get_auth_token, get_admin_user, send_json, get_supabase_client, parse_body
from datetime import datetime

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
            items = parse_body(self)
            if not isinstance(items, list):
                send_json(self, {"success": False, "message": "无效的数据格式"}, 400)
                return

            supabase = get_supabase_client()
            for item in items:
                supabase.table("system_config").upsert({
                    "key": item.get("key"),
                    "value": item.get("value"),
                    "description": item.get("description"),
                    "updated_at": datetime.utcnow().isoformat()
                }).execute()
            
            send_json(self, {"success": True, "message": "配置已更新"})

        except Exception as e:
            send_json(self, {"success": False, "message": f"更新配置失败: {str(e)}"}, 500)
