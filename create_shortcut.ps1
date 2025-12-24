$WshShell = New-Object -comObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$Shortcut = $WshShell.CreateShortcut("$DesktopPath\Telegram Store Bot.lnk")
$Shortcut.TargetPath = "c:\Users\Hp\Desktop\TelegramStoreBot\start_bot.bat"
$Shortcut.WorkingDirectory = "c:\Users\Hp\Desktop\TelegramStoreBot"
$Shortcut.Description = "Start the Telegram Store Bot"
$Shortcut.Save()
Write-Host "Shortcut created at $DesktopPath\Telegram Store Bot.lnk"
