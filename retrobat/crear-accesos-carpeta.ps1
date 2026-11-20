# Crea en RetroBat (roms\windows) un acceso directo por cada juego de una carpeta.
# Cada subcarpeta es un juego: se elige su ejecutable principal (el .exe más grande,
# con nombres de instaladores y herramientas al final) y el acceso directo se llama como la carpeta.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File crear-accesos-carpeta.ps1 -Categoria 'beat*em up'
# -Categoria admite comodines (*) y se busca dentro de "Juegos de PC".

param(
    [string]$Categoria = 'beat*em up'
)

$base    = 'C:\Users\Tecnotics Arcade\Desktop\Juegos de PC'
$destino = 'C:\RetroBat\roms\windows'

# Nombres que se dejan al final de las sugerencias
$menosPrioritarios = 'unins|crash|setup|redist|vcredist|dxsetup|directx|dotnet|helper|report|UE4Prereq|oalinst|vc_redist|launcher|config|settings|install'
$coincidencias = @(Get-ChildItem -LiteralPath $base -Directory | Where-Object { $_.Name -like $Categoria })
if ($coincidencias.Count -gt 1) { "Categoria ambigua: $($coincidencias.Name -join ', ')"; exit 1 }
$carpeta = $coincidencias | Select-Object -First 1
if (-not $carpeta) { "No encuentro la carpeta '$Categoria' dentro de $base"; exit 1 }
"Carpeta: $($carpeta.FullName)"

New-Item -ItemType Directory -Force -Path $destino | Out-Null
$shell = New-Object -ComObject WScript.Shell

foreach ($juego in Get-ChildItem -LiteralPath $carpeta.FullName -Directory) {
    $exe = Get-ChildItem -LiteralPath $juego.FullName -Recurse -File -Filter *.exe -ErrorAction SilentlyContinue |
           Sort-Object { $_.Name -match $menosPrioritarios }, @{Expression='Length'; Descending=$true}, FullName | Select-Object -First 1
    if (-not $exe) { "SIN EJECUTABLE: $($juego.Name)"; continue }

    $rutaAcceso = Join-Path $destino "$($juego.Name).lnk"
    if (Test-Path -LiteralPath $rutaAcceso) { "YA EXISTE: $rutaAcceso"; continue }
    $lnk = $shell.CreateShortcut($rutaAcceso)
    $lnk.TargetPath       = $exe.FullName
    $lnk.WorkingDirectory = $exe.DirectoryName
    $lnk.Save()
    "OK: $($juego.Name)  ->  $($exe.FullName.Replace($juego.FullName + '\', ''))"
}
