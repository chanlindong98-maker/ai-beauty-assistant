"""
Vercel Serverless 共享工具模块
"""
import os
import json
from supabase import create_client


def get_supabase_client():
    """获取 Supabase 客户端"""
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    
    if not url or not key:
        raise ValueError("缺少 Supabase 环境变量 (SUPABASE_URL 或 SUPABASE_SERVICE_ROLE_KEY)")
        
    if not key.startswith("eyJ"):
        raise ValueError("SUPABASE_SERVICE_ROLE_KEY 格式似乎不正确。请确保使用的是 Service Role (Secret) Key，它应该以 'eyJ' 开头。当前值以 " + (key[:4] if key else "空") + " 开头。")
        
    return create_client(url, key)


def cors_headers():
    """CORS 响应头"""
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
    }


def json_response(data: dict, status: int = 200):
    """创建 JSON 响应"""
    from http.server import BaseHTTPRequestHandler
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            **cors_headers()
        },
        "body": json.dumps(data, ensure_ascii=False)
    }


def get_user_from_token(token: str) -> dict | None:
    """从 token 获取用户信息"""
    if not token:
        return None
    
    try:
        supabase = get_supabase_client()
        user_response = supabase.auth.get_user(token)
        
        if not user_response or not user_response.user:
            return None
        
        user_id = user_response.user.id
        
        # 获取用户资料
        profile = supabase.table("user_profiles").select("*").eq("id", user_id).single().execute()
        
        if profile.data:
            return {
                "id": user_id,
                "email": user_response.user.email,
                **profile.data
            }
    except Exception:
        pass
    
    return None


def get_admin_user(token: str) -> dict | None:
    """获取并验证管理员用户"""
    user = get_user_from_token(token)
    if user and user.get("is_admin"):
        return user
    return None


def parse_body(handler) -> dict:
    """解析请求体"""
    try:
        content_length = int(handler.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        body = handler.rfile.read(content_length).decode("utf-8")
        return json.loads(body) if body else {}
    except Exception:
        return {}


def get_auth_token(handler) -> str | None:
    """从处理类中获取认证令牌"""
    auth = handler.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


def send_json(handler, data: dict, status: int = 200):
    """发送 JSON 响应"""
    handler.send_response(status)
    for key, value in cors_headers().items():
        handler.send_header(key, value)
    handler.send_header("Content-Type", "application/json")
    handler.end_headers()
    handler.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
