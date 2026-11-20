# Desactiva el Modo Arcade: la cuenta vuelve a tener el escritorio normal
# y Windows deja de iniciar sesión solo. No borra RetroBat ni los juegos.
# (El Configurador borra además la contraseña cifrada del inicio automático.)
[Console]::OutputEncoding = [Text.Encoding]::UTF8

Remove-ItemProperty 'HKCU:\Software\Microsoft\Windows NT\CurrentVersion\Winlogon' -Name Shell -ErrorAction SilentlyContinue
'Escritorio normal de Windows restaurado en esta cuenta'

$wl = 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon'
Set-ItemProperty $wl -Name AutoAdminLogon -Value '0'
Remove-ItemProperty $wl -Name DefaultPassword -ErrorAction SilentlyContinue
'Inicio de sesión automático desactivado'

Remove-Item 'HKLM:\SOFTWARE\Microsoft\Windows Embedded\EmbeddedLogon' -Recurse -ErrorAction SilentlyContinue
bcdedit /set '{globalsettings}' bootuxdisabled off | Out-Null
bcdedit /set '{bootmgr}' noerrordisplay off | Out-Null
'Arranque y pantallas de Windows restaurados'

# Restos de la versión anterior (usuario Arcade + Shell Launcher)
$viejo = Get-LocalUser -Name 'Arcade' -ErrorAction SilentlyContinue
try {
    $sl = [wmiclass]'\\localhost\root\standardcimv2\embedded:WESL_UserSetting'
    if ($viejo) { try { $sl.RemoveCustomShell($viejo.SID.Value) | Out-Null } catch { } }
    $sl.SetEnabled($false) | Out-Null
} catch { }
if ($viejo) {
    Get-CimInstance Win32_UserProfile | Where-Object { $_.SID -eq $viejo.SID.Value } | Remove-CimInstance -ErrorAction SilentlyContinue
    Remove-LocalUser -Name 'Arcade' -ErrorAction SilentlyContinue
    'Usuario Arcade de la versión anterior eliminado'
}

"`nModo Arcade desactivado. Al reiniciar verás el inicio de sesión y el escritorio normales."
