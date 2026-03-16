@echo off
echo Installing libraries...
python -m pip install customtkinter requests pyinstaller Pillow --quiet

echo.
echo Generating car icon...
python -c "from PIL import Image,ImageDraw; size=64; img=Image.new('RGBA',(size,size),(0,0,0,0)); d=ImageDraw.Draw(img); d.rounded_rectangle([4,26,60,50],radius=7,fill='#3b82f6'); d.polygon([(15,26),(20,12),(44,12),(49,26)],fill='#1d4ed8'); d.polygon([(42,25),(47,25),(43,13),(35,13)],fill='#93c5fd'); d.polygon([(17,25),(22,25),(26,13),(18,13)],fill='#93c5fd'); d.ellipse([8,44,28,60],fill='#1e293b'); d.ellipse([36,44,56,60],fill='#1e293b'); d.ellipse([14,49,22,56],fill='#94a3b8'); d.ellipse([42,49,50,56],fill='#94a3b8'); d.ellipse([52,32,61,40],fill='#fde68a'); d.ellipse([3,32,11,40],fill='#ef4444'); img.save('car.ico',format='ICO',sizes=[(64,64),(32,32),(16,16)]); print('car.ico OK')"

echo.
echo Cleaning old build...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist car_search.spec del /q car_search.spec

echo.
echo Building EXE...
python -m PyInstaller --onedir --windowed --clean --name car_search --icon=car.ico main.py

echo.
echo ============================================
echo  Done: dist\car_search\car_search.exe
echo ============================================
pause
