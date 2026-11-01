<#
.SYNOPSIS
    Round 4: RAPL (C2.2-C2.3, 3 seeds) and LR-MoE with ablations (C2.1, seed 0) as a job queue.

.DESCRIPTION
    Runs at most -MaxParallel jobs at a time in the background of this window; each job's output goes to
    logs\round4_<job>.log. Every job is resumable (finished folds / subjects are skipped), so the script can be
    started again after an interruption. Start it from a PowerShell window in which "conda activate torch-gpu"
    has been run.

.EXAMPLE
    conda activate torch-gpu
    Set-ExecutionPolicy -Scope Process Bypass
    .\scripts\round4.ps1 -Smoke              # a few minutes, writes to results_smoke\
    .\scripts\round4.ps1                     # the real run
    .\scripts\round4.ps1 -Report             # tables after all jobs finished
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

$Moe = @('lrmoe', 'eegnet_sz', 'eegnet_mirroraug', 'lrmoe_generic', 'lrmoe_nodecomp', 'lrmoe_nolat',
         'lrmoe_nocoh', 'lrmoe_anti')

if ($Report) {
    foreach ($s in 0, 1, 2) { & $Py scripts\run_rapl.py --summary-only --seed $s --results-dir $ResultsDir }
    $m = @()
    foreach ($v in $Moe) { $m += $v; $m += "${v}_subjgate" }
    & $Py scripts\compare_methods.py --protocol loso --reference eegnet_sz --results-dir $ResultsDir --methods @m --out "$ResultsDir\compare_loso_moe.md"
    exit
}

# job list in priority order: name -> arguments
$Jobs = [ordered]@{}
$Jobs['moe_lrmoe'] = @('-u', 'scripts\run_moe.py', '--method', 'lrmoe') + $Common
$Jobs['moe_eegnet_sz'] = @('-u', 'scripts\run_moe.py', '--method', 'eegnet_sz') + $Common
foreach ($s in 0, 1, 2) { $Jobs["rapl_seed$s"] = @('-u', 'scripts\run_rapl.py', '--seed', "$s") + $Common }
foreach ($v in $Moe[2..($Moe.Count - 1)]) { $Jobs["moe_$v"] = @('-u', 'scripts\run_moe.py', '--method', $v) + $Common }

$running = @{}
$failed = @()
foreach ($name in $Jobs.Keys) {
    while ((@($running.Values | Where-Object { -not $_.HasExited })).Count -ge $MaxParallel) { Start-Sleep -Seconds 20 }
    $log = "logs\round4_$name.log"
    Write-Host "$(Get-Date -Format 'HH:mm') start $name  (log $log)" -ForegroundColor Cyan
    $p = Start-Process -FilePath $Py -ArgumentList $Jobs[$name] -NoNewWindow -PassThru `
         -RedirectStandardOutput $log -RedirectStandardError "logs\round4_$name.err.log"
    $null = $p.Handle
    $running[$name] = $p
}
foreach ($name in $running.Keys) {
    $running[$name].WaitForExit()
    if ($running[$name].ExitCode -ne 0) { $failed += $name }
}
if ($failed.Count -gt 0) {
    Write-Host "FAILED: $($failed -join ', ')  (see logs\round4_<job>.err.log; re-run this script to resume)" -ForegroundColor Red
} else {
    Write-Host "ALL JOBS FINISHED $(Get-Date -Format 'yyyy-MM-dd HH:mm'). Next: .\scripts\round4.ps1 -Report$(if ($Smoke) {' -Smoke'})" -ForegroundColor Green
}
