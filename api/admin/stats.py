from http.server import BaseHTTPRequestHandler
import json
from api._utils import get_auth_token, get_admin_user, send_json, get_supabase_client
from datetime import date

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        token = get_auth_token(self)
        admin = get_admin_user(token)
        if not admin:
            send_json(self, {"success": False, "message": "需要管理员权限"}, 403)
            return

        try:
            supabase = get_supabase_client()
            
            # 1. 总用户数
            users_res = supabase.table("user_profiles").select("id", count="exact").execute()
            total_users = users_res.count or 0
            
            # 2. 充值总额和总订单数 (已支付)
            orders_res = supabase.table("orders").select("amount").eq("status", "PAID").execute()
            total_recharge_amount = sum(item["amount"] for item in orders_res.data) if orders_res.data else 0
            total_orders = len(orders_res.data) if orders_res.data else 0
            
            # 3. 今日充值额
            today = str(date.today())
            today_orders_res = supabase.table("orders")\
                .select("amount")\
                .eq("status", "PAID")\
                .gte("created_at", f"{today}T00:00:00")\
                .execute()
            today_recharge_amount = sum(item["amount"] for item in today_orders_res.data) if today_orders_res.data else 0
            
            send_json(self, {
                "total_users": total_users,
                "total_recharge_amount": total_recharge_amount,
                "today_recharge_amount": today_recharge_amount,
                "total_orders": total_orders,
                "active_users_24h": total_users # 暂时简化
            })

        except Exception as e:
            send_json(self, {"success": False, "message": f"获取统计数据失败: {str(e)}"}, 500)
