from http.server import BaseHTTPRequestHandler
import json
import os
import traceback
from decimal import Decimal
from datetime import date, datetime
from urllib.parse import urlparse, parse_qs
from supabase import create_client

# --- 自包含工具函数 (避免 import _utils 失败) ---

def get_supabase_client():
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise ValueError("缺少 Supabase 环境变量 (SUPABASE_URL 或 SUPABASE_SERVICE_ROLE_KEY)")
    return create_client(url, key)

def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
    }

def get_auth_token(handler):
    auth = handler.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None

def get_admin_user(token):
    if not token: return None
    try:
        supabase = get_supabase_client()
        user_res = supabase.auth.get_user(token)
        if not user_res or not user_res.user: return None
        profile = supabase.table("user_profiles").select("is_admin").eq("id", user_res.user.id).single().execute()
        if profile.data and profile.data.get("is_admin"):
            return {"id": user_res.user.id, "is_admin": True}
    except: pass
    return None

def parse_body(handler):
    try:
        content_length = int(handler.headers.get("Content-Length", 0))
        if content_length == 0: return {}
        body = handler.rfile.read(content_length).decode("utf-8")
        return json.loads(body) if body else {}
    except: return {}

class AdminJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal): return float(obj)
        if isinstance(obj, (datetime, date)): return obj.isoformat()
        return super(AdminJSONEncoder, self).default(obj)

def safe_send_json(handler, data, status=200):
    try:
        handler.send_response(status)
        for k, v in cors_headers().items():
            handler.send_header(k, v)
        handler.send_header("Content-Type", "application/json")
        handler.end_headers()
        handler.wfile.write(json.dumps(data, cls=AdminJSONEncoder, ensure_ascii=False).encode("utf-8"))
    except: pass

# --- 处理类 ---

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        safe_send_json(self, {})

    def do_GET(self):
        self.handle_req("GET")

    def do_POST(self):
        self.handle_req("POST")

    def handle_req(self, method):
        try:
            # 识别路由
            parsed = urlparse(self.path)
            action = "unknown"
            if "stats" in parsed.path: action = "stats"
            elif "users" in parsed.path: action = "users"
            elif "credits" in parsed.path: action = "credits"
            elif "config" in parsed.path: action = "config"
            elif "password" in parsed.path: action = "password"

            # 权限检查
            token = get_auth_token(self)
            admin = get_admin_user(token)
            if not admin:
                safe_send_json(self, {"success": False, "message": "管理员权限验证失败，尝试重新登录"}, 403)
                return

            supabase = get_supabase_client()

            if action == "stats" and method == "GET":
                u_res = supabase.table("user_profiles").select("id", count="exact").execute()
                o_res = supabase.table("orders").select("amount").eq("status", "PAID").execute()
                amounts = [float(i["amount"]) for i in (o_res.data or []) if i.get("amount")]
                
                today = str(date.today())
                t_res = supabase.table("orders").select("amount").eq("status", "PAID").gte("created_at", f"{today}T00:00:00").execute()
                t_amounts = [float(i["amount"]) for i in (t_res.data or []) if i.get("amount")]

                safe_send_json(self, {
                    "total_users": u_res.count or 0,
                    "total_recharge_amount": sum(amounts),
                    "today_recharge_amount": sum(t_amounts),
                    "total_orders": len(amounts),
                    "active_users_24h": u_res.count or 0
                })

            elif action == "users" and method == "GET":
                q = parse_qs(parsed.query).get("query", [None])[0]
                builder = supabase.table("user_profiles").select("*")
                if q: builder = builder.ilike("nickname", f"%{q}%")
                res = builder.order("id").limit(100).execute()
                safe_send_json(self, [{"id":i["id"],"nickname":i["nickname"],"credits":i.get("credits",0),"is_admin":i.get("is_admin",False)} for i in (res.data or [])])

            elif action == "config":
                if method == "GET":
                    res = supabase.table("system_config").select("*").execute()
                    db_config = {item["key"]: item for item in (res.data or [])}
                    
                    essential_keys = [
                        ("gemini_api_key", "Google Gemini API 密钥", os.environ.get("GEMINI_API_KEY", "")),
                        ("alipay_app_id", "支付宝 AppID", os.environ.get("ALIPAY_APP_ID", "")),
                        ("alipay_app_private_key", "支付宝应用私钥", os.environ.get("ALIPAY_APP_PRIVATE_KEY", "")),
                        ("alipay_public_key", "支付宝公钥", os.environ.get("ALIPAY_PUBLIC_KEY", "")),
                        ("alipay_notify_url", "支付宝异步回调地址", os.environ.get("ALIPAY_NOTIFY_URL", "")),
                        ("alipay_return_url", "支付宝同步跳转地址", os.environ.get("ALIPAY_RETURN_URL", "")),
                    ]
                    
                    result = []
                    added = set()
                    
                    # 首先添加基础配置项
                    for key, desc, env_val in essential_keys:
                        if key in db_config:
                            result.append(db_config[key])
                        else:
                            result.append({"key": key, "value": env_val or "", "description": desc})
                        added.add(key)
                    
                    # 添加数据库中其他的配置
                    for item in (res.data or []):
                        if item["key"] not in added:
                            result.append(item)
                    
                    safe_send_json(self, result)
                elif method == "POST":
                    items = parse_body(self)
                    for it in items:
                        if "key" in it:
                            supabase.table("system_config").upsert({"key":it["key"],"value":it["value"],"description":it.get("description",""),"updated_at":datetime.utcnow().isoformat()}).execute()
                    safe_send_json(self, {"success":True})

            elif action == "password" and method == "POST":
                pwd = parse_body(self).get("new_password")
                if not pwd or len(pwd) < 6:
                    safe_send_json(self, {"success":False,"message":"密码过短"}, 400)
                    return
                supabase.auth.admin.update_user_by_id(admin["id"], {"password": pwd})
                safe_send_json(self, {"success":True})
            
            else:
                safe_send_json(self, {"success":False,"message":"Unsupported action"}, 404)

        except Exception as e:
            safe_send_json(self, {"success":False,"message":f"API Error: {str(e)}","trace":traceback.format_exc()}, 500)
