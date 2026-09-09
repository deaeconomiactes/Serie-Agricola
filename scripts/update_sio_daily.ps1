$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repoRoot

$startedAt = Get-Date
Write-Host "Inicio actualización diaria SIO: $($startedAt.ToString('yyyy-MM-dd HH:mm:ss zzz'))"

$steps = @(
    @{ Name = "Capturar snapshot latest"; Arguments = @(".\explorar_sio_granos.py", "--update-latest", "--allow-web", "--save-response") },
    @{ Name = "Integrar snapshot e histórico"; Arguments = @(".\integrar_commodities_sio.py") },
    @{ Name = "Auditar actualización y calidad"; Arguments = @(".\auditar_commodities_sio.py") },
    @{ Name = "Regenerar agregados dashboard-ready"; Arguments = @(".\preparar_commodities_dashboard.py") }
)

foreach ($step in $steps) {
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $($step.Name)..."
    & python @($step.Arguments)
    if ($LASTEXITCODE -ne 0) {
        throw "El paso '$($step.Name)' terminó con código $LASTEXITCODE."
    }
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $($step.Name): OK"
}

$finishedAt = Get-Date
Write-Host "Fin actualización diaria SIO: $($finishedAt.ToString('yyyy-MM-dd HH:mm:ss zzz'))"
Write-Host "Duración: $((New-TimeSpan -Start $startedAt -End $finishedAt).ToString())"
