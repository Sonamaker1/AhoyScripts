#Requires AutoHotkey v2.0

^+"::Send '""{Left}'

^Left::Send 'LE '
^Right::Send 'RE '
^Down::Send 'DW '
^Up::Send 'UP '

^NumpadLeft::Send 'LE '
^NumpadRight::Send 'RE '
^NumpadDown::Send 'DW '
^NumpadUp::Send 'UP '

^space::
{
    WinSetAlwaysOnTop -1, "A"
}
