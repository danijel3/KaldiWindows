pyinstaller -F --onefile main.py

move dist\main.exe main.exe

rd /s /q dist
rd /s /q build