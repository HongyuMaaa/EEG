<#
.SYNOPSIS
    Round 8: repetition-consistency routing with RED-trained experts (+ RAPL), 3 seeds, as a job queue.

.DESCRIPTION
    Runs at most -MaxParallel jobs at a time in the background of this window; each job's output goes to
    logs\round8_<job>.log. Every job is resumable (finished folds / subjects are skipped), so the script can be
    started again after an interruption. Start it from a PowerShell window in which "conda activate torch-gpu"
    has been run.

.EXAMPLE
    conda activate torch-gpu
    Set-ExecutionPolicy -Scope Process Bypass
    .\scripts\round8.ps1 -Smoke              # a few minutes, writes to results_smoke\
    .\scripts\round8.ps1                     # the real run
    .\scripts\round8.ps1 -Report             # tables after all jobs finished
    .\scripts\round8.ps1 -MaxParallel 3 -MaxVramGB 4    # gentler: 3 jobs sharing at most ~4 GB of GPU memory

.PARAMETER MaxVramGB
    Total GPU memory budget in GB for all jobs together. Each job gets MaxVramGB / MaxParallel, minus ~0.5 GB
    reserved for its CUDA context (which PyTorch cannot cap), as a hard per-process limit (--max-vram-gb).
    A job that would need more stops with an out-of-memory error instead of slowing the computer down;
    about 1 GB per job is enough for these models. Jobs also run at below-normal CPU priority.
#>
param(
    [int]$MaxParallel = 6,
    [switch]$Smoke,
    [switch]$Report,
    [string]$Device = 'cuda',
    [string]$Python = '',
    [double]$MaxVramGB = 0
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
if ($MaxVramGB -gt 0) {
    $perJob = [math]::Max(0.5, $MaxVramGB / $MaxParallel - 0.5)
    $perJobText = $perJob.ToString('0.00', [System.Globalization.CultureInfo]::InvariantCulture)
    Write-Host "GPU memory: $MaxVramGB GB total for $MaxParallel parallel jobs -> limit $perJobText GB per job (+ CUDA context)" -ForegroundColor Yellow
    $Common += @('--max-vram-gb', $perJobText)
}
if ($Smoke) { $Common += @('--subjects', '2', '18', '--max-epochs', '1', '--n-bagged', '2') }

if ($Report) {
    $m = @()
    foreach ($v in 'full', 'uniform', 'top1', 'top3', 'soft', 'oracle', 'full_rapl', 'top1_rapl', 'top3_rapl') {
        $m += "rcr_$v"; $m += "rcr_red_$v"
    }
    if ($Smoke) {   # round-7 (EEGNet-expert) results exist only in results\
        & $Py scripts\compare_methods.py --protocol loso --reference rcr_red_full --results-dir $ResultsDir --methods @m
        exit
    }
    & $Py scripts\compare_methods.py --protocol loso --reference rcr_full --results-dir $ResultsDir --methods @m --out "$ResultsDir\compare_rcr_red.md"
    & $Py scripts\compare_methods.py --protocol loso --reference rcr_top3_rapl --results-dir $ResultsDir --methods @m --out "$ResultsDir\compare_rcr_red_vs_best.md"
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
        $Jobs["rcr_red_seed${s}_$h"] = @('-u', 'scripts\run_rcr.py', '--expert', 'red', '--seed', "$s") + $Common + $subj
    }
}

$running = @{}
$failed = @()
foreach ($name in $Jobs.Keys) {
    while ((@($running.Values | Where-Object { -not $_.HasExited })).Count -ge $MaxParallel) { Start-Sleep -Seconds 20 }
    $log = "logs\round8_$name.log"
    Write-Host "$(Get-Date -Format 'HH:mm') start $name  (log $log)" -ForegroundColor Cyan
    $p = Start-Process -FilePath $Py -ArgumentList $Jobs[$name] -NoNewWindow -PassThru `
         -RedirectStandardOutput $log -RedirectStandardError "logs\round8_$name.err.log"
    $null = $p.Handle
    try { $p.PriorityClass = [System.Diagnostics.ProcessPriorityClass]::BelowNormal } catch { }   # keep the desktop responsive
    $running[$name] = $p
}
foreach ($name in $running.Keys) {
    $running[$name].WaitForExit()
    if ($running[$name].ExitCode -ne 0) { $failed += $name }
}
if ($failed.Count -gt 0) {
    foreach ($name in $failed) {
        Write-Host "--- $name (last lines of logs\round8_$name.err.log):" -ForegroundColor Red
        Get-Content "logs\round8_$name.err.log" -Tail 6 -ErrorAction SilentlyContinue | ForEach-Object { Write-Host "    $_" }
    }
    Write-Host "FAILED: $($failed -join ', ')  (see logs\round8_<job>.err.log; re-run this script to resume)" -ForegroundColor Red
} else {
    Write-Host "ALL JOBS FINISHED $(Get-Date -Format 'yyyy-MM-dd HH:mm'). Next: .\scripts\round8.ps1 -Report$(if ($Smoke) {' -Smoke'})" -ForegroundColor Green
}
