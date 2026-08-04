# Benchmark: 1.3.0beta3 vs 1.2.1 (memory / idle CPU / threads / size)
$ErrorActionPreference = "SilentlyContinue"
$root = "C:\Users\张鑫\Desktop\ZhaxxxxxxQAQ"
$py = "$root\venv\Scripts\python.exe"
$v121 = "$root\版本存档\v1.2.1"

Write-Host "=== [1/5] Kill old instances ==="
Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*main.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 3
Remove-Item "$v121\data\app.lock" -Force -ErrorAction SilentlyContinue
Remove-Item "$root\data\app.lock" -Force -ErrorAction SilentlyContinue

Write-Host "=== [2/5] Start both (same interpreter) ==="
$r1 = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine="`"$py`" -X utf8 `"$v121\app\main.py`""}
$r2 = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine="`"$py`" -X utf8 `"$root\app\main.py`""}
Write-Host "1.2.1 pid=$($r1.ProcessId)  beta3 pid=$($r2.ProcessId)"
Start-Sleep -Seconds 18

Write-Host "=== [3/5] Find processes ==="
$p121 = Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*v1.2.1*' } | Select-Object -First 1
$pb3 = Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like "*$root\app\main.py*" } | Select-Object -First 1
Write-Host "1.2.1 proc: $($p121.ProcessId)  beta3 proc: $($pb3.ProcessId)"
if (-not $p121 -or -not $pb3) { Write-Host "FAIL: processes not found"; exit 1 }

Write-Host "=== [4/5] Sample 10 rounds (2s interval, idle) ==="
$mem121 = @(); $memB3 = @(); $cpu121 = @(); $cpuB3 = @(); $thr121 = @(); $thrB3 = @()
for ($i = 0; $i -lt 10; $i++) {
    $a = Get-Process -Id $p121.ProcessId
    $b = Get-Process -Id $pb3.ProcessId
    $mem121 += $a.WorkingSet64 / 1MB
    $memB3 += $b.WorkingSet64 / 1MB
    $cpu121 += $a.CPU
    $cpuB3 += $b.CPU
    $thr121 += $a.Threads.Count
    $thrB3 += $b.Threads.Count
    Start-Sleep -Seconds 2
}
function Avg($arr) { return [math]::Round(($arr | Measure-Object -Average).Average, 2) }
$m1 = Avg $mem121; $m2 = Avg $memB3
$c1 = Avg $cpu121; $c2 = Avg $cpuB3
$t1 = Avg $thr121; $t2 = Avg $thrB3
Write-Host "=== [5/5] Results (avg of 10) ==="
Write-Host "Memory WorkingSet MB: 1.2.1=$m1  beta3=$m2  delta=$([math]::Round($m2-$m1,2))"
Write-Host "CPU total sec:         1.2.1=$c1  beta3=$c2  delta=$([math]::Round($c2-$c1,3))"
Write-Host "Threads:               1.2.1=$t1  beta3=$t2"

Write-Host "=== Size ==="
$exe121 = Get-Item "$v121\ZhaxxxxxxQAQ_Setup_v1.2.1.exe"
$exeB3 = Get-Item "$root\build\dist\installer\ZhaxxxxxxQAQ_Setup_v1.3.0.exe"
Write-Host "Installer MB: 1.2.1=$([math]::Round($exe121.Length/1MB,1))  beta3=$([math]::Round($exeB3.Length/1MB,1))"
$lines121 = (Get-ChildItem "$v121\app" -Filter "*.py" | Get-Content | Measure-Object -Line).Lines
$linesB3 = (Get-ChildItem "$root\app" -Filter "*.py" | Get-Content | Measure-Object -Line).Lines
Write-Host "Source lines: 1.2.1=$lines121  beta3=$linesB3"
