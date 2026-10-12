<#
.SYNOPSIS
    Attiva le variabili d'ambiente per la demo solo nel terminale corrente (Scope Process).
.DESCRIPTION
    Legge il file .env del progetto e carica le variabili (inclusa GOOGLE_API_KEY)
    esclusivamente nella sessione PowerShell attiva, senza modificare il sistema Windows.
#>

$rootPath = Resolve-Path "$PSScriptRoot\.."
$envFile = Join-Path $rootPath ".env"

if (-not (Test-Path $envFile)) {
    Write-Error "File .env non trovato in $rootPath"
    return
}

$loadedCount = 0
Get-Content $envFile | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
        $parts = $line.Split("=", 2)
        $key = $parts[0].Trim()
        $val = $parts[1].Trim().Trim('"').Trim("'")
        if ($key -and $val) {
            # Imposta la variabile d'ambiente solo nel processo corrente
            [System.Environment]::SetEnvironmentVariable($key, $val, [System.EnvironmentVariableTarget]::Process)
            Set-Item -Path "Env:$key" -Value $val
            $loadedCount++
        }
    }
}

Write-Host "[OK] Ambiente demo attivato nel terminale corrente ($loadedCount variabili caricate da .env)." -ForegroundColor Green
if ($env:GOOGLE_API_KEY) {
    Write-Host "     GOOGLE_API_KEY: $($env:GOOGLE_API_KEY.Substring(0, [Math]::Min(12, $env:GOOGLE_API_KEY.Length)))... (attiva)" -ForegroundColor Yellow
}
