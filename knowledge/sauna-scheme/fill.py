import sys
from PIL import Image, ImageDraw, ImageFont
src, dst = sys.argv[1], sys.argv[2]
im = Image.open(src).convert("RGB")
d = ImageDraw.Draw(im)
F = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
BLUE=(10,40,200); RED=(210,20,20)
K=1512/1500
# (x, y_center, text, color, size) in preview coords
items = [
 (470,673,"10°",BLUE,26),
 (1301,717,"500",BLUE,20),
 (950,703,"500",BLUE,22),
 (903,962,"130",BLUE,20),
 (400,1045,"120",BLUE,20),
 (873,1092,"500",BLUE,20),
 (771,1113,"380",BLUE,22),
 (222,1177,"500",RED,22),
 (1138,1278,"70",BLUE,20),
 (181,1540,"260",BLUE,18),
 (1034,1594,"700",BLUE,16),
 (1081,1594,"500",BLUE,18),
 (1311,1653,"140",RED,20),
 (866,495,"1,0",RED,16),
 (543,424,"0,5",BLUE,20),
 (582,496,"0,7",BLUE,20),
]
for x,y,t,c,s in items:
    f = ImageFont.truetype(F, round(s*K))
    d.text((x*K,y*K), t, font=f, fill=c, anchor="lm")
im.save(dst, quality=95)
