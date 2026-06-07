"""生成 StockOracle 应用图标"""
from PIL import Image, ImageDraw, ImageFont
import os

def create_icon():
    # 创建多个尺寸的图标（用于 .ico 文件）
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    images = []
    
    for size in sizes:
        # 创建带透明背景的图像
        img = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # 绘制圆角矩形背景
        margin = size[0] // 8
        corner_radius = size[0] // 4
        draw.rounded_rectangle(
            [margin, margin, size[0] - margin, size[1] - margin],
            radius=corner_radius,
            fill=(41, 128, 185, 255),  # 蓝色背景
        )
        
        # 绘制股票图标（简化的上升曲线）
        center_x, center_y = size[0] // 2, size[1] // 2
        line_width = max(1, size[0] // 16)
        
        # 绘制上升折线
        points = [
            (size[0] // 4, size[1] * 3 // 4),
            (size[0] // 3, size[1] // 2),
            (size[0] // 2, size[1] * 2 // 3),
            (size[0] * 2 // 3, size[1] // 3),
            (size[0] * 3 // 4, size[1] // 4),
        ]
        draw.line(points, fill=(255, 255, 255, 255), width=line_width)
        
        # 绘制箭头
        arrow_size = size[0] // 8
        arrow_x = size[0] * 3 // 4
        arrow_y = size[1] // 4
        draw.polygon([
            (arrow_x, arrow_y - arrow_size),
            (arrow_x + arrow_size, arrow_y),
            (arrow_x, arrow_y + arrow_size // 2),
        ], fill=(255, 255, 255, 255))
        
        images.append(img)
    
    # 保存为 .ico 文件
    icon_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'icons', 'app_icon.ico')
    images[0].save(
        icon_path,
        format='ICO',
        sizes=sizes,
        append_images=images[1:]
    )
    print(f"图标已保存: {os.path.abspath(icon_path)}")
    
    # 同时保存 PNG 版本
    png_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'icons', 'app_icon.png')
    images[-1].save(png_path, format='PNG')
    print(f"PNG 图标已保存: {os.path.abspath(png_path)}")

if __name__ == '__main__':
    create_icon()
