# Tecnotics Arcade - desactiva el modo arcade y deja Windows como antes.
# No borra el usuario Arcade, RetroBat ni los juegos.
#
# Uso (PowerShell como administrador, también por SSH):
#   powershell -ExecutionPolicy Bypass -File .\desinstalar-modo-arcade.ps1

#Requires -RunAsAdministrator
$usuario = 'Arcade'

try {
    $sl = [wmiclass]'\\localhost\root\standardcimv2\embedded:WESL_UserSetting'
    $u = Get-LocalUser -Name $usuario -ErrorAction SilentlyContinue
    if ($u) { try { $sl.RemoveCustomShell($u.SID.Value) | Out-Null } catch { } }
    $sl.SetEnabled($false) | Out-Null
    'Shell Launcher desactivado'
} catch { 'Shell Launcher no estaba activo' }

$wl = 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon'
Set-ItemProperty $wl -Name AutoAdminLogon -Value '0'
Remove-ItemProperty $wl -Name DefaultPassword -ErrorAction SilentlyContinue
'Inicio de sesión automático desactivado'

Remove-Item 'HKLM:\SOFTWARE\Microsoft\Windows Embedded\EmbeddedLogon' -Recurse -ErrorAction SilentlyContinue
'Custom Logon desactivado'

bcdedit /set '{globalsettings}' bootuxdisabled off | Out-Null
bcdedit /set '{bootmgr}' noerrordisplay off | Out-Null
'Logo de arranque de Windows restaurado'

"`nListo. Reinicia el equipo: Restart-Computer"
