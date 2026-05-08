<#
    Pomodoro Timer - Terminal Edition
    Double-click pomodoro.bat or run: powershell -ExecutionPolicy Bypass -File pomodoro.ps1
#>

$ErrorActionPreference = 'Continue'

# Config
$Durations = @{
    work  = 25 * 60
    break = 5 * 60
    long  = 15 * 60
}
$ModeLabels = @{ work = '[Focus]'; break = '[Break]'; long = '[Long Break]' }

# State
$Mode      = 'work'
$Remaining = $Durations.work
$Total     = $Durations.work
$Running   = $false
$DataFile  = Join-Path $env:USERPROFILE '.pomodoro_data.json'
$Today     = (Get-Date).ToString('yyyy-MM-dd')

# Load saved sessions
$SessionsToday = 0
if (Test-Path $DataFile) {
    $data = Get-Content $DataFile -Raw | ConvertFrom-Json
    if ($data.date -eq $Today) {
        $SessionsToday = $data.sessions
    }
}

function Save-Data {
    @{ date = $Today; sessions = $SessionsToday } | ConvertTo-Json | Set-Content $DataFile
}

# Sound
function Play-Sound {
    try {
        for ($i = 0; $i -lt 3; $i++) {
            [System.Console]::Beep(500 + $i * 200, 200)
        }
    } catch {
        # Fallback: ASCII bell
        Write-Host "[DING!]" -NoNewline
    }
}

# UI helpers
try { $Host.UI.RawUI.CursorVisible = $false } catch {}
try { [Console]::CursorVisible = $false } catch {}
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch {}

function Format-Time($seconds) {
    $m = [int]($seconds / 60)
    $s = [int]($seconds % 60)
    return ('{0:D2}:{1:D2}' -f $m, $s)
}

function Format-Bar {
    $width = 40
    $progress = 1 - ($Remaining / $Total)
    $filled = [Math]::Floor($progress * $width)
    $empty = $width - $filled
    $bar = [string]::new('@', $filled) + [string]::new('-', $empty)
    return $bar
}

function Format-Dots {
    $d = ''
    for ($i = 1; $i -le 4; $i++) {
        if ($i -le ($SessionsToday % 4)) {
            $d += 'o '
        } else {
            $d += '. '
        }
    }
    return $d.TrimEnd()
}

function Show-UI {
    Clear-Host
    $label = $ModeLabels[$Mode]
    $timeStr = Format-Time $Remaining
    $bar = Format-Bar
    $dots = Format-Dots
    $progressPct = [Math]::Floor((1 - $Remaining / $Total) * 100)

    if ($Running) {
        $status = '> RUNNING'
    } else {
        $status = '  PAUSED'
    }

    Write-Host ''
    Write-Host '  +============================================+'
    Write-Host "  |        $label  Pomodoro Timer        |"
    Write-Host '  +============================================+'
    Write-Host '  |                                            |'
    Write-Host "  |              $timeStr                         |"
    Write-Host '  |                                            |'
    Write-Host "  |         $bar  ${progressPct}%                  |"
    Write-Host '  |                                            |'
    Write-Host "  |              $status                         |"
    Write-Host '  |                                            |'
    Write-Host '  +============================================+'
    Write-Host '  | [Space]Start/Pause [1]Focus [2]Break [3]Long |'
    Write-Host "  | [R]Reset  [S]Skip  [Q]Quit   Today: $dots  x${SessionsToday}|"
    Write-Host '  +============================================+'
    Write-Host ''
}

# Actions
function Switch-Mode($m) {
    $script:Mode = $m
    $script:Remaining = $Durations[$m]
    $script:Total = $Durations[$m]
    $script:Running = $false
}

function Reset-Current {
    $script:Remaining = $Durations[$Mode]
    $script:Total = $Durations[$Mode]
    $script:Running = $false
}

function Skip-Current {
    $script:Running = $false
    $script:Remaining = 0
    if ($Mode -eq 'work') {
        $script:SessionsToday++
        Save-Data
        if ($SessionsToday % 4 -eq 0) {
            Switch-Mode 'long'
        } else {
            Switch-Mode 'break'
        }
    } else {
        Switch-Mode 'work'
    }
}

# Main Loop
function Main {
    Show-UI

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $lastSecond = -1

    while ($true) {
        # Check keypress
        if ([Console]::KeyAvailable) {
            $key = [Console]::ReadKey($true)
            switch ($key.Key) {
                'Spacebar' {
                    if ($Remaining -le 0) { Reset-Current }
                    $script:Running = -not $Running
                }
                'D1' { Switch-Mode 'work' }
                'D2' { Switch-Mode 'break' }
                'D3' { Switch-Mode 'long' }
                'R'    { Reset-Current }
                'S'    { Skip-Current }
                'Q'    { try { $Host.UI.RawUI.CursorVisible = $true } catch {}; try { [Console]::CursorVisible = $true } catch {}; return }
                'Escape' { try { $Host.UI.RawUI.CursorVisible = $true } catch {}; try { [Console]::CursorVisible = $true } catch {}; return }
            }
            Show-UI
        }

        # Tick every second
        $elapsed = [Math]::Floor($sw.Elapsed.TotalSeconds)
        if ($elapsed -ne $lastSecond) {
            $lastSecond = $elapsed
            if ($Running -and $Remaining -gt 0) {
                $script:Remaining--
                Show-UI

                if ($Remaining -eq 0) {
                    $script:Running = $false
                    if ($Mode -eq 'work') {
                        $script:SessionsToday++
                        Save-Data
                    }
                    Play-Sound
                    Show-UI
                }
            }
        }

        Start-Sleep -Milliseconds 50
    }
}

# Entry
try {
    Write-Host ''
    Write-Host '  Pomodoro Timer starting...'
    Write-Host ''
    Main
} finally {
    try { $Host.UI.RawUI.CursorVisible = $true } catch {}; try { [Console]::CursorVisible = $true } catch {}
    Write-Host ''
}
