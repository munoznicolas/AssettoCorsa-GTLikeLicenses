"""
Texture Generator for GT-Like Licenses Mod
Generates RGBA PNG textures for:
- medal_gold.png
- medal_silver.png
- medal_bronze.png
- ribbon_start.png
- ribbon_finish.png
"""

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def draw_medal(filepath: Path, base_color: tuple[int, int, int], rim_color: tuple[int, int, int], text: str):
    size = (256, 256)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    center = 128
    radius = 110
    
    # Outer glowing rim / drop shadow
    draw.ellipse([center - radius - 6, center - radius - 6, center + radius + 6, center + radius + 6], fill=(0, 0, 0, 100))
    # Outer metallic ring
    draw.ellipse([center - radius, center - radius, center + radius, center + radius], fill=rim_color)
    # Inner medal body
    draw.ellipse([center - radius + 10, center - radius + 10, center + radius - 10, center + radius - 10], fill=base_color)
    
    # Star / Laurel design in center
    star_points = []
    num_points = 5
    outer_r = 55
    inner_r = 25
    for i in range(num_points * 2):
        r = outer_r if i % 2 == 0 else inner_r
        angle = i * math.pi / num_points - math.pi / 2
        star_points.append((center + r * math.cos(angle), center + r * math.sin(angle)))
    
    draw.polygon(star_points, fill=rim_color)
    
    filepath.parent.mkdir(parents=True, exist_ok=True)
    img.save(filepath, "PNG")
    print(f"Generated: {filepath}")

def draw_start_ribbon(filepath: Path):
    """Generates glowing cyan/white neon chevron gradient pattern for start ribbon."""
    w, h = 512, 128
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Gradient backdrop: vibrant cyan with neon glow
    for x in range(w):
        pulse = 0.5 + 0.5 * math.sin(x / w * math.pi * 8)
        r = int(0 + 40 * pulse)
        g = int(180 + 75 * pulse)
        b = int(240 + 15 * pulse)
        alpha = 230
        draw.line([(x, 0), (x, h)], fill=(r, g, b, alpha))
        
    # Border glows top and bottom
    draw.line([(0, 0), (w, 0)], fill=(255, 255, 255, 255), width=3)
    draw.line([(0, h - 1), (w, h - 1)], fill=(255, 255, 255, 255), width=3)
    
    filepath.parent.mkdir(parents=True, exist_ok=True)
    img.save(filepath, "PNG")
    print(f"Generated: {filepath}")

def draw_finish_ribbon(filepath: Path):
    """Generates high-contrast chequered racing flag ribbon."""
    w, h = 512, 128
    img = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    cols = 16
    rows = 4
    cw = w // cols
    ch = h // rows
    
    for r in range(rows):
        for c in range(cols):
            if (r + c) % 2 == 1:
                draw.rectangle([c * cw, r * ch, (c + 1) * cw, (r + 1) * ch], fill=(20, 20, 20, 255))
                
    # Border neon finish line
    draw.line([(0, 0), (w, 0)], fill=(255, 50, 50, 255), width=4)
    draw.line([(0, h - 1), (w, h - 1)], fill=(255, 50, 50, 255), width=4)
    
    filepath.parent.mkdir(parents=True, exist_ok=True)
    img.save(filepath, "PNG")
    print(f"Generated: {filepath}")

def main():
    base_dir = Path("d:/Repositories/AssettoCorsa-GTLikeLicenses/assets/textures")
    draw_medal(base_dir / "medal_gold.png", (245, 185, 30, 255), (255, 235, 120, 255), "GOLD")
    draw_medal(base_dir / "medal_silver.png", (185, 195, 205, 255), (240, 245, 250, 255), "SILVER")
    draw_medal(base_dir / "medal_bronze.png", (185, 115, 60, 255), (230, 165, 110, 255), "BRONZE")
    draw_start_ribbon(base_dir / "ribbon_start.png")
    draw_finish_ribbon(base_dir / "ribbon_finish.png")
    print("All texture assets generated successfully!")

if __name__ == "__main__":
    main()
