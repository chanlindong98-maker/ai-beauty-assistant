import re
import json
from http.server import BaseHTTPRequestHandler
from datetime import date, timedelta
from api._utils import get_supabase_client, parse_body, send_json, get_auth_token, get_user_from_token

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        send_json(self, {})

    def do_POST(self):
        token = get_auth_token(self)
        user = get_user_from_token(token)
        if not user:
            send_json(self, {"success": False, "message": "请先登录哦 🍭"}, 401)
            return

        try:
            data = parse_body(self)
            code = data.get("code", "").strip()
            
            # 正则验证兑换码
            pattern = r"^(\d{2})(\d+)([A-Z]{4})(\d{2})([a-z]{2})$"
            match = re.match(pattern, code)
            
            if not match:
                send_json(self, {"success": False, "message": "兑换码格式不对哦，请检查一下~"}, 400)
                return
            
            today_dd, credits_str, _, later_dd, _ = match.groups()
            
            # 验证日期
            today = date.today()
            later = today + timedelta(days=13)
            if today_dd != today.strftime("%d") or later_dd != later.strftime("%d"):
                send_json(self, {"success": False, "message": "哎呀，这个兑换码不是今天的，或者已经过期了。"}, 400)
                return
            
            credits_to_add = int(credits_str)
            supabase = get_supabase_client()
            
            # 检查重复
            check = supabase.table("used_redeem_codes").select("code").eq("code", code).execute()
            if check.data:
                send_json(self, {"success": False, "message": "这个兑换码已经用过啦，不能重复使用哦。"}, 400)
                return
            
            # 记录并更新
            supabase.table("used_redeem_codes").insert({
                "code": code,
                "user_id": user["id"],
                "credits_added": credits_to_add
            }).execute()
            
            new_credits = user["credits"] + credits_to_add
            supabase.table("user_profiles").update({"credits": new_credits}).eq("id", user["id"]).execute()
            
            send_json(self, {
                "success": True, 
                "message": f"兑换成功！获得了 {credits_to_add} 次魔法能量 ✨",
                "data": {"credits": new_credits}
            })

        except Exception as e:
            send_json(self, {"success": False, "message": f"兑换过程中出错了: {str(e)}"}, 500)
