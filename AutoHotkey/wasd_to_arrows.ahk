#Requires AutoHotkey v2.0

; Initial remapping state
remapEnabled := true

; Track internal key state
keys := Map("w", false, "a", false, "s", false, "d", false, "Space", false)
keyMap := Map(
    "w", "Up",
    "a", "Left",
    "s", "Down",
    "d", "Right",
    "Space", "z"
)

; Start timer loop
SetTimer(CheckKeys, 10)

CheckKeys() {
    global remapEnabled, keys, keyMap
    if !remapEnabled
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

; Toggle remapping with F1
F1:: {
    global remapEnabled
    remapEnabled := !remapEnabled
    TrayTip("WASD Remap", remapEnabled ? "Remapping enabled" : "Remapping disabled", 1)

    ; If disabling, release all currently "down" remapped keys
    if !remapEnabled {
        for keyName, isDown in keys {
            if isDown {
                keys[keyName] := false
                Send("{" keyMap[keyName] " up}")
            }
        }
    }
}
