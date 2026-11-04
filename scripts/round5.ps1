<#
.SYNOPSIS
    Round 5: oracle phenotype-routing test (Chapter 2 feasibility gate), 6 variants x 3 seeds, as a job queue.

.DESCRIPTION
    Runs at most -MaxParallel jobs at a time in the background of this window; each job's output goes to
    logs\round5_<job>.log. Every job is resumable (finished folds / subjects are skipped), so the script can be
    started again after an interruption. Start it from a PowerShell window in which "conda activate torch-gpu"
    has been run.

.EXAMPLE
    conda activate torch-gpu
    Set-ExecutionPolicy -Scope Process Bypass
    .\scripts\round5.ps1 -Smoke              # a few minutes, writes to results_smoke\
    .\scripts\round5.ps1                     # the real run
    .\scripts\round5.ps1 -Report             # tables after all jobs finished
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
if ($Smoke) { $Common += @('--subjects', '1', '2', '--max-epochs', '1') }

$Variants = @('phen_split', 'rand_split', 'wrong_split', 'phen_knn', 'rand_knn', 'phen_cond')

if ($Report) {
    $Ref = if ($Smoke) { 'oracle_rand_split' } else { 'eegnet' }     # the baseline has no smoke results
    $m = @($Ref)
    foreach ($v in $Variants) { $m += "oracle_$v" }
    & $Py scripts\compare_methods.py --protocol loso --reference $Ref --results-dir $ResultsDir --methods @m --out "$ResultsDir\compare_oracle_routing.md"
    exit
}

# job list: every variant for seeds 0, 1, 2
$Jobs = [ordered]@{}
foreach ($s in 0, 1, 2) {
    foreach ($v in $Variants) { $Jobs["${v}_seed$s"] = @('-u', 'scripts\run_oracle_routing.py', '--variant', $v, '--seed', "$s") + $Common }
}

$running = @{}
$failed = @()
foreach ($name in $Jobs.Keys) {
    while ((@($running.Values | Where-Object { -not $_.HasExited })).Count -ge $MaxParallel) { Start-Sleep -Seconds 20 }
    $log = "logs\round5_$name.log"
    Write-Host "$(Get-Date -Format 'HH:mm') start $name  (log $log)" -ForegroundColor Cyan
    $p = Start-Process -FilePath $Py -ArgumentList $Jobs[$name] -NoNewWindow -PassThru `
         -RedirectStandardOutput $log -RedirectStandardError "logs\round5_$name.err.log"
    $null = $p.Handle
    $running[$name] = $p
}
foreach ($name in $running.Keys) {
    $running[$name].WaitForExit()
    if ($running[$name].ExitCode -ne 0) { $failed += $name }
}
if ($failed.Count -gt 0) {
    Write-Host "FAILED: $($failed -join ', ')  (see logs\round5_<job>.err.log; re-run this script to resume)" -ForegroundColor Red
} else {
    Write-Host "ALL JOBS FINISHED $(Get-Date -Format 'yyyy-MM-dd HH:mm'). Next: .\scripts\round5.ps1 -Report$(if ($Smoke) {' -Smoke'})" -ForegroundColor Green
}
