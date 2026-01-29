import os
import json
import sys
from http.server import BaseHTTPRequestHandler
import google.generativeai as genai

# 导入共享工具模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _utils import get_config

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # 优先从数据库读取 API 密钥
            api_key = get_config("gemini_api_key")
            if not api_key:
                self._send_json({"success": False, "message": "未配置 Gemini API 密钥，请在管理后台设置"}, 500)
                return

            genai.configure(api_key=api_key, transport='rest')
            
            models = []
            for m in genai.list_models():
                models.append({
                    "name": m.name,
                    "version": m.version,
                    "display_name": m.display_name,
                    "description": m.description,
                    "supported_generation_methods": m.supported_generation_methods
                })

            self._send_json({
                "success": True,
                "message": f"成功获取到 {len(models)} 个可用模型",
                "models": models,
                "api_key_masked": f"{api_key[:6]}...{api_key[-4:]}" if len(api_key) > 10 else "invalid"
            })

        except Exception as e:
            self._send_json({
                "success": False, 
                "message": f"获取模型列表失败: {str(e)}"
            }, 500)

    def _send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
