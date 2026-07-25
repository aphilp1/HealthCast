@echo off
rem PeopleWatch — start the local server (no-cache) and open the app.
rem Double-click this file any time http://localhost:8020/census.html won't load.
cd /d "C:\Users\aphil\Documents\Census"
start "PeopleWatch server" /min python serve_peoplewatch.py
timeout /t 2 /nobreak >nul
start http://localhost:8020/census.html
