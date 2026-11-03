"""Remove the white ring around the black icon square and write PNG/ICNS/ICO.

Usage: python3 tools/make_icon.py  (reads/writes assets/AppIcon.*)
Run once on the original image; running it again crops a little more each time.
"""
from PIL import Image, ImageDraw

SRC = "assets/AppIcon.png"
INNER = (118, 118, 906, 906)   # black square inside the white ring (source pixels)
RADIUS = 128                   # corner radius of that square (source pixels)
BODY, CANVAS, SS = 824, 1024, 4  # Apple grid: 824 px body on a 1024 canvas

src = Image.open(SRC).convert("RGBA")
square = src.crop(INNER).resize((BODY, BODY), Image.LANCZOS)

# Anti-aliased rounded-rect mask (draw 4x larger, then shrink).
r = round(RADIUS * BODY / (INNER[2] - INNER[0]))
big = Image.new("L", (BODY * SS, BODY * SS), 0)
ImageDraw.Draw(big).rounded_rectangle((0, 0, BODY * SS - 1, BODY * SS - 1), r * SS, fill=255)
square.putalpha(big.resize((BODY, BODY), Image.LANCZOS))

out = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
off = (CANVAS - BODY) // 2
out.paste(square, (off, off), square)
out.save("assets/AppIcon.png")
out.save("assets/AppIcon.icns")
# Windows: no Apple padding, so the square fills the icon.
tight = out.crop((off, off, off + BODY, off + BODY))
tight.save("assets/AppIcon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("wrote assets/AppIcon.png, .icns, .ico")
