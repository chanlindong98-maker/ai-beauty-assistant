from http.server import BaseHTTPRequestHandler
import json
import os

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 获取环境变量（脱敏处理）
        supabase_url = os.environ.get("SUPABASE_URL", "未设置")
        service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "未设置")
        
        def mask_key(k):
            if k == "未设置": return k
            if len(k) < 8: return f"太短({len(k)}位)"
            return f"{k[:4]}...{k[-4:]} (长度: {len(k)})"

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        # 简单判断 Key 格式
        is_jwt = service_key.startswith("eyJ")
        
        self.wfile.write(json.dumps({
            "success": True, 
            "message": "API 连通性测试成功！✨",
            "diagnostics": {
                "SUPABASE_URL": supabase_url,
                "SUPABASE_SERVICE_ROLE_KEY": mask_key(service_key),
                "KEY_FORMAT_IS_JWT": is_jwt,
                "PYTHON_VERSION": os.sys.version
            }
        }, ensure_ascii=False).encode('utf-8'))
