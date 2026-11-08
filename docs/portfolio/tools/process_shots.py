from PIL import Image
from pathlib import Path
import sys
src=Path('/home/claude/shots'); out=Path(sys.argv[1]); out.mkdir(parents=True,exist_ok=True)
cursor={'01':None,'02':None,'03':(130,431),'04':(130,430),'05':(130,431),'06':(130,431),'07':(130,431),
 '08':(130,431),'09':(130,431)}
for n in range(10,19): cursor[f'{n:02d}']=(130,300)
names={
'01-landing':'landing-ready-to-fly','02-overview-kpis':'dashboard-overview-kpis','03-overview-charts':'dashboard-monthly-passengers-top-routes',
'04-overview-airports-models':'dashboard-busiest-airports-models','05-overview-night':'dashboard-overview-night',
'06-routes-monthly':'routes-explorer-monthly','07-routes-ranking':'routes-explorer-ranking','08-airports-gru-monthly':'airports-gru-monthly',
'09-airports-ranking':'airports-ranking','10-mlstudio-top':'ml-studio-overview','11-mlstudio-a-actual-vs-pred':'ml-studio-a-actual-vs-predicted',
'12-mlstudio-d-summary':'ml-studio-d-route-demand-summary','13-mlstudio-d-actual-vs-pred':'ml-studio-d-actual-vs-predicted',
'14-mlstudio-d-error-analysis':'ml-studio-d-error-analysis','15-mlstudio-model-registry':'ml-studio-model-registry',
'16-analyst-live-answer':'analyst-live-busiest-airports','17-analyst-verified-cases':'analyst-verified-cases','18-analyst-night':'analyst-live-night',
'19-mobile-overview':'mobile-overview','20-mobile-charts':'mobile-charts','21-mobile-mlstudio-night':'mobile-ml-studio-night'}
for f in sorted(src.glob('*.jpg')):
    key=f.stem[:2]; im=Image.open(f).convert('RGB'); w,h=im.size
    c=cursor.get(key)
    if c:
        x,y=c; box=(x-4,y-4,x+18,y+26)
        from PIL import ImageFilter
        pad=8; big=(box[0]-pad,box[1]-pad,box[2]+pad,box[3]+pad)
        patch=im.crop((big[0],big[1]-44,big[2],big[3]-44))
        mask=Image.new('L',patch.size,0); mask.paste(255,(3,3,patch.size[0]-3,patch.size[1]-3))
        mask=mask.filter(ImageFilter.GaussianBlur(2)); im.paste(patch,big[:2],mask)
    if w==1375: im=im.crop((0,0,1366 if key in('01','02') else 1375,h))
    if w==502: im=im.crop((0,0,494,h))
    dest=out/(names[f.stem]+'.jpg'); im.save(dest,quality=90,optimize=True,progressive=True); print(dest.name, im.size, dest.stat().st_size//1024,'KB')
