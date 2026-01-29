from http.server import BaseHTTPRequestHandler
import json
import os
from datetime import date, datetime
from api._utils import get_auth_token, get_admin_user, send_json, get_supabase_client, parse_body
from urllib.parse import urlparse, parse_qs

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        send_json(self, {})

    def do_GET(self):
        self.handle_request("GET")

    def do_POST(self):
        self.handle_request("POST")

    def handle_request(self, method):
        # 1. 验证权限
        token = get_auth_token(self)
        admin = get_admin_user(token)
        if not admin:
            send_json(self, {"success": False, "message": "需要管理员权限"}, 403)
            return

        # 2. 解析路由
        parsed_url = urlparse(self.path)
        path = parsed_url.path.strip("/")
        # 处理可能的后缀，例如 /api/admin_stats -> admin_stats
        action = path.split("/")[-1] 
        
        # 如果是通过 query 参数传递 action (作为备选)
        query_params = parse_qs(parsed_url.query)
        action_param = query_params.get("action", [None])[0]
        if action_param:
            action = action_param

        try:
            supabase = get_supabase_client()

            # --- 分发路由 ---
            
            # [Stats] 营收统计
            if "stats" in action and method == "GET":
                # 总用户
                users_res = supabase.table("user_profiles").select("id", count="exact").execute()
                total_users = users_res.count or 0
                # 订单统计
                orders_res = supabase.table("orders").select("amount").eq("status", "PAID").execute()
                total_recharge_amount = sum(float(item["amount"]) for item in (orders_res.data or []))
                total_orders = len(orders_res.data or [])
                # 今日统计
                today = str(date.today())
                today_res = supabase.table("orders").select("amount").eq("status", "PAID").gte("created_at", f"{today}T00:00:00").execute()
                today_recharge_amount = sum(float(item["amount"]) for item in (today_res.data or []))
                
                send_json(self, {
                    "total_users": total_users,
                    "total_recharge_amount": total_recharge_amount,
                    "today_recharge_amount": today_recharge_amount,
                    "total_orders": total_orders,
                    "active_users_24h": total_users
                })

            # [Users] 会员列表
            elif "users" in action and method == "GET":
                query = query_params.get("query", [None])[0]
                builder = supabase.table("user_profiles").select("*")
                if query:
                    builder = builder.ilike("nickname", f"%{query}%")
                res = builder.order("id").limit(100).execute()
                users = []
                for item in (res.data or []):
                    users.append({
                        "id": item["id"],
                        "nickname": item["nickname"],
                        "email": None,
                        "credits": item["credits"],
                        "is_admin": item.get("is_admin", False)
                    })
                send_json(self, users)

            # [Credits] 修改魔法值
            elif "credits" in action and method == "POST":
                data = parse_body(self)
                user_id = data.get("user_id")
                credits = data.get("credits", 0)
                mode = data.get("mode", "set")
                if not user_id:
                    send_json(self, {"success": False, "message": "缺少用户 ID"}, 400)
                    return
                
                if mode == "add":
                    curr = supabase.table("user_profiles").select("credits").eq("id", user_id).single().execute()
                    new_credits = (curr.data["credits"] if curr.data else 0) + credits
                else:
                    new_credits = credits
                
                new_credits = max(0, new_credits)
                supabase.table("user_profiles").update({"credits": new_credits}).eq("id", user_id).execute()
                send_json(self, {"success": True, "message": f"成功更新为 {new_credits} 次", "new_credits": new_credits})

            # [Config] 系统设置
            elif "config" in action:
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
                    for key, desc, env_val in essential_keys:
                        if key in db_config:
                            result.append(db_config[key])
                        else:
                            result.append({"key": key, "value": env_val or "", "description": desc})
                        added.add(key)
                    for item in (res.data or []):
                        if item["key"] not in added:
                            result.append(item)
                    send_json(self, result)
                elif method == "POST":
                    items = parse_body(self)
                    if not isinstance(items, list):
                        send_json(self, {"success": False, "message": "格式无效"}, 400)
                        return
                    for item in items:
                        supabase.table("system_config").upsert({
                            "key": item.get("key"),
                            "value": item.get("value"),
                            "description": item.get("description"),
                            "updated_at": datetime.utcnow().isoformat()
                        }).execute()
                    send_json(self, {"success": True, "message": "配置已更新"})

            # [Password] 重置密码
            elif "password" in action and method == "POST":
                data = parse_body(self)
                new_pwd = data.get("new_password")
                if not new_pwd or len(new_pwd) < 6:
                    send_json(self, {"success": False, "message": "密码至少6位"}, 400)
                    return
                supabase.auth.admin.update_user_by_id(admin["id"], {"password": new_pwd})
                send_json(self, {"success": True, "message": "修改成功"})

            else:
                send_json(self, {"success": False, "message": f"未知的操作: {action}"}, 404)

        except Exception as e:
            send_json(self, {"success": False, "message": f"管理操作失败: {str(e)}"}, 500)
