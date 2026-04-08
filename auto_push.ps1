while ($true) {
    git add .
    git commit -m "auto update" 2>$null
    git push origin main
    Start-Sleep -Seconds 60
}