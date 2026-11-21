# Crea en RetroBat (roms\windows) un acceso directo por cada juego de lucha.
# El nombre del acceso directo es el que se ve en el menú de RetroBat.
# Para añadir un juego, agrega una línea:  'Nombre en el menú' = 'ruta\al\juego.exe'
# (la ruta es relativa a la carpeta $lucha)

$lucha   = 'C:\Juegos\Lucha'   # el usuario Arcade debe poder leer esta carpeta
$destino = 'C:\RetroBat\roms\windows'

$juegos = [ordered]@{
    'Big Rumble Boxing Creed Champions' = 'Big Rumble Boxing Creed Champions\RM\Binaries\Win64\RM-Win64-Shipping.exe'
    'Blade Strangers'                   = 'Blade Strangers Build\game.exe'
    'Mortal Kombat Komplete Edition'    = 'DiscContentPC\MKKE.exe'
    'Guilty Gear Xrd Rev 2'             = 'GUILTY GEAR Xrd REV 2\GUILTY GEAR Xrd -REVELATOR-\Binaries\Win32\GuiltyGearXrd.exe'
    'Guilty Gear XX Accent Core Plus R' = 'Guilty Gear XX Accent Core Plus R\GGXXACPR_Win.exe'
    'Hunter x Hunter Nen x Impact'      = 'HxHNENxIMPACT\HxHNENxIMPACT.exe'
    'Melty Blood Type Lumina'           = 'MELTY BLOOD TYPE LUMINA\MBTL.exe'
    'Nickelodeon All-Star Brawl 2'      = 'Nickelodeon All Star Brawl 2 Iroh Brawl\Nickelodeon All-Star Brawl 2.exe'
    'Nitroplus Blasterz'                = 'Nitroplus Blasterz Heroines Infinite Duel\Nitroplus Blasterz.exe'
    'Pocket Bravery'                    = 'Pocket Bravery\Bravery.exe'
    'Power Rangers Battle for the Grid' = 'Power Rangers Battle for the Grid\BattleForTheGrid.exe'
    'Real Bout Fatal Fury 2'            = 'REAL BOUT FATAL FURY 2\RB2.exe'
    'The King of Fighters XIII'         = 'THE KING OF FIGHTERS XIII GLOBAL MATCH\game.exe'
    'The King of Fighters XIV'          = 'THE KING OF FIGHTERS XIV\kofxiv.exe'
}

New-Item -ItemType Directory -Force -Path $destino | Out-Null
$shell = New-Object -ComObject WScript.Shell
foreach ($nombre in $juegos.Keys) {
    $exe = Join-Path $lucha $juegos[$nombre]
    if (-not (Test-Path $exe)) { "NO ENCONTRADO: $nombre -> $exe"; continue }
    $lnk = $shell.CreateShortcut((Join-Path $destino "$nombre.lnk"))
    $lnk.TargetPath       = $exe
    $lnk.WorkingDirectory = Split-Path $exe   # el juego arranca desde su propia carpeta
    $lnk.Save()
    "OK: $nombre"
}
