# BlenderMCP Starter Script
# 1. Blender'ı başlat
# 2. BlenderMCP addon'unu etkinleştir (Edit > Preferences > Add-ons > search "blender_mcp")
# 3. Addon panelinden "Start MCP Server" butonuna bas
# 4. Bu script MCP server'ı başlatır

$BlenderDir = "C:\Blender\blender-4.4.3-windows-x64"
$MCPVenv = "C:\BlenderMCP"

Write-Host "=== Patchbay BlenderMCP ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Blender'i baslatiliyor..." -ForegroundColor Yellow
Start-Process "$BlenderDir\blender.exe"

Write-Host ""
Write-Host "2. Blender acildiktan sonra:" -ForegroundColor Yellow
Write-Host "   - Edit > Preferences > Add-ons" -ForegroundColor White
Write-Host "   - 'blender_mcp' ara ve etkinlestir" -ForegroundColor White
Write-Host "   - Sidebar (N tusu) > BlenderMCP tab'ina git" -ForegroundColor White
Write-Host "   - 'Start Server' butonuna bas (port 9876)" -ForegroundColor White
Write-Host ""
Write-Host "3. MCP server baslatiliyor (SSE port 8456)..." -ForegroundColor Yellow

& "$MCPVenv\Scripts\python.exe" -m blender_mcp.server

Write-Host ""
Write-Host "BlenderMCP hazir! Patchbay gateway port 8456 uzerinden baglanabilir." -ForegroundColor Green
