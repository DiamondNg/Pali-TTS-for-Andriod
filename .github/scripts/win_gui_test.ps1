# GUI tests of the installed Windows app (run by build_windows.yml).
# 1) open the window with text; 2) Close only hides it (tray app keeps running);
# 3) Ctrl+Shift+Y reads the selection without the clipboard; 4) floating button:
#    appears after a mouse selection, Esc hides it, a click reads the text;
# 5) tray menu Exit quits; 6) the window opens at the remembered size.
param([string]$App = "$env:LOCALAPPDATA\Programs\Read Pali Aloud\ReadPaliAloud.exe",
      [string]$Out = "shots")
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force $Out | Out-Null
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
Add-Type @"
using System; using System.Runtime.InteropServices; using System.Text;
public static class K {
  [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, UIntPtr extra);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, int dx, int dy, uint data, UIntPtr extra);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern uint GetClipboardSequenceNumber();
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr FindWindow(string cls, string title);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  public static void Key(byte vk) { keybd_event(vk,0,0,UIntPtr.Zero); keybd_event(vk,0,2,UIntPtr.Zero); }
  public static void CtrlShiftY() {
    keybd_event(0x11,0,0,UIntPtr.Zero); keybd_event(0x10,0,0,UIntPtr.Zero);
    keybd_event(0x59,0,0,UIntPtr.Zero); keybd_event(0x59,0,2,UIntPtr.Zero);
    keybd_event(0x10,0,2,UIntPtr.Zero); keybd_event(0x11,0,2,UIntPtr.Zero);
  }
  public static void Drag(int x1, int y, int x2) {
    SetCursorPos(x1, y); mouse_event(2,0,0,0,UIntPtr.Zero);
    for (int x = x1; x <= x2; x += 20) { SetCursorPos(x, y); System.Threading.Thread.Sleep(15); }
    SetCursorPos(x2, y); mouse_event(4,0,0,0,UIntPtr.Zero);
  }
  public static void Click(int x, int y) {
    SetCursorPos(x, y); System.Threading.Thread.Sleep(50);
    mouse_event(2,0,0,0,UIntPtr.Zero); mouse_event(4,0,0,0,UIntPtr.Zero);
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
function Dumped { if (Test-Path $env:PALI_TTS_DUMP) { Get-Content $env:PALI_TTS_DUMP -Raw -Encoding UTF8 } else { "" } }
function PopupVisible { $h = [K]::FindWindow("PaliTTS.Popup", [NullString]::Value); ($h -ne [IntPtr]::Zero) -and [K]::IsWindowVisible($h) }

# All Pāli letters with diacritics must arrive unchanged
$text = "Evaṃ me sutaṃ ekaṁ samayaṃ bhagavā sāvatthiyaṃ viharati aṅga aññaṃ paññā kaṭhina ḍaṇḍa paṇṇa ḷ ī ū"
$fail = 0
$env:PALI_TTS_DUMP = Join-Path $env:RUNNER_TEMP "dump.txt"

# A text box in another program, as the place where the user selects text
function TestForm([scriptblock]$steps) {
  $form = New-Object System.Windows.Forms.Form
  $form.Text = "Selection test"; $form.TopMost = $true; $form.Width = 900; $form.Height = 200
  $form.StartPosition = "Manual"; $form.Left = 100; $form.Top = 100
  $box = New-Object System.Windows.Forms.TextBox
  $box.Multiline = $true; $box.Dock = "Fill"; $box.Text = $text
  $box.Font = New-Object System.Drawing.Font("Segoe UI", 14)
  $form.Controls.Add($box)
  $t = New-Object System.Windows.Forms.Timer; $t.Interval = 1500
  $script:box = $box; $script:form = $form; $script:t = $t; $script:steps = $steps; $script:step = 0
  $t.Add_Tick({
    $script:step++; & $script:steps
    if ($script:step -ge 8) { $script:t.Stop(); $script:form.Close() } })
  $form.Add_Shown({ $script:form.Activate(); $script:box.Focus(); $script:t.Start() })
  [System.Windows.Forms.Application]::Run($form)
}

# 1) Window opened with text (installed app starts in the tray, this copy hands over)
StopAll
$in = Join-Path $env:RUNNER_TEMP "in.txt"
[IO.File]::WriteAllText($in, $text, (New-Object Text.UTF8Encoding $false))
Start-Process $App -ArgumentList "--input-file", "`"$in`""
Start-Sleep 10
Titles
Shot "window"
if ((Dumped) -ne $text) { "FAIL: text not received: '$(Dumped)'"; $fail = 1 } else { "OK: window got the text" }
if (-not (Titles | Select-String "Read Pāli Aloud")) { "FAIL: no 'Read Pāli Aloud' window"; $fail = 1 }
$tray = [K]::FindWindow("PaliTTS.TrayWindow", [NullString]::Value)
if ($tray -eq [IntPtr]::Zero) { "FAIL: no tray window"; $fail = 1 } else { "OK: tray running" }

# 2) Close hides the window; the app keeps running
$p = Get-Process ReadPaliAloud | Where-Object MainWindowTitle | Select-Object -First 1
if ($p) { $p.CloseMainWindow() | Out-Null }
Start-Sleep 3
Shot "after-close"
if (Get-Process ReadPaliAloud -ErrorAction SilentlyContinue) { "OK: still running after Close" } else { "FAIL: Close quit the app"; $fail = 1 }

# 3) Ctrl+Shift+Y reads the selection without touching the clipboard
Remove-Item $env:PALI_TTS_DUMP -ErrorAction SilentlyContinue
Set-Clipboard "clipboard sentinel"
$seq = [K]::GetClipboardSequenceNumber()
TestForm { if ($script:step -eq 1) { $script:form.Activate(); $script:box.Focus(); $script:box.SelectAll(); [K]::CtrlShiftY() } }
Start-Sleep 3
Shot "hotkey"
"Ctrl+Shift+Y text: '$(Dumped)'"
if ((Dumped) -eq $text) { "OK: Ctrl+Shift+Y passed the selected text" } else { "FAIL: wrong text"; $fail = 1 }
if ([K]::GetClipboardSequenceNumber() -ne $seq -or (Get-Clipboard) -ne "clipboard sentinel") {
  "FAIL: the clipboard was used"; $fail = 1 } else { "OK: clipboard untouched" }
$p = Get-Process ReadPaliAloud | Where-Object MainWindowTitle | Select-Object -First 1
if ($p) { $p.CloseMainWindow() | Out-Null }
Start-Sleep 2

# 4) Floating button: select with the mouse → button; Esc hides it; select again → click it
Remove-Item $env:PALI_TTS_DUMP -ErrorAction SilentlyContinue
$script:sawPopup = $false; $script:escHid = $false
TestForm {
  switch ($script:step) {
    1 { [K]::Drag(115, 148, 700) }
    2 { $script:sawPopup = PopupVisible; Shot "popup"; [K]::Key(0x1B) }
    3 { $script:escHid = -not (PopupVisible); [K]::Drag(115, 148, 900) }
    4 {
      $h = [K]::FindWindow("PaliTTS.Popup", [NullString]::Value); $r = New-Object "K+RECT"
      if ((PopupVisible) -and [K]::GetWindowRect($h, [ref]$r)) {
        Shot "popup2"; [K]::Click([int](($r.L + $r.R) / 2), [int](($r.T + $r.B) / 2)) }
    }
  }
}
Start-Sleep 3
Shot "popup-read"
if ($script:sawPopup) { "OK: floating button appeared" } else { "FAIL: no floating button after selecting"; $fail = 1 }
if ($script:escHid) { "OK: Esc hid the button" } else { "FAIL: Esc did not hide the button"; $fail = 1 }
"button text: '$(Dumped)'"
if ((Dumped).Length -gt 10 -and $text.StartsWith((Dumped).Substring(0, 10))) { "OK: button read the selection" }
else { "FAIL: button did not pass the selection"; $fail = 1 }

# 5) Tray menu → Exit quits completely
$tray = [K]::FindWindow("PaliTTS.TrayWindow", [NullString]::Value)
[K]::PostMessage($tray, 0x0111, [IntPtr]4, [IntPtr]::Zero) | Out-Null  # WM_COMMAND, Exit
Start-Sleep 4
if (Get-Process ReadPaliAloud -ErrorAction SilentlyContinue) { "FAIL: Exit did not quit"; $fail = 1 } else { "OK: Exit quit the app" }

# 6) The saved window size is used when the window is opened again
$cfg = Join-Path $env:APPDATA "PaliTTS\settings.json"
$set = if (Test-Path $cfg) { Get-Content $cfg -Raw -Encoding UTF8 | ConvertFrom-Json } else { [pscustomobject]@{} }
"saved size after the tests: $($set.size -join 'x')"
$scr = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$tw = [Math]::Min([int]$set.size[0] + 80, $scr.Width - 40)   # app: never bigger than the screen
$th = [Math]::Min([int]$set.size[1] + 40, $scr.Height - 120)
$set | Add-Member -Force -NotePropertyName size -NotePropertyValue @($tw, $th)
[IO.File]::WriteAllText($cfg, ($set | ConvertTo-Json -Depth 5), (New-Object Text.UTF8Encoding $false))
Start-Process $App -ArgumentList "--input-file", "`"$in`""
Start-Sleep 10
$p = Get-Process ReadPaliAloud | Where-Object MainWindowTitle | Select-Object -First 1
$r = New-Object "K+RECT"
if ($p -and [K]::GetWindowRect($p.MainWindowHandle, [ref]$r)) {
  $w = $r.R - $r.L; $h = $r.B - $r.T
  "wanted ${tw}x${th}; window with frame: ${w}x${h}"
  if ($w -ge $tw -and $w -le $tw + 60 -and $h -ge $th -and $h -le $th + 80) { "OK: remembered size used" }
  else { "FAIL: remembered size not used"; $fail = 1 }
} else { "FAIL: no window for the size test"; $fail = 1 }
Shot "remembered-size"
StopAll
exit $fail
