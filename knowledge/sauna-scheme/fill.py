import sys
from PIL import Image, ImageDraw, ImageFont
src, dst = sys.argv[1], sys.argv[2]
im = Image.open(src).convert("RGB")
d = ImageDraw.Draw(im)
F = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
BLUE=(10,40,200); RED=(210,20,20); ORANGE=(225,105,0)
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
 (1138,1278,"70",ORANGE,20),
 (181,1540,"260",ORANGE,18),
 (1034,1594,"700",BLUE,16),
 (1081,1594,"500",BLUE,18),
 (1311,1653,"140",ORANGE,20),
 (860,495,"1,25",ORANGE,14),
 (543,424,"0,5",BLUE,20),
 (582,496,"0,7",BLUE,20),
]
for x,y,t,c,s in items:
    f = ImageFont.truetype(F, round(s*K))
    d.text((x*K,y*K), t, font=f, fill=c, anchor="lm")
FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
# (x, y_center, text, color, size): подписи пунктов СП 7.13130.2013 (ред. 27.03.2025)
labels = [
 (240,806,"п. 5.10",BLUE,14),
 (1205,806,"п. 5.10",BLUE,14),
 (985,962,"п. 5.20",BLUE,13),
 (140,1078,"п. 5.11",BLUE,14),
 (1010,1112,"Прил. Б, п. Б.1",BLUE,13),
 (90,1208,"норма не найдена",RED,13),
 (1008,1322,"п. 5.14",ORANGE,14),
 (84,1575,"Прил. Б, табл. Б.1",ORANGE,13),
 (1030,1624,"п. 5.21, пп. а",BLUE,13),
 (1215,1700,"п. 5.22, пп. а",ORANGE,13),
 (70,455,"Лист 0,5 x 0,7 м: п. 5.21, пп. а",BLUE,14),
 (70,480,"До стены 1,25 м: п. 5.21",ORANGE,14),
 (80,1870,"Источник: СП 7.13130.2013 (ред. от 27.03.2025). Паспорт печи приоритетнее.",(40,40,40),15),
 (80,1895,"Синий: значение и место на схеме подтверждены пунктом СП.",BLUE,15),
 (80,1920,"Оранжевый: значение из СП, привязка к месту на схеме моя трактовка.",ORANGE,15),
 (80,1945,"Красный: норма не найдена.",RED,15),
]
for x,y,t,c,sz in labels:
    f = ImageFont.truetype(FR, round((sz+2)*K))
    bb = d.textbbox((x*K,y*K), t, font=f, anchor="lm")
    d.rectangle((bb[0]-3,bb[1]-2,bb[2]+3,bb[3]+2), fill=(255,255,255))
    d.text((x*K,y*K), t, font=f, fill=c, anchor="lm")
im.save(dst, quality=95)
