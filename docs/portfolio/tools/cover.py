from PIL import Image, ImageDraw, ImageFilter, ImageFont
import sys
from pathlib import Path
S=Path(sys.argv[1]); OUT=Path(sys.argv[2])
INTER="/usr/share/fonts/opentype/inter/Inter-{}.otf"; SERIF="/home/claude/work/fonts/InstrumentSerif-Italic.ttf"
def f(w,s): return ImageFont.truetype(INTER.format(w),s)
def rounded(im,r):
    m=Image.new("L",im.size,0); ImageDraw.Draw(m).rounded_rectangle((0,0,*im.size),r,fill=255); out=im.convert("RGBA"); out.putalpha(m); return out
def make(W,H,name,lang="pt"):
    bg=Image.open(S/"landing-ready-to-fly.jpg").convert("RGB")
    # sky area only: crop the upper band without the headline, then scale
    left=bg.crop((0,470,590,674)); right=bg.crop((770,470,1355,674))
    band=Image.new("RGB",(590+585-60,204)); band.paste(left,(0,0));
    m=Image.linear_gradient("L").rotate(90).resize((60,204)).transpose(Image.FLIP_LEFT_RIGHT)
    rpart=right.copy(); band.paste(rpart,(530,0)); band.paste(left.crop((530,0,590,204)),(530,0),Image.linear_gradient("L").rotate(-90).resize((60,204)))
    sky=band.resize((W,int(H*0.40)),Image.LANCZOS)
    grad=Image.linear_gradient("L").resize((W,H))
    c1=Image.new("RGB",(W,H),"#2a63c9"); c2=Image.new("RGB",(W,H),"#7fb0ea"); canvas=Image.composite(c2,c1,grad)
    fm=Image.linear_gradient("L").resize(sky.size).point(lambda v: min(255,v*3)); canvas.paste(sky,(0,H-sky.size[1]),fm)
    d=ImageDraw.Draw(canvas)
    # dashboard card on the right
    shot=Image.open(S/"dashboard-overview-kpis.jpg").convert("RGB")
    cw=int(W*0.47); ch=int(cw*shot.size[1]/shot.size[0]); card=rounded(shot.resize((cw,ch),Image.LANCZOS),18)
    x0=W-cw-int(W*0.035); y0=int(H*0.12)
    sh=Image.new("RGBA",(cw+60,ch+60),(0,0,0,0)); ImageDraw.Draw(sh).rounded_rectangle((30,36,cw+30,ch+36),22,fill=(10,30,70,110))
    sh=sh.filter(ImageFilter.GaussianBlur(16)); canvas.paste(sh,(x0-30,y0-30),sh); canvas.paste(card,(x0,y0),card)
    # analyst card overlapping
    an=Image.open(S/"analyst-live-busiest-airports.jpg").convert("RGB").crop((290,70,875,545))
    aw=int(W*0.24); ah=int(aw*an.size[1]/an.size[0]); acard=rounded(an.resize((aw,ah),Image.LANCZOS),14)
    ax0=W-aw-int(W*0.02); ay0=y0+ch-int(ah*0.30)
    sh=Image.new("RGBA",(aw+60,ah+60),(0,0,0,0)); ImageDraw.Draw(sh).rounded_rectangle((30,36,aw+30,ah+36),18,fill=(10,30,70,120))
    sh=sh.filter(ImageFilter.GaussianBlur(14)); canvas.paste(sh,(ax0-30,ay0-30),sh); canvas.paste(acard,(ax0,ay0),acard)
    # text
    L=int(W*0.045); y=int(H*0.12)
    d.text((L,y),"ANAC  FLIGHT  INTELLIGENCE",font=f("SemiBold",int(H*0.026)),fill=(225,236,252)); y+=int(H*0.06)
    big=f("Bold",int(H*0.078)); d.text((L,y),"Aviação brasileira" if lang=="pt" else "Brazilian aviation",font=big,fill="white"); y+=int(H*0.09)
    serif=ImageFont.truetype(SERIF,int(H*0.095))
    d.text((L,y-int(H*0.01)),"em dados" if lang=="pt" else "in data,",font=serif,fill="white")
    w2=d.textlength("em dados " if lang=="pt" else "in data, ",font=serif)
    d.text((L+w2,y),"verificáveis." if lang=="pt" else "verified.",font=big,fill="white"); y+=int(H*0.125)
    sub=("22,1 milhões de etapas de voo, 2000–2025\nModelos comparados a baselines · AI Analyst" if lang=="pt" else "22.1M flight legs, 2000–2025\nModels tested against baselines · AI analyst")
    small=f("Medium",int(H*0.026)); d.multiline_text((L,y),sub,font=small,fill=(235,243,255),spacing=int(H*0.012)); y+=int(H*0.12)
    chips=(["Python · Polars · DuckDB","LightGBM","FastAPI · Next.js","Groq"] )
    cx=L; cf=f("SemiBold",int(H*0.024))
    for t in chips:
        tw=d.textlength(t,font=cf); pad=int(H*0.018)
        d.rounded_rectangle((cx,y,cx+tw+2*pad,y+int(H*0.052)),int(H*0.026),fill=(255,255,255,255),outline=None)
        d.text((cx+pad,y+int(H*0.011)),t,font=cf,fill="#1d3f8f"); cx+=tw+2*pad+int(H*0.014)
        if cx>W*0.33: cx=L; y+=int(H*0.066)
    foot=f("Medium",int(H*0.024))
    d.text((L,H-int(H*0.075)),"anac-flight-intelligence-api-main.vercel.app",font=foot,fill="#1d3f8f")
    canvas.save(OUT/name,quality=92); print(name,canvas.size)
make(1280,640,"cover-github-1280x640.jpg","pt")
make(1200,627,"linkedin-post-1200x627.jpg","pt")
make(1280,640,"cover-github-1280x640-en.jpg","en")
