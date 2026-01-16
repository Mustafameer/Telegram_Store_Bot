# تشغيل بوت شحن الهاتف المحمول - السرفر المحلي
# Mobile Recharge Bot - Local Server Startup

# تعيين الترميز الصحيح
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

# الألوان
$colors = @{
    Success = 'Green'
    Error = 'Red'
    Warning = 'Yellow'
    Info = 'Cyan'
}

function Write-Status {
    param(
        [string]$Message,
        [string]$Type = 'Info'
    )
    $color = $colors[$Type]
    Write-Host $Message -ForegroundColor $color
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Magenta
Write-Host "  🤖 بوت شحن الهاتف المحمول" -ForegroundColor Magenta
Write-Host "  Mobile Recharge Bot" -ForegroundColor Magenta
Write-Host "============================================" -ForegroundColor Magenta
Write-Host ""

# التحقق من Python
Write-Status "✓ التحقق من Python..." -Type Info

try {
    $pythonVersion = python --version 2>&1
    Write-Status "✓ $pythonVersion" -Type Success
} catch {
    Write-Status "✗ Python غير مثبت!" -Type Error
    exit 1
}

# تحديد المسار
$projectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Write-Status "✓ مسار المشروع: $projectPath" -Type Info

# التحقق من .env
if (-not (Test-Path "$projectPath\.env")) {
    Write-Status "✗ ملف .env غير موجود!" -Type Error
    Write-Status "  Copy .env.example to .env" -Type Info
    exit 1
}
Write-Status "✓ ملف الإعدادات موجود" -Type Success

# التحقق من requirements.txt
if (-not (Test-Path "$projectPath\requirements.txt")) {
    Write-Status "✗ ملف requirements.txt غير موجود!" -Type Error
    exit 1
}
Write-Status "✓ ملف المتطلبات موجود" -Type Success

# تثبيت المتطلبات (إذا لم تُثبّت)
Write-Host ""
Write-Status "♦ التحقق من المتطلبات..." -Type Info

$missingPackages = @()
$requiredPackages = @('python-telegram-bot', 'requests', 'python-dotenv', 'Flask', 'Gunicorn', 'Werkzeug')

foreach ($package in $requiredPackages) {
    try {
        pip show $package > $null 2>&1
        Write-Status "  ✓ $package" -Type Success
    } catch {
        $missingPackages += $package
    }
}

if ($missingPackages.Count -gt 0) {
    Write-Status "⚠ تثبيت المتطلبات المفقودة..." -Type Warning
    pip install -q -r "$projectPath\requirements.txt"
    Write-Status "✓ تم تثبيت المتطلبات" -Type Success
} else {
    Write-Status "✓ جميع المتطلبات مثبتة" -Type Success
}

# عرض معلومات السرفر
Write-Host ""
Write-Host "============================================" -ForegroundColor Magenta
Write-Host "  📡 معلومات السرفر المحلي" -ForegroundColor Magenta
Write-Host "============================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "🌐 عنوان IP:      192.168.0.108" -ForegroundColor Cyan
Write-Host "🔌 المنفذ:        8000" -ForegroundColor Cyan
Write-Host "📍 Webhook URL:   http://192.168.0.108:8000/webhook" -ForegroundColor Cyan
Write-Host "💾 قاعدة البيانات: bot_data.db (SQLite)" -ForegroundColor Cyan
Write-Host ""

# تشغيل البوت
Write-Status "⏳ جاري تشغيل البوت..." -Type Info
Write-Host ""

Set-Location $projectPath
python start_server.py

Write-Status "✗ توقف السرفر!" -Type Error
