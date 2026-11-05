<#
.SYNOPSIS
    Round 6: label-free phenotype routing (+ RAPL), 3 seeds, as a job queue.

.DESCRIPTION
    Runs at most -MaxParallel jobs at a time in the background of this window; each job's output goes to
    logs\round6_<job>.log. Every job is resumable (finished folds / subjects are skipped), so the script can be
    started again after an interruption. Start it from a PowerShell window in which "conda activate torch-gpu"
    has been run.

.EXAMPLE
    conda activate torch-gpu
    Set-ExecutionPolicy -Scope Process Bypass
    .\scripts\round6.ps1 -Smoke              # a few minutes, writes to results_smoke\
    .\scripts\round6.ps1                     # the real run
    .\scripts\round6.ps1 -Report             # tables after all jobs finished
#>
param(
    [int]$MaxParallel = 6,
    [switch]$Smoke,
    [switch]$Report,
    [string]$Device = 'cuda',
    [string]$Python = ''
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
New-Item -ItemType Directory -Force -Path (Join-Path $Root 'logs') | Out-Null

if ($Python) { $Py = $Python }
elseif ($env:CONDA_PREFIX -and (Test-Path (Join-Path $env:CONDA_PREFIX 'python.exe'))) { $Py = Join-Path $env:CONDA_PREFIX 'python.exe' }
else { $Py = (Get-Command python).Source }
Write-Host "Python: $Py" -ForegroundColor Yellow
& $Py -c 'import torch; print(torch.__version__, torch.cuda.is_available())'

$ResultsDir = if ($Smoke) { 'results_smoke' } else { 'results' }
$Common = @('--device', $Device, '--results-dir', $ResultsDir)
if ($Smoke) { $Common += @('--subjects', '2', '18', '--max-epochs', '1') }

if ($Report) {
    $m = @('est_full', 'est_full_rapl', 'est_knn', 'est_knn_rapl', 'est_oracle_knn', 'est_rand_knn')
    & $Py scripts\compare_methods.py --protocol loso --reference est_full --results-dir $ResultsDir --methods @m --out "$ResultsDir\compare_est_routing.md"
    & $Py scripts\compare_methods.py --protocol loso --reference est_full_rapl --results-dir $ResultsDir --methods @m --out "$ResultsDir\compare_est_routing_vs_rapl.md"
    exit
}

# one job per seed (each trains 4 models per subject: source, estimated-kNN, oracle-kNN, random-kNN)
$Jobs = [ordered]@{}
foreach ($s in 0, 1, 2) { $Jobs["est_seed$s"] = @('-u', 'scripts\run_est_routing.py', '--seed', "$s") + $Common }

$running = @{}
$failed = @()
foreach ($name in $Jobs.Keys) {
    while ((@($running.Values | Where-Object { -not $_.HasExited })).Count -ge $MaxParallel) { Start-Sleep -Seconds 20 }
    $log = "logs\round6_$name.log"
    Write-Host "$(Get-Date -Format 'HH:mm') start $name  (log $log)" -ForegroundColor Cyan
    $p = Start-Process -FilePath $Py -ArgumentList $Jobs[$name] -NoNewWindow -PassThru `
         -RedirectStandardOutput $log -RedirectStandardError "logs\round6_$name.err.log"
    $null = $p.Handle
    $running[$name] = $p
}
foreach ($name in $running.Keys) {
    $running[$name].WaitForExit()
    if ($running[$name].ExitCode -ne 0) { $failed += $name }
}
if ($failed.Count -gt 0) {
    Write-Host "FAILED: $($failed -join ', ')  (see logs\round6_<job>.err.log; re-run this script to resume)" -ForegroundColor Red
} else {
    Write-Host "ALL JOBS FINISHED $(Get-Date -Format 'yyyy-MM-dd HH:mm'). Next: .\scripts\round6.ps1 -Report$(if ($Smoke) {' -Smoke'})" -ForegroundColor Green
}
