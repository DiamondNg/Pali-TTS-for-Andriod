# GUI tests of the installed Windows app (run by build_windows.yml).
# 1) open the window with text, screenshot; 2) Ctrl+Alt+P on selected text.
param([string]$App = "$env:LOCALAPPDATA\Programs\Read Pali Aloud\ReadPaliAloud.exe",
      [string]$Out = "shots")
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force $Out | Out-Null
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
Add-Type @"
using System; using System.Runtime.InteropServices;
public static class K {
  [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, UIntPtr extra);
  public static void CtrlAltP() {
    keybd_event(0x11,0,0,UIntPtr.Zero); keybd_event(0x12,0,0,UIntPtr.Zero);
    keybd_event(0x50,0,0,UIntPtr.Zero); keybd_event(0x50,0,2,UIntPtr.Zero);
    keybd_event(0x12,0,2,UIntPtr.Zero); keybd_event(0x11,0,2,UIntPtr.Zero);
  }
}
"@
function Shot($name) {
  $b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
  $bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
  $bmp.Save("$Out\$name.png"); $g.Dispose(); $bmp.Dispose()
}
function Titles { Get-Process ReadPaliAloud -ErrorAction SilentlyContinue |
  Where-Object MainWindowTitle | ForEach-Object { "window: '$($_.MainWindowTitle)'" } }
function StopAll { Get-Process ReadPaliAloud -ErrorAction SilentlyContinue | Stop-Process -Force; Start-Sleep 1 }

$text = "Evaṃ me sutaṃ. Ekaṃ samayaṃ bhagavā sāvatthiyaṃ viharati. aññaṃ paññā"
$fail = 0

# 1) Window opened with text (like the shortcut does)
StopAll
$in = Join-Path $env:RUNNER_TEMP "in.txt"
[IO.File]::WriteAllText($in, $text, (New-Object Text.UTF8Encoding $false))
$env:PALI_TTS_DUMP = Join-Path $env:RUNNER_TEMP "dump1.txt"
Start-Process $App -ArgumentList "--input-file", "`"$in`""
Start-Sleep 10
Titles
Shot "window"
$got = if (Test-Path $env:PALI_TTS_DUMP) { Get-Content $env:PALI_TTS_DUMP -Raw -Encoding UTF8 } else { "" }
if ($got -ne $text) { "FAIL: text not received"; $fail = 1 }
else { "OK: window got the text" }
if (-not (Titles | Select-String "Read Pāli Aloud")) { "FAIL: no 'Read Pāli Aloud' window"; $fail = 1 }

# 2) Ctrl+Alt+P: helper copies the selected text and opens the window
StopAll
$env:PALI_TTS_DUMP = Join-Path $env:RUNNER_TEMP "dump2.txt"
Start-Process $App -ArgumentList "--hotkey"
Start-Sleep 4
$form = New-Object System.Windows.Forms.Form
$form.Text = "Selection test"; $form.TopMost = $true; $form.Width = 600; $form.Height = 200
$box = New-Object System.Windows.Forms.TextBox
$box.Multiline = $true; $box.Dock = "Fill"; $box.Text = $text
$form.Controls.Add($box)
$t = New-Object System.Windows.Forms.Timer; $t.Interval = 1500; $step = 0
$t.Add_Tick({
  $script:step++
  if ($script:step -eq 1) { $form.Activate(); $box.Focus(); $box.SelectAll(); [K]::CtrlAltP() }
  elseif ($script:step -ge 6) { $t.Stop(); $form.Close() }
})
$form.Add_Shown({ $form.Activate(); $t.Start() })
[System.Windows.Forms.Application]::Run($form)
Start-Sleep 6
Titles
Shot "hotkey"
if (Test-Path $env:PALI_TTS_DUMP) {
  $got = Get-Content $env:PALI_TTS_DUMP -Raw -Encoding UTF8
  "Ctrl+Alt+P text: '$got'"
  if ($got -eq $text) { "OK: Ctrl+Alt+P passed the selected text" } else { "FAIL: wrong text"; $fail = 1 }
} else { "FAIL: Ctrl+Alt+P did not open the window"; $fail = 1 }
StopAll
exit $fail
