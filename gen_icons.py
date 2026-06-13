
import os, math
from PIL import Image, ImageDraw

SIZE = 81
CENTER = SIZE // 2
OUTDIR = os.path.expanduser(r"~\.qclaw\workspace\memory-app\miniprogram\images")
os.makedirs(OUTDIR, exist_ok=True)

NORMAL = (138, 138, 154)    # #8a8a9a
ACTIVE = (108, 99, 255)     # #6c63ff

def new_icon():
    return Image.new("RGBA", (SIZE, SIZE), (0,0,0,0))

def draw_circle(draw, cx, cy, r, color, width=2):
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=color, width=width)

def draw_line(draw, x1, y1, x2, y2, color, width=2):
    draw.line([(x1,y1),(x2,y2)], fill=color, width=width)

def draw_poly(draw, points, color):
    draw.polygon(points, fill=color)

def save_both(name, draw_fn):
    """Save normal and active versions."""
    for suffix, color in [("", NORMAL), ("-active", ACTIVE)]:
        img = new_icon()
        d = ImageDraw.Draw(img)
        draw_fn(d, color)
        path = os.path.join(OUTDIR, f"{name}{suffix}.png")
        img.save(path, "PNG")
        print(f"  {name}{suffix}.png")

# ── 1. capture (捕获) — pencil/edit icon ──
def capture_icon(draw, c):
    w = 2.5
    # pencil body (diagonal)
    x0, y0 = 52, 18
    x1, y1 = 28, 56
    # shaft
    draw.line([(x0, y0), (x1, y1)], fill=c, width=int(w*1.5))
    # tip (triangle)
    tip_pts = [(x1, y1), (x1-7, y1+2), (x1+2, y1+7)]
    draw_poly(draw, tip_pts, c)
    # top eraser
    draw.line([(x0, y0), (x0+4, y0-8)], fill=c, width=int(w))
    draw.line([(x0-4, y0-8), (x0+8, y0-12)], fill=c, width=int(w*1.2))
save_both("capture", capture_icon)

# ── 2. discover (发现) — compass / star ──
def discover_icon(draw, c):
    w = 2
    cx, cy = 40, 40
    r = 16
    draw_circle(draw, cx, cy, r, c, width=int(w))
    # compass needle (N)
    draw_line(draw, cx, cy-13, cx, cy+8, c, width=int(w*1.5))
    # smaller needle (S)
    draw_line(draw, cx, cy-5, cx, cy+13, c, width=int(w))
    # center dot
    draw.ellipse([cx-3,cy-3,cx+3,cy+3], fill=c)
    # N mark
    draw_line(draw, cx, cy-18, cx, cy-22, c, width=int(w*1.2))
save_both("discover", discover_icon)

# ── 3. search (搜索) — magnifying glass ──
def search_icon(draw, c):
    w = 2.5
    # glass circle
    cx, cy = 32, 32
    r = 14
    draw.ellipse([cx-r,cy-r,cx+r,cy+r], outline=c, width=int(w))
    # handle
    angle = math.radians(45)
    hx = cx + r * math.cos(angle)
    hy = cy + r * math.sin(angle)
    hx2 = hx + 16
    hy2 = hy + 16
    draw.line([(hx, hy), (hx2, hy2)], fill=c, width=int(w*1.8))
    # rounded cap
    draw.ellipse([hx2-3,hy2-3,hx2+3,hy2+3], fill=c)
save_both("search", search_icon)

# ── 4. mine (我的) — person/profile ──
def mine_icon(draw, c):
    w = 2.5
    cx, cy = 40, 28
    # head
    r = 10
    draw.ellipse([cx-r,cy-r,cx+r,cy+r], outline=c, width=int(w))
    # body (arc from shoulders)
    body_top = cy + r
    body_bot = 64
    # shoulders curve
    shoulder_w = 13
    draw.arc([cx-shoulder_w, body_top-4, cx+shoulder_w, body_top+20], 
             math.radians(180), math.radians(360), fill=c, width=int(w))
    # body sides down
    draw.line([(cx-shoulder_w, body_top+6), (cx-shoulder_w+5, body_bot)], fill=c, width=int(w))
    draw.line([(cx+shoulder_w, body_top+6), (cx+shoulder_w-5, body_bot)], fill=c, width=int(w))
save_both("mine", mine_icon)

print("\nDone! 8 icons generated.")
