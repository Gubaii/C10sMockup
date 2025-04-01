from flask import Flask, request, render_template, send_file, jsonify
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import io
import os
import json
import numpy as np

app = Flask(__name__, static_url_path='/static')

# 确保上传文件夹存在
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def process_image(image, invert=False, make_transparent=False):
    # 转换为灰度图
    gray_image = ImageOps.grayscale(image)
    
    # 如果需要反相
    if invert:
        gray_image = ImageOps.invert(gray_image)
    
    # 如果需要透明化处理
    if make_transparent:
        # 创建RGBA模式的新图像
        rgba_image = Image.new('RGBA', gray_image.size)
        for x in range(gray_image.size[0]):
            for y in range(gray_image.size[1]):
                gray_value = gray_image.getpixel((x, y))
                # 调整透明度计算方式
                # 使用阈值：当灰度值大于200（接近白色）时保持完全不透明
                # 其他值按比例调整，使得中间灰度也更倾向于不透明
                if gray_value > 200:
                    alpha = 255
                else:
                    # 将0-200的值映射到0-255，并使用指数函数使得更多像素保持不透明
                    alpha = int((gray_value / 200) ** 0.7 * 255)
                rgba_image.putpixel((x, y), (255, 255, 255, alpha))
        return rgba_image
    
    return gray_image

def process_image_transparent(image, invert=False, levels=10, contrast=1.0):
    # 转换为灰度图
    gray_image = ImageOps.grayscale(image)
    
    # 如果需要反相
    if invert:
        gray_image = ImageOps.invert(gray_image)
    
    # 增强对比度
    if contrast != 1.0:
        enhancer = ImageEnhance.Contrast(gray_image)
        gray_image = enhancer.enhance(contrast)
    
    # 创建RGBA模式的新图像
    rgba_image = Image.new('RGBA', gray_image.size)
    
    # 计算50-200之间的等级间隔
    interval = (200 - 50) / levels
    
    # 基于灰度值创建透明度
    for x in range(gray_image.size[0]):
        for y in range(gray_image.size[1]):
            gray_value = gray_image.getpixel((x, y))
            
            # 小于50的变为完全透明
            if gray_value < 50:
                alpha = 0
            # 200以上的灰度值都变成完全不透明
            elif gray_value > 200:
                alpha = 255
            else:
                # 50-200之间分为levels个等级，就近归入等级
                level = round((gray_value - 50) / interval)
                # 确保level在合理范围内
                level = max(0, min(levels - 1, level))
                # 计算该等级对应的alpha值
                alpha = int(50 + level * interval)
                # 将alpha值映射到0-255范围
                alpha = int((alpha - 50) / 150 * 255)
            
            rgba_image.putpixel((x, y), (255, 255, 255, alpha))
    
    return rgba_image

def create_text_mask(text, width, height, font_size=40):
    # 创建一个黑色背景的图像（背景透明）
    image = Image.new('L', (width, height), 0)
    draw = ImageDraw.Draw(image)
    
    try:
        # 尝试使用系统字体
        font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", font_size)
    except:
        try:
            # 尝试使用 Arial
            font = ImageFont.truetype("Arial", font_size)
        except:
            # 使用默认字体
            font = ImageFont.load_default()
            font_size = 40  # 重置字体大小
    
    # 获取文本大小
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    # 计算居中位置
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    
    # 先绘制文字轮廓（白色）
    draw.text((x, y), text, fill=255, font=font, stroke_width=5, stroke_fill=255)
    # 再绘制文字内部（白色）
    draw.text((x, y), text, fill=255, font=font)
    
    # 稍微模糊处理以改善边缘
    image = image.filter(ImageFilter.GaussianBlur(radius=0.5))
    
    # 增强对比度，确保文字是纯白色
    image = ImageOps.autocontrast(image, cutoff=1)
    
    # 二值化处理，确保只有黑白两种颜色
    threshold = 128
    image = image.point(lambda x: 255 if x > threshold else 0)
    
    return image

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    if 'image' not in request.files:
        return 'No image uploaded', 400
    
    file = request.files['image']
    if file.filename == '':
        return 'No selected file', 400
    
    # 获取处理选项
    invert = request.form.get('invert') == 'true'
    make_transparent = request.form.get('transparent') == 'true'
    
    # 打开并处理图像
    image = Image.open(file)
    processed_image = process_image(image, invert, make_transparent)
    
    # 将处理后的图像保存到内存中
    img_io = io.BytesIO()
    if make_transparent:
        processed_image.save(img_io, 'PNG')
    else:
        processed_image.save(img_io, 'JPEG')
    img_io.seek(0)
    
    return send_file(img_io, 
                    mimetype='image/png' if make_transparent else 'image/jpeg',
                    as_attachment=True,
                    download_name='processed_image.png' if make_transparent else 'processed_image.jpg')

@app.route('/process_transparent', methods=['POST'])
def process_transparent():
    if 'image' not in request.files:
        return 'No image uploaded', 400
    
    file = request.files['image']
    if file.filename == '':
        return 'No selected file', 400
    
    # 获取反相选项、等级数量和对比度
    invert = request.form.get('invert') == 'true'
    levels = int(request.form.get('levels', 10))  # 默认10个等级
    contrast = float(request.form.get('contrast', 1.0))  # 默认不改变对比度
    
    # 打开并处理图像
    image = Image.open(file)
    processed_image = process_image_transparent(image, invert, levels, contrast)
    
    # 将处理后的图像保存到内存中
    img_io = io.BytesIO()
    processed_image.save(img_io, 'PNG')
    img_io.seek(0)
    
    return send_file(img_io, mimetype='image/png')

@app.route('/apply_texture', methods=['POST'])
def apply_texture():
    if 'texture' not in request.files or 'object_data' not in request.form:
        return 'Missing data', 400
    
    # 获取纹理图片
    texture_file = request.files['texture']
    texture_image = Image.open(texture_file)
    
    # 获取对象数据
    object_data = json.loads(request.form['object_data'])
    width = int(object_data['width'])
    height = int(object_data['height'])
    
    # 调整纹理图片大小
    texture_image = texture_image.resize((width, height), Image.Resampling.LANCZOS)
    
    # 创建蒙版
    if object_data['type'] == 'text':
        # 对于文字，使用文字形状作为蒙版
        mask = create_text_mask(object_data['text'], width, height)
    else:
        # 对于图片元素，先转灰度再创建透明蒙版
        original_image = Image.open(request.files['image']) if 'image' in request.files else None
        if original_image:
            # 获取反相选项
            invert = request.form.get('invert') == 'true'
            # 调整原始图片大小
            original_image = original_image.resize((width, height), Image.Resampling.LANCZOS)
            # 转换为灰度图
            gray_image = ImageOps.grayscale(original_image)
            # 如果需要反相
            if invert:
                gray_image = ImageOps.invert(gray_image)
            # 创建蒙版
            mask = Image.new('L', gray_image.size)
            for x in range(gray_image.size[0]):
                for y in range(gray_image.size[1]):
                    gray_value = gray_image.getpixel((x, y))
                    # 白色区域（灰度值接近255）显示纹理
                    # 黑色区域（灰度值接近0）完全透明
                    if gray_value > 200:
                        mask_value = 255  # 完全显示纹理
                    else:
                        # 其他区域按比例显示纹理
                        mask_value = gray_value  # 灰度值直接决定纹理显示程度
                    mask.putpixel((x, y), mask_value)
        else:
            # 如果没有原始图片，使用处理后的透明度
            processed = process_image_transparent(texture_image)
            mask = processed.split()[3]
    
    # 将纹理图片转换为RGBA
    texture_rgba = texture_image.convert('RGBA')
    
    # 创建最终图像
    result = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    
    # 使用numpy进行更快的图像处理
    texture_array = np.array(texture_rgba)
    mask_array = np.array(mask)
    
    # 创建结果数组
    result_array = np.zeros((height, width, 4), dtype=np.uint8)
    
    # 复制纹理的RGB通道到结果数组
    result_array[..., :3] = texture_array[..., :3]
    
    # 使用蒙版作为alpha通道
    result_array[..., 3] = mask_array
    
    # 创建一个布尔掩码，标识需要保持透明的区域
    transparent_mask = mask_array == 0
    
    # 将透明区域的所有通道都设为0
    result_array[transparent_mask] = [0, 0, 0, 0]
    
    # 转换回PIL图像
    result = Image.fromarray(result_array)
    
    # 保存到内存
    img_io = io.BytesIO()
    result.save(img_io, 'PNG')
    img_io.seek(0)
    
    return send_file(img_io, mimetype='image/png')

@app.route('/default_images', methods=['GET'])
def default_images():
    """返回默认图片路径"""
    return jsonify({
        'background': 'https://i.imgur.com/dZiq5zz.jpg',
        'texture': 'https://i.imgur.com/q4k2sZw.jpg',
        'element': 'https://i.imgur.com/L8ObmW8.png'
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001) 