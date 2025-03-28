from http.server import BaseHTTPRequestHandler
import json
import os
import sys

# 添加src目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# 导入项目模块
from src.config import get_config
from src.main import PlatformAnalyzer

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        response = {
            "status": "success",
            "message": "Maritime Safety Platform API is running",
            "version": "1.0.0"
        }
        
        self.wfile.write(json.dumps(response).encode())
        return
    
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode())
            
            # 初始化分析器
            analyzer = PlatformAnalyzer()
            
            # 处理请求
            if self.path == '/api/analyze':
                # 这里应该处理实际的分析请求
                # 由于Vercel环境限制，我们返回模拟结果
                result = {
                    "status": "success",
                    "message": "Analysis request received",
                    "data": data,
                    "note": "This is a simplified API endpoint for Vercel deployment"
                }
            else:
                result = {
                    "status": "error",
                    "message": f"Unknown endpoint: {self.path}"
                }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            error_response = {
                "status": "error",
                "message": str(e)
            }
            
            self.wfile.write(json.dumps(error_response).encode())
        
        return
