<#
.SYNOPSIS
    Round 9 (Chapter 1, direction 4): cross-subject pretraining + within-subject fine-tuning of EEGNet and RED,
    3 seeds, as a two-phase job queue.

.DESCRIPTION
    Phase 1: scripts\pretrain_subjects.py - one EEGNet per target subject on the other 27 subjects (3 seeds).
    Phase 2: scripts\run_baseline.py --init pretrain - within-subject fine-tuning from that model:
             eegnet@ft and red_selfteacher@ft (same folds and settings as eegnet / red_selfteacher).
    Runs at most -MaxParallel jobs at a time in the background of this window; each job's output goes to
    logs\round9_<job>.log. Every job is resumable (finished subjects / folds are skipped), so the script can be
    started again after an interruption. Start it from a PowerShell window in which "conda activate torch-gpu"
    has been run.

.EXAMPLE
    conda activate torch-gpu
    Set-ExecutionPolicy -Scope Process Bypass
    .\scripts\round9.ps1 -Smoke              # a few minutes, writes to results_smoke\ and checkpoints_smoke\
    .\scripts\round9.ps1                     # the real run
    .\scripts\round9.ps1 -Report             # tables after all jobs finished
    .\scripts\round9.ps1 -MaxParallel 3 -MaxVramGB 4    # gentler: 3 jobs sharing at most ~4 GB of GPU memory

.PARAMETER MaxVramGB
    Total GPU memory budget in GB for all jobs together. Each job gets MaxVramGB / MaxParallel, minus ~0.5 GB
    reserved for its CUDA context (which PyTorch cannot cap), as a hard per-process limit (--max-vram-gb).
    Pretraining holds the whole dataset on the GPU (~0.5 GB); about 1-1.5 GB per job is enough.
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
$CkptDir = if ($Smoke) { 'checkpoints_smoke' } else { 'checkpoints' }    # smoke models never reach checkpoints\
$Common = @('--device', $Device, '--results-dir', $ResultsDir, '--checkpoint-dir', $CkptDir)
if ($MaxVramGB -gt 0) {
    $perJob = [math]::Max(0.5, $MaxVramGB / $MaxParallel - 0.5)
    $perJobText = $perJob.ToString('0.00', [System.Globalization.CultureInfo]::InvariantCulture)
    Write-Host "GPU memory: $MaxVramGB GB total for $MaxParallel parallel jobs -> limit $perJobText GB per job (+ CUDA context)" -ForegroundColor Yellow
    $Common += @('--max-vram-gb', $perJobText)
}

if ($Report) {
    $m = @('eegnet', 'eegnet@ft', 'red_selfteacher', 'red_selfteacher@ft')
    if ($Smoke) {   # the from-scratch references exist only in results\
        & $Py scripts\compare_methods.py --protocol within --reference 'eegnet@ft' --results-dir $ResultsDir --methods 'eegnet@ft' 'red_selfteacher@ft'
        exit
    }
    & $Py scripts\compare_methods.py --protocol within --reference eegnet --results-dir $ResultsDir --methods @m --out "$ResultsDir\compare_round9.md"
    & $Py scripts\compare_methods.py --protocol within --reference 'eegnet@ft' --results-dir $ResultsDir --methods @m --out "$ResultsDir\compare_round9_vs_ft.md"
    exit
}

$Halves = @{ 'a' = @('1','2','3','4','5','6','7','8','9','10','11','12','13','14');
             'b' = @('15','16','17','18','19','20','21','22','23','24','25','26','27','28') }
$Seeds = if ($Smoke) { @(0) } else { @(0, 1, 2) }
$HalfNames = if ($Smoke) { @('a') } else { @('a', 'b') }
function Subjects($h) { if ($Smoke) { @('--subjects', '2', '18') } else { @('--subjects') + $Halves[$h] } }

$Phase1 = [ordered]@{}
$Phase2 = [ordered]@{}
foreach ($s in $Seeds) {
    foreach ($h in $HalfNames) {
        $extra = if ($Smoke) { @('--max-epochs', '1') } else { @() }
        $Phase1["pretrain_seed${s}_$h"] = @('-u', 'scripts\pretrain_subjects.py', '--seed', "$s") + $Common + (Subjects $h) + $extra
        foreach ($method in 'eegnet', 'red_selfteacher') {
            $extra2 = if ($Smoke) { @('--sessions', '1', '--max-epochs', '1') } else { @() }
            $Phase2["${method}_ft_seed${s}_$h"] = @('-u', 'scripts\run_baseline.py', '--method', $method, '--protocol',
                'within', '--init', 'pretrain', '--tag', 'ft', '--seed', "$s") + $Common + (Subjects $h) + $extra2
        }
    }
}

function Run-Queue($Jobs, $Label) {
    $running = @{}
    $failed = @()
    foreach ($name in $Jobs.Keys) {
        while ((@($running.Values | Where-Object { -not $_.HasExited })).Count -ge $MaxParallel) { Start-Sleep -Seconds 20 }
        $log = "logs\round9_$name.log"
        Write-Host "$(Get-Date -Format 'HH:mm') start $name  (log $log)" -ForegroundColor Cyan
        $p = Start-Process -FilePath $Py -ArgumentList $Jobs[$name] -NoNewWindow -PassThru `
             -RedirectStandardOutput $log -RedirectStandardError "logs\round9_$name.err.log"
        $null = $p.Handle
        try { $p.PriorityClass = [System.Diagnostics.ProcessPriorityClass]::BelowNormal } catch { }   # keep the desktop responsive
        $running[$name] = $p
    }
    foreach ($name in $running.Keys) {
        $running[$name].WaitForExit()
        if ($running[$name].ExitCode -ne 0) { $failed += $name }
    }
    foreach ($name in $failed) {
        Write-Host "--- $name (last lines of logs\round9_$name.err.log):" -ForegroundColor Red
        Get-Content "logs\round9_$name.err.log" -Tail 6 -ErrorAction SilentlyContinue | ForEach-Object { Write-Host "    $_" }
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
    Write-Host "ALL JOBS FINISHED $(Get-Date -Format 'yyyy-MM-dd HH:mm'). Next: .\scripts\round9.ps1 -Report$(if ($Smoke) {' -Smoke'})" -ForegroundColor Green
}
