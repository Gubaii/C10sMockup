from flask import Flask, Response
import sys, os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入app.py中的Flask应用
from app import app as flask_app

# Vercel处理函数
from flask.helpers import send_from_directory
from werkzeug.middleware.shared_data import SharedDataMiddleware

# 修改Flask应用以支持static文件
flask_app.wsgi_app = SharedDataMiddleware(flask_app.wsgi_app, {
    '/static': os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')
}

# 简化的handler函数，直接作为WSGI应用程序入口
app = flask_app
