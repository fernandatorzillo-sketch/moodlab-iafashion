while ($true) {
    git add .

    git status --porcelain | ForEach-Object {
        if ($_ -notmatch "data_models/orders_vtex_24m.json") {
            git commit -m "auto update" 2>$null
            git push origin main
        }
    }

    Start-Sleep -Seconds 60
}