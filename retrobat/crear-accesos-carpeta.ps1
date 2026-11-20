# Crea en RetroBat (roms\windows) un acceso directo por cada juego de una carpeta.
# Cada subcarpeta es un juego: se elige su ejecutable principal (el .exe más grande,
# descartando instaladores y herramientas) y el acceso directo se llama como la carpeta.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File crear-accesos-carpeta.ps1 -Categoria 'beat*em up'
# -Categoria admite comodines (*) y se busca dentro de "Juegos de PC".

param(
    [string]$Categoria = 'beat*em up'
)

$base    = 'C:\Users\Tecnotics Arcade\Desktop\Juegos de PC'
$destino = 'C:\RetroBat\roms\windows'

# Ejecutables que no son el juego
$descartar = 'unins|crash|setup|redist|vcredist|dxsetup|directx|dotnet|helper|report|UE4Prereq|oalinst|vc_redist|launcher|config|settings|install'
# Archivos típicos de cracks / emuladores de Steam
$marcasCrack = '^(3dm.*\.dll|3dmgame\.ini|cream_api\.ini|steam_api(64)?_o\.dll|steam_emu\.ini|codex\.ini|cpy\.ini|steam_interfaces\.txt|onlinefix.*|smartsteamemu.*|goldberg.*)$'

$carpeta = Get-ChildItem $base -Directory | Where-Object { $_.Name -like $Categoria } | Select-Object -First 1
if (-not $carpeta) { "No encuentro la carpeta '$Categoria' dentro de $base"; exit 1 }
"Carpeta: $($carpeta.FullName)"

New-Item -ItemType Directory -Force -Path $destino | Out-Null
$shell = New-Object -ComObject WScript.Shell

foreach ($juego in Get-ChildItem $carpeta.FullName -Directory) {
    $crack = Get-ChildItem $juego.FullName -Recurse -File -ErrorAction SilentlyContinue |
             Where-Object { $_.Name -match $marcasCrack } | Select-Object -First 1
    if ($crack) { "OMITIDO: $($juego.Name) (contiene $($crack.Name))"; continue }

    $exe = Get-ChildItem $juego.FullName -Recurse -Filter *.exe -ErrorAction SilentlyContinue |
           Where-Object { $_.Name -notmatch $descartar } |
           Sort-Object Length -Descending | Select-Object -First 1
    if (-not $exe) { "SIN EJECUTABLE: $($juego.Name)"; continue }

    $lnk = $shell.CreateShortcut((Join-Path $destino "$($juego.Name).lnk"))
    $lnk.TargetPath       = $exe.FullName
    $lnk.WorkingDirectory = $exe.DirectoryName
    $lnk.Save()
    "OK: $($juego.Name)  ->  $($exe.FullName.Replace($juego.FullName + '\', ''))"
}
