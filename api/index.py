from flask import Flask
import sys, os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入app.py中的Flask应用
from app import app

# Vercel处理函数
def handler(request):
    return app
