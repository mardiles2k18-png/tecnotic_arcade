# Crea en RetroBat un acceso directo por cada juego de una carpeta.
#   -Base           carpeta de juegos
#   -ConCategorias  1 si dentro hay categorías (Lucha, Beat 'em up...) y dentro de ellas los juegos
#   -RetroBat       ruta de retrobat.exe
param(
    [string]$Base = 'C:\Juegos',
    [string]$ConCategorias = '1',
    [string]$RetroBat = 'C:\RetroBat\retrobat.exe'
)
[Console]::OutputEncoding = [Text.Encoding]::UTF8

$destino = Join-Path (Split-Path $RetroBat) 'roms\windows'
$descartar = 'unins|crash|setup|redist|vcredist|dxsetup|directx|dotnet|helper|report|UE4Prereq|oalinst|vc_redist|launcher|config|settings|install'
$marcasCrack = '^(3dm.*\.dll|3dmgame\.ini|cream_api\.ini|steam_api(64)?_o\.dll|steam_emu\.ini|codex\.ini|cpy\.ini|steam_interfaces\.txt|onlinefix.*|smartsteamemu.*|goldberg.*)$'

if (-not (Test-Path $Base)) { "No existe la carpeta $Base"; exit 1 }
New-Item -ItemType Directory -Force -Path $destino | Out-Null

# El usuario Arcade necesita poder abrir (y guardar partidas en) la carpeta de juegos
if (Get-LocalUser -Name Arcade -ErrorAction SilentlyContinue) {
    icacls $Base /grant 'Arcade:(OI)(CI)M' /Q | Out-Null
    "Permisos del usuario Arcade en $Base"
}

if ($ConCategorias -eq '1') { $juegos = Get-ChildItem $Base -Directory | ForEach-Object { Get-ChildItem $_.FullName -Directory } }
else { $juegos = Get-ChildItem $Base -Directory }

$shell = New-Object -ComObject WScript.Shell
$creados = 0
foreach ($juego in $juegos) {
    $crack = Get-ChildItem $juego.FullName -Recurse -File -ErrorAction SilentlyContinue |
             Where-Object { $_.Name -match $marcasCrack } | Select-Object -First 1
    if ($crack) { "OMITIDO: $($juego.Name) (contiene $($crack.Name))"; continue }

    $exe = Get-ChildItem $juego.FullName -Recurse -Filter *.exe -ErrorAction SilentlyContinue |
           Where-Object { $_.Name -notmatch $descartar } |
           Sort-Object Length -Descending | Select-Object -First 1
    if (-not $exe) { "SIN EJECUTABLE: $($juego.Name)"; continue }

    $lnk = $shell.CreateShortcut((Join-Path $destino "$($juego.Name).lnk"))
    $lnk.TargetPath = $exe.FullName
    $lnk.WorkingDirectory = $exe.DirectoryName
    $lnk.Save()
    $creados++
    "OK: $($juego.Name)  ->  $($exe.FullName.Replace($juego.FullName + '\', ''))"
}
"Accesos directos creados: $creados (en $destino)"
"En RetroBat: Menú > Ajustes de juegos > Actualizar lista de juegos."
