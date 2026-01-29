from http.server import BaseHTTPRequestHandler
import json
import os
from datetime import datetime
from api._utils import get_auth_token, get_admin_user, send_json, get_supabase_client, parse_body

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        send_json(self, {})

    def do_GET(self):
        token = get_auth_token(self)
        admin = get_admin_user(token)
        if not admin:
            send_json(self, {"success": False, "message": "需要管理员权限"}, 403)
            return

        try:
            # 这里的逻辑参考 backend/api/admin.py
            # 为了能在 serverless 中工作，我们需要直接读取环境变量作为默认值
            supabase = get_supabase_client()
            res = supabase.table("system_config").select("*").execute()
            db_config = {item["key"]: item for item in (res.data or [])}
            
            # 从环境变量读取默认值
            essential_keys = [
                ("gemini_api_key", "Google Gemini API 密钥 (AI 核心)", os.environ.get("GEMINI_API_KEY", "")),
                ("alipay_app_id", "支付宝 AppID", os.environ.get("ALIPAY_APP_ID", "")),
                ("alipay_app_private_key", "支付宝应用私钥", os.environ.get("ALIPAY_APP_PRIVATE_KEY", "")),
                ("alipay_public_key", "支付宝公钥", os.environ.get("ALIPAY_PUBLIC_KEY", "")),
                ("alipay_notify_url", "支付宝异步回调地址", os.environ.get("ALIPAY_NOTIFY_URL", "")),
                ("alipay_return_url", "支付宝同步跳转地址", os.environ.get("ALIPAY_RETURN_URL", "")),
            ]
            
            result = []
            added_keys = set()
            
            for key, desc, env_val in essential_keys:
                if key in db_config:
                    result.append(db_config[key])
                else:
                    result.append({"key": key, "value": env_val or "", "description": desc})
                added_keys.add(key)
            
            for item in (res.data or []):
                if item["key"] not in added_keys:
                    result.append(item)
            
            send_json(self, result)

        except Exception as e:
            send_json(self, {"success": False, "message": f"获取配置失败: {str(e)}"}, 500)

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
