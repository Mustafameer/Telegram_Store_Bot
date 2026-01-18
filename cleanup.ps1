# Delete images, messages, and orders from database
$env:DATABASE_URL = 'postgresql://postgres:bqcTJxNXLgwOftDoarrtmjmjYWurEIEh@switchback.proxy.rlwy.net:20266/railway'

Write-Host "Deleting images, messages, and orders from database..."
Write-Host ""

python delete_data_now.py

Write-Host ""
Write-Host "Done!"
