@echo off
rem Launcher for the U.S. Census Bureau Data API MCP server (no Docker).
rem Reads CENSUS_API_KEY from C:\Users\aphil\Documents\Census\.env
for /f "usebackq eol=# tokens=1,* delims==" %%a in ("C:\Users\aphil\Documents\Census\.env") do set "%%a=%%b"
node "C:\Users\aphil\Documents\Census\us-census-bureau-data-api-mcp\mcp-server\dist\index.js"
