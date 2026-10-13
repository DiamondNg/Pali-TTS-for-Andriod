#NoEnv
#SingleInstance Force
#Persistent

; Find the exe in per-user location first, then all-users (Program Files)
EnvGet, LocalAppData, LOCALAPPDATA
EnvGet, ProgramFiles, PROGRAMFILES

if FileExist(LocalAppData . "\PaliTTS\pali_tts.exe")
    exe := LocalAppData . "\PaliTTS\pali_tts.exe"
else
    exe := ProgramFiles . "\PaliTTS\pali_tts.exe"

; ── System tray ───────────────────────────────────────────────────────────────
Menu, Tray, NoStandard
Menu, Tray, Icon, shell32.dll, 168
Menu, Tray, Tip, Pali TTS
Menu, Tray, Add, Read Pali Aloud  (Win+P), DoRead
Menu, Tray, Add,
Menu, Tray, Add, Exit, DoExit
Menu, Tray, Default, Read Pali Aloud  (Win+P)

; ── Hotkey ────────────────────────────────────────────────────────────────────
#p::GoSub, DoRead

DoRead:
    RunPali()
Return

DoExit:
    ExitApp
Return

; ── Capture selected text -> temp file -> call exe ───────────────────────────
RunPali() {
    global exe

    savedClip := ClipboardAll
    Clipboard := ""
    Send, ^c
    ClipWait, 1
    if ErrorLevel {
        Clipboard := savedClip
        ; Launch with no text so the GUI opens with empty text box
        Run, "%exe%", , Hide
        return
    }

    selectedText := Clipboard
    Clipboard := savedClip
    savedClip := ""

    if (selectedText = "") {
        Run, "%exe%", , Hide
        return
    }

    tmpFile := A_Temp . "\pali_input_" . A_TickCount . ".txt"
    FileAppend, %selectedText%, %tmpFile%, UTF-8

    Run, "%exe%" --input-file "%tmpFile%", , Hide
}
