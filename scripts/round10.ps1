<#
.SYNOPSIS
    Round 10 (Chapter 1, direction 1): limited-calibration study - eegnet, eegnet@ft, red_selfteacher and
    red_selfteacher@ft with only 1, 2 or 3 own training sessions, 3 seeds, as a job queue.

.DESCRIPTION
    Same folds as the main within-subject runs (test and validation session unchanged); only N of the 4 own
    training sessions are used (aved.data.limit_train_sessions: cyclic order after the validation session, nested,
    identical for every method and seed). The 4-session condition is the existing eegnet / red_selfteacher /
    *@ft results. Results: results\<method>@cal<N>\ and results\<method>@ft_cal<N>\.
    Phase 1 re-runs the round-9 cross-subject pretraining (skipped for every model that already exists in
    checkpoints\pretrain\). Phase 2 runs the calibration jobs, seed by seed, so seed 0 can be analysed first.
    Every job is resumable (finished folds are skipped). Logs: logs\round10_<job>.log.
    Start it from a PowerShell window in which "conda activate torch-gpu" has been run.

.EXAMPLE
    conda activate torch-gpu
    Set-ExecutionPolicy -Scope Process Bypass
    .\scripts\round10.ps1 -Smoke             # a few minutes, writes to results_smoke\ and checkpoints_smoke\
    .\scripts\round10.ps1                    # the real run (~110 job-hours; ~18-20 h with 6 parallel jobs)
    .\scripts\round10.ps1 -Seeds 0           # only seed 0 first (~6-7 h)
    .\scripts\round10.ps1 -Report            # tables after all jobs finished
    .\scripts\round10.ps1 -MaxParallel 3 -MaxVramGB 4

.PARAMETER MaxVramGB
    Total GPU memory budget in GB for all jobs together. Each job gets MaxVramGB / MaxParallel, minus ~0.5 GB
    reserved for its CUDA context (which PyTorch cannot cap), as a hard per-process limit (--max-vram-gb).
#>
param(
    [int]$MaxParallel = 6,
    [switch]$Smoke,
    [switch]$Report,
    [string]$Device = 'cuda',
    [string]$Python = '',
    [double]$MaxVramGB = 0,
    [int[]]$Seeds = @(0, 1, 2),
    [int[]]$NSessions = @(1, 2, 3)
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
$CkptDir = if ($Smoke) { 'checkpoints_smoke' } else { 'checkpoints' }    # smoke models never reach checkpoints\
$Common = @('--device', $Device, '--results-dir', $ResultsDir, '--checkpoint-dir', $CkptDir)
if ($MaxVramGB -gt 0) {
    $perJob = [math]::Max(0.5, $MaxVramGB / $MaxParallel - 0.5)
    $perJobText = $perJob.ToString('0.00', [System.Globalization.CultureInfo]::InvariantCulture)
    Write-Host "GPU memory: $MaxVramGB GB total for $MaxParallel parallel jobs -> limit $perJobText GB per job (+ CUDA context)" -ForegroundColor Yellow
    $Common += @('--max-vram-gb', $perJobText)
}

if ($Report) {
    foreach ($n in $NSessions) {
        $m = @("eegnet@cal$n", "eegnet@ft_cal$n", "red_selfteacher@cal$n", "red_selfteacher@ft_cal$n")
        $out = if ($Smoke) { @() } else { @('--out', "$ResultsDir\compare_round10_cal$n.md") }
        & $Py scripts\compare_methods.py --protocol within --reference "eegnet@cal$n" --results-dir $ResultsDir --methods @m @out
    }
    exit
}

$Halves = @{ 'a' = @('1','2','3','4','5','6','7','8','9','10','11','12','13','14');
             'b' = @('15','16','17','18','19','20','21','22','23','24','25','26','27','28') }
if ($Smoke) { $Seeds = @(0); $NSessions = @(1) }
$HalfNames = if ($Smoke) { @('a') } else { @('a', 'b') }
function Subjects($h) { if ($Smoke) { @('--subjects', '2') } else { @('--subjects') + $Halves[$h] } }

$Phase1 = [ordered]@{}
$Phase2 = [ordered]@{}
foreach ($s in $Seeds) {
    foreach ($h in $HalfNames) {
        $extra = if ($Smoke) { @('--max-epochs', '1') } else { @() }
        $Phase1["pretrain_seed${s}_$h"] = @('-u', 'scripts\pretrain_subjects.py', '--seed', "$s") + $Common + (Subjects $h) + $extra
    }
}
foreach ($s in $Seeds) {
    foreach ($n in $NSessions) {
        foreach ($method in 'red_selfteacher', 'eegnet') {          # RED first: the longest jobs start early
            foreach ($init in 'pretrain', 'none') {
                $tag = if ($init -eq 'pretrain') { "ft_cal$n" } else { "cal$n" }
                $extra2 = if ($Smoke) { @('--subjects', '2', '--sessions', '1', '--max-epochs', '1') } else { @() }
                $Phase2["${method}_${tag}_seed$s"] = @('-u', 'scripts\run_baseline.py', '--method', $method, '--protocol',
                    'within', '--init', $init, '--n-train-sessions', "$n", '--tag', $tag, '--seed', "$s") + $Common + $extra2
            }
        }
    }
}

function Run-Queue($Jobs, $Label) {
    $running = @{}
    $failed = @()
    foreach ($name in $Jobs.Keys) {
        while ((@($running.Values | Where-Object { -not $_.HasExited })).Count -ge $MaxParallel) { Start-Sleep -Seconds 20 }
        $log = "logs\round10_$name.log"
        Write-Host "$(Get-Date -Format 'HH:mm') start $name  (log $log)" -ForegroundColor Cyan
        $p = Start-Process -FilePath $Py -ArgumentList $Jobs[$name] -NoNewWindow -PassThru `
             -RedirectStandardOutput $log -RedirectStandardError "logs\round10_$name.err.log"
        $null = $p.Handle
        try { $p.PriorityClass = [System.Diagnostics.ProcessPriorityClass]::BelowNormal } catch { }   # keep the desktop responsive
        $running[$name] = $p
    }
    foreach ($name in $running.Keys) {
        $running[$name].WaitForExit()
        if ($running[$name].ExitCode -ne 0) { $failed += $name }
    }
    foreach ($name in $failed) {
        Write-Host "--- $name (last lines of logs\round10_$name.err.log):" -ForegroundColor Red
        Get-Content "logs\round10_$name.err.log" -Tail 6 -ErrorAction SilentlyContinue | ForEach-Object { Write-Host "    $_" }
    }
    if ($failed.Count -gt 0) {
        Write-Host "$Label FAILED: $($failed -join ', ')  (re-run this script to resume)" -ForegroundColor Red
    }
    return $failed.Count
}

$n1 = Run-Queue $Phase1 'Phase 1 (pretraining)'
if ($n1 -gt 0) { exit 1 }
Write-Host "$(Get-Date -Format 'HH:mm') phase 1 (pretraining) finished; starting phase 2 (fine-tuning)" -ForegroundColor Green
$n2 = Run-Queue $Phase2 'Phase 2 (fine-tuning)'
if ($n2 -eq 0) {
    Write-Host "ALL JOBS FINISHED $(Get-Date -Format 'yyyy-MM-dd HH:mm'). Next: .\scripts\round10.ps1 -Report$(if ($Smoke) {' -Smoke'})" -ForegroundColor Green
}
