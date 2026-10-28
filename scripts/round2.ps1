<#
.SYNOPSIS
    Chapter 1 round 2 (controls, seeds, sweeps, tuned final runs) in four parallel lanes.

.DESCRIPTION
    Lane 1: red_selfteacher (seed 0), then eegnet seeds 1 and 2
    Lane 2: red_randteacher (seed 0), then eegnet_avgaug (seed 0)
    Lane 3: red seeds 1 and 2
    Lane 4: sweep chain weights -> tau -> teacher (each sweep trains -SweepWorkers configurations at once),
            then the selected configuration "red@tuned" with seeds 0, 1, 2 in parallel
    Lanes only write to their own result directories, so they never interfere. Every run is resumable:
    re-running a lane skips finished folds.

.PARAMETER Lane
    all (default): open one PowerShell window per lane. 1-4: run that lane in this window.
    report: summary, comparison tables and sweep tables (run after all lanes have finished).

.PARAMETER Smoke
    Run the whole schedule on 2 subjects, 1 test session and 2 epochs, into results_smoke/ and
    checkpoints_smoke/ (git-ignored). Takes a few minutes; use it to check the setup first.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\round2.ps1 -Smoke
    powershell -ExecutionPolicy Bypass -File scripts\round2.ps1
    powershell -ExecutionPolicy Bypass -File scripts\round2.ps1 -Lane report
#>
param(
    [ValidateSet('all', '1', '2', '3', '4', 'report')] [string]$Lane = 'all',
    [switch]$Smoke,
    [int]$SweepWorkers = 3,
    [string]$Device = 'cuda'
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
New-Item -ItemType Directory -Force -Path (Join-Path $Root 'logs') | Out-Null

$Py = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path $Py)) { $Py = 'python' }
if (-not $env:OMP_NUM_THREADS) { $env:OMP_NUM_THREADS = '2' }   # several processes share the CPU

if ($Smoke) {
    $ResultsDir = 'results_smoke'
    $Extra = @('--device', $Device, '--max-epochs', '2', '--results-dir', 'results_smoke', '--checkpoint-dir', 'checkpoints_smoke')
    $Subset = @('--subjects', '1', '2', '--sessions', '1')
} else {
    $ResultsDir = 'results'
    $Extra = @('--device', $Device)
    $Subset = @()
}

function Invoke-Py([string[]]$ArgList, [string]$Log) {
    Write-Host ">> python $($ArgList -join ' ')" -ForegroundColor Cyan
    if ($Log) {
        & $Py @ArgList | Tee-Object -FilePath $Log -Append
    } else {
        & $Py @ArgList
    }
    if ($LASTEXITCODE -ne 0) { throw "failed (exit code $LASTEXITCODE): python $($ArgList -join ' ')" }
}

function Invoke-Run([string]$Method, [int]$Seed) {
    $a = @('-u', 'scripts\run_baseline.py', '--method', $Method, '--protocol', 'within', '--seed', "$Seed") + $Extra + $Subset
    Invoke-Py $a "logs\${Method}_within_seed$Seed.log"
}

function Invoke-Sweep([string]$Name, [string[]]$Grid, [string]$BaseFrom) {
    $a = @('-u', 'scripts\run_sweep.py', '--name', $Name, '--method', 'red', '--workers', "$SweepWorkers", '--grid') + $Grid + $Extra
    if ($BaseFrom) { $a += @('--base-from', $BaseFrom) }
    if ($Smoke) { $a += $Subset }
    Invoke-Py $a ''
}

$Stamp = { Get-Date -Format 'yyyy-MM-dd HH:mm' }

switch ($Lane) {
    'all' {
        $shell = (Get-Process -Id $PID).Path            # powershell.exe or pwsh.exe, whichever runs this script
        foreach ($l in 1..4) {
            $a = @('-NoExit', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`"", '-Lane', "$l",
                   '-Device', $Device, '-SweepWorkers', "$SweepWorkers")
            if ($Smoke) { $a += '-Smoke' }
            Start-Process -FilePath $shell -ArgumentList $a -WorkingDirectory $Root
            Start-Sleep -Seconds 2
        }
        Write-Host "Started 4 lane windows. When all show 'LANE n FINISHED', run:"
        Write-Host "  powershell -ExecutionPolicy Bypass -File scripts\round2.ps1 -Lane report$(if ($Smoke) {' -Smoke'})"
    }
    '1' {
        $Host.UI.RawUI.WindowTitle = 'round2 lane 1: red_selfteacher, eegnet seeds 1-2'
        Write-Host "lane 1 started $(& $Stamp)"
        Invoke-Run 'red_selfteacher' 0
        Invoke-Run 'eegnet' 1
        Invoke-Run 'eegnet' 2
        Write-Host "LANE 1 FINISHED $(& $Stamp)" -ForegroundColor Green
    }
    '2' {
        $Host.UI.RawUI.WindowTitle = 'round2 lane 2: red_randteacher, eegnet_avgaug'
        Write-Host "lane 2 started $(& $Stamp)"
        Invoke-Run 'red_randteacher' 0
        Invoke-Run 'eegnet_avgaug' 0
        Write-Host "LANE 2 FINISHED $(& $Stamp)" -ForegroundColor Green
    }
    '3' {
        $Host.UI.RawUI.WindowTitle = 'round2 lane 3: red seeds 1-2'
        Write-Host "lane 3 started $(& $Stamp)"
        Invoke-Run 'red' 1
        Invoke-Run 'red' 2
        Write-Host "LANE 3 FINISHED $(& $Stamp)" -ForegroundColor Green
    }
    '4' {
        $Host.UI.RawUI.WindowTitle = 'round2 lane 4: sweeps, then red@tuned seeds 0-2'
        Write-Host "lane 4 started $(& $Stamp)"
        Invoke-Sweep 'weights' @('loss.lambda_critic=[0.5, 1, 2]', 'loss.lambda_n2n=[0.3, 1, 3]') ''
        Invoke-Sweep 'tau' @('loss.tau=[1, 2, 4]') 'weights'
        Invoke-Sweep 'teacher' @('teacher.k_set=[[2, 3, 6], [1, 2, 3, 4, 5, 6]]', 'loss.beta_lateral=[1, 5]') 'tau'

        # final runs of the selected configuration: three seeds in parallel
        $procs = @()
        foreach ($s in 0, 1, 2) {
            $a = @('-u', 'scripts\run_baseline.py', '--method', 'red', '--protocol', 'within', '--seed', "$s",
                   '--set-from-sweep', 'teacher', '--tag', 'tuned') + $Extra + $Subset
            Write-Host ">> python $($a -join ' ')  (background, log logs\red@tuned_within_seed$s.log)" -ForegroundColor Cyan
            $p = Start-Process -FilePath $Py -ArgumentList $a -NoNewWindow -PassThru `
                 -RedirectStandardOutput "logs\red@tuned_within_seed$s.log" -RedirectStandardError "logs\red@tuned_within_seed$s.err.log"
            $null = $p.Handle                               # keeps the exit code available after the process ends
            $procs += $p
        }
        $procs | Wait-Process
        foreach ($p in $procs) {
            if ($p.ExitCode -ne 0) { throw "a red@tuned run failed (exit code $($p.ExitCode)); see logs\red@tuned_*.log" }
        }
        Write-Host "LANE 4 FINISHED $(& $Stamp)" -ForegroundColor Green
    }
    'report' {
        $rd = @('--results-dir', $ResultsDir)
        Invoke-Py (@('scripts\summarize_results.py') + $rd) ''
        foreach ($sw in 'weights', 'tau', 'teacher') {
            Invoke-Py (@('scripts\select_config.py', '--method', 'red', '--sweep', $sw, '--out', "$ResultsDir\sweep_$sw.md") + $rd) ''
        }
        $methods = @('eegnet', 'dcpm', 'eegnet_avgaug', 'kd_naive', 'red_n2n', 'red_critic', 'red_classmean',
                     'red_randteacher', 'red_selfteacher', 'red', 'red@tuned')
        Invoke-Py (@('scripts\compare_methods.py', '--protocol', 'within', '--methods') + $methods +
                   @('--out', "$ResultsDir\compare_within.md") + $rd) ''
        Invoke-Py (@('scripts\compare_methods.py', '--protocol', 'within', '--exclude-sessions', '2', '5', '--methods') + $methods +
                   @('--out', "$ResultsDir\compare_within_clean.md") + $rd) ''
        Write-Host "Report written to $ResultsDir\ (summary.md, compare_within*.md, sweep_*.md)" -ForegroundColor Green
    }
}
