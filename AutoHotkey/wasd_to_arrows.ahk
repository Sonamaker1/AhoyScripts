#Requires AutoHotkey v2.0

; Track internal state
keys := Map("w", false, "a", false, "s", false, "d", false, "Space", false)
keyMap := Map(
    "w", "Up",
    "a", "Left",
    "s", "Down",
    "d", "Right",
    "Space", "z"
)

; Set up a timer that runs every 10 ms
SetTimer(CheckKeys, 10)

CheckKeys() {
    global keys, keyMap
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
