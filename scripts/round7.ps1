<#
.SYNOPSIS
    Round 7: repetition-consistency routing over subject-bagged experts (+ RAPL), 3 seeds, as a job queue.

.DESCRIPTION
    Runs at most -MaxParallel jobs at a time in the background of this window; each job's output goes to
    logs\round7_<job>.log. Every job is resumable (finished folds / subjects are skipped), so the script can be
    started again after an interruption. Start it from a PowerShell window in which "conda activate torch-gpu"
    has been run.

.EXAMPLE
    conda activate torch-gpu
    Set-ExecutionPolicy -Scope Process Bypass
    .\scripts\round7.ps1 -Smoke              # a few minutes, writes to results_smoke\
    .\scripts\round7.ps1                     # the real run
    .\scripts\round7.ps1 -Report             # tables after all jobs finished
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
if ($Smoke) { $Common += @('--subjects', '2', '18', '--max-epochs', '1', '--n-bagged', '2') }

if ($Report) {
    $m = @('rcr_full', 'rcr_random', 'rcr_uniform', 'rcr_top1', 'rcr_top3', 'rcr_soft', 'rcr_oracle',
           'rcr_full_rapl', 'rcr_top1_rapl', 'rcr_top3_rapl')
    & $Py scripts\compare_methods.py --protocol loso --reference rcr_full --results-dir $ResultsDir --methods @m --out "$ResultsDir\compare_rcr.md"
    & $Py scripts\compare_methods.py --protocol loso --reference rcr_full_rapl --results-dir $ResultsDir --methods @m --out "$ResultsDir\compare_rcr_vs_rapl.md"
    exit
}

# 3 seeds x 2 halves of the subjects (separate output files per subject, so the halves never collide)
$Halves = @{ 'a' = @('1','2','3','4','5','6','7','8','9','10','11','12','13','14');
             'b' = @('15','16','17','18','19','20','21','22','23','24','25','26','27','28') }
$Jobs = [ordered]@{}
foreach ($s in 0, 1, 2) {
    foreach ($h in 'a', 'b') {
        $subj = if ($Smoke) { @() } else { @('--subjects') + $Halves[$h] }
        if ($Smoke -and $h -eq 'b') { continue }
        $Jobs["rcr_seed${s}_$h"] = @('-u', 'scripts\run_rcr.py', '--seed', "$s") + $Common + $subj
    }
}

$running = @{}
$failed = @()
foreach ($name in $Jobs.Keys) {
    while ((@($running.Values | Where-Object { -not $_.HasExited })).Count -ge $MaxParallel) { Start-Sleep -Seconds 20 }
    $log = "logs\round7_$name.log"
    Write-Host "$(Get-Date -Format 'HH:mm') start $name  (log $log)" -ForegroundColor Cyan
    $p = Start-Process -FilePath $Py -ArgumentList $Jobs[$name] -NoNewWindow -PassThru `
         -RedirectStandardOutput $log -RedirectStandardError "logs\round7_$name.err.log"
    $null = $p.Handle
    $running[$name] = $p
}
foreach ($name in $running.Keys) {
    $running[$name].WaitForExit()
    if ($running[$name].ExitCode -ne 0) { $failed += $name }
}
if ($failed.Count -gt 0) {
    Write-Host "FAILED: $($failed -join ', ')  (see logs\round7_<job>.err.log; re-run this script to resume)" -ForegroundColor Red
} else {
    Write-Host "ALL JOBS FINISHED $(Get-Date -Format 'yyyy-MM-dd HH:mm'). Next: .\scripts\round7.ps1 -Report$(if ($Smoke) {' -Smoke'})" -ForegroundColor Green
}
