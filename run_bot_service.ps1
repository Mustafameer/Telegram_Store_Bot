# PowerShell Script لتشغيل البوت مع Service Wrapper
# بدون الحاجة لـ .\ prefix

$botDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $botDir

Write-Host ""
Write-Host "========================================"
Write-Host "   🤖 Telegram Store Bot Service"
Write-Host "========================================"
Write-Host ""
Write-Host "البوت يعمل الآن في الخلفية..."
Write-Host "سيتم إعادة تشغيله تلقائياً عند التعطل"
Write-Host ""
Write-Host "لإيقاف البوت: اضغط Ctrl + C"
Write-Host ""
Write-Host "========================================"
Write-Host ""

# تشغيل البوت عبر Service Wrapper
& python.exe service_wrapper.py

Write-Host ""
Write-Host "تم إيقاف البوت"
Write-Host ""
