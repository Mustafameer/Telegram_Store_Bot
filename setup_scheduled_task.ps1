# PowerShell script لإنشاء Scheduled Task للبوت
# شغّل هذا Script بصلاحيات Admin

# المتغيرات
$taskName = "TelegramStoreBot"
$scriptPath = "C:\Users\Hp\Desktop\TelegramStoreBot\run_bot_background.bat"
$botPath = "C:\Users\Hp\Desktop\TelegramStoreBot\bot.py"
$pythonPath = "python.exe"
$workingDir = "C:\Users\Hp\Desktop\TelegramStoreBot"

# حذف Task قديمة إذا كانت موجودة
Write-Host "حذف Task القديمة (إن وجدت)..."
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

# إنشاء Trigger (عند بدء التشغيل)
$trigger = New-ScheduledTaskTrigger -AtStartup

# إنشاء Action (تشغيل البوت)
$action = New-ScheduledTaskAction -Execute $pythonPath -Argument $botPath -WorkingDirectory $workingDir

# إنشاء Settings
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable

# إنشاء Task
Write-Host "إنشاء Scheduled Task..."
Register-ScheduledTask -TaskName $taskName `
    -Trigger $trigger `
    -Action $action `
    -Settings $settings `
    -Description "Telegram Store Bot - يعمل عند بدء التشغيل" `
    -RunLevel Highest `
    -Force

Write-Host "✅ تم إنشاء Task بنجاح!"
Write-Host "اسم Task: $taskName"
Write-Host "سيتم تشغيل البوت تلقائياً عند بدء Windows"
