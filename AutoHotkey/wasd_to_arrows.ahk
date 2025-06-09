#Requires AutoHotkey v2.0

; Initial remapping state
remapEnabled := true
targetHWND := 0  ; Will store the window handle (HWND)

; Track internal key state
keys := Map("w", false, "a", false, "s", false, "d", false, "Space", false, "m", false, "n", false, ",", false)
keyMap := Map(
    "w", "Up",
    "a", "Left",
    "s", "Down",
    "d", "Right",
    "Space", "z",
    "m", "x",
    "n", "z",
    ",", "c"
)

; Start timer loop
SetTimer(CheckKeys, 10)

CheckKeys() {
    global remapEnabled, keys, keyMap, targetHWND

    if !remapEnabled
        return

    ; Only run if target window is active
    activeHWND := WinGetID("A")
    if (targetHWND != 0 && activeHWND != targetHWND)
        return

    for keyName, isDown in keys {
        physDown := GetKeyState(keyName, "P")
        if (physDown && !isDown) {
            keys[keyName] := true
            Send("{" keyMap[keyName] " down}")
        } else if (!physDown && isDown) {
            keys[keyName] := false
            Send("{" keyMap[keyName] " up}")
        }
    }
}

; F1 to toggle enable/disable
F1:: {
    global remapEnabled, keys, keyMap
    remapEnabled := !remapEnabled
    TrayTip("WASD Remap", remapEnabled ? "Remapping enabled" : "Remapping disabled", 1)

    ; Release keys if disabling
    if !remapEnabled {
        for keyName, isDown in keys {
            if isDown {
                keys[keyName] := false
                Send("{" keyMap[keyName] " up}")
            }
        }
    }
}

; Ctrl+Space to set current window as remap target
^Space:: {
    global targetHWND
    targetHWND := WinGetID("A")
    TrayTip("WASD Remap", "Remap locked to window ID: " targetHWND, 1)
}
