from flask import Flask
import sys
import os

# 添加应用目录到路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app