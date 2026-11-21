param(
    [Parameter(Mandatory=$true)][string]$SourceZip,
    [Parameter(Mandatory=$true)][string]$MediaDirectory,
    [string]$OutputDirectory = (Join-Path $PSScriptRoot '../themes/es-theme-tecnotics-alubrush'),
    [string]$Logo = (Join-Path $PSScriptRoot '../logo/tecnotics-horizontal.png')
)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem
$out=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path $out) { throw "El destino debe ser una carpeta nueva: $out" }
New-Item $out -ItemType Directory -Force | Out-Null
$zip=[IO.Compression.ZipFile]::OpenRead((Resolve-Path -LiteralPath $SourceZip))
$manifest=@()
try {
 foreach($entry in $zip.Entries) {
  if(!$entry.Length) { continue }
  $rel=$entry.FullName -replace '^es-theme-AluBrush/',''
  $dest=[IO.Path]::GetFullPath((Join-Path $out $rel))
  if(!$dest.StartsWith($out+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) { throw 'Ruta fuera del destino' }
  New-Item (Split-Path $dest) -ItemType Directory -Force | Out-Null
  [IO.Compression.ZipFileExtensions]::ExtractToFile($entry,$dest,$false)
  $manifest+=[pscustomobject]@{path=$rel;sha256=(Get-FileHash -LiteralPath $dest -Algorithm SHA256).Hash.ToLower()}
 }
} finally { $zip.Dispose() }
$custom=Join-Path $out 'art/tecnotics'
New-Item "$custom/systems" -ItemType Directory -Force | Out-Null
Copy-Item -LiteralPath $Logo -Destination "$custom/logo.png"
foreach($pair in @(@('FB NEO wallpaper.jpg','fbneo.jpg'),@('fb neo.png','fbneo.png'),@('mame_wallpaper.jpg','mame.jpg'),@('mame.png','mame.png'),@('windows_wallpaper.jpg','windows.jpg'),@('windows.png','windows.png'))) {
 Copy-Item -LiteralPath (Join-Path $MediaDirectory $pair[0]) -Destination (Join-Path "$custom/systems" $pair[1])
}
# Conserva también las seis imágenes originales sustituidas.
foreach($sys in @('fbneo','mame','windows')) {
 foreach($pair in @(@('background','jpg'),@('consoles','png'))) {
  $rel='art/'+$pair[0]+'/'+$sys+'.'+$pair[1]
  $backup=Join-Path "$out/originales/sustituidos" $rel
  New-Item (Split-Path $backup) -ItemType Directory -Force | Out-Null
  Copy-Item (Join-Path $out $rel) $backup
  Copy-Item "$custom/systems/$sys.$($pair[1])" (Join-Path $out $rel) -Force
 }
}
# Los XML de origen se conservan antes de aplicar correcciones.
$t=[IO.File]::ReadAllText((Join-Path $out 'theme.xml'))
$t=$t.Replace('./lang/gr.xml','./lang/el.xml')
$t=$t.Replace('</theme>','  <include>./tecnotics.xml</include>' + "`n</theme>")
[IO.File]::WriteAllText((Join-Path $out 'theme.xml'),$t,[Text.UTF8Encoding]::new($false))
# Copia exacta del principal original para comprobar su conservación.
$stream=[IO.Compression.ZipFile]::OpenRead((Resolve-Path -LiteralPath $SourceZip))
New-Item "$out/originales" -ItemType Directory -Force | Out-Null
try { [IO.Compression.ZipFileExtensions]::ExtractToFile($stream.GetEntry('es-theme-AluBrush/theme.xml'),"$out/originales/theme.xml",$false) } finally { $stream.Dispose() }
Copy-Item "$out/_splash.xml" "$out/originales/_splash.xml"
$s=[IO.File]::ReadAllText("$out/_splash.xml").Replace('./art/colors/','./subsets/colorsets/').Replace('${cyan}>','${cyan}').Replace('${orange}>','${orange}')
$s=$s.Replace(':/logo.png','./art/tecnotics/logo.png').Replace('<minSize>1 1</minSize>','<maxSize>0.65 0.4</maxSize>')
[IO.File]::WriteAllText("$out/_splash.xml",$s,[Text.UTF8Encoding]::new($false))
$gameSplash=Join-Path $out 'gamesplash.xml'
New-Item "$out/originales/sustituidos" -ItemType Directory -Force | Out-Null
Copy-Item $gameSplash "$out/originales/sustituidos/gamesplash.xml"
$gameText=[IO.File]::ReadAllText($gameSplash)
$badge='<image name="tecnoticsBrand" extra="true"><path>${themePath}/art/tecnotics/logo.png</path><pos>0.5 0.12</pos><origin>0.5 0.5</origin><maxSize>0.35 0.12</maxSize><zIndex>150</zIndex></image>'
$gameText=$gameText.Replace('</view>',$badge+'</view>')
[IO.File]::WriteAllText($gameSplash,$gameText,[Text.UTF8Encoding]::new($false))
Copy-Item (Join-Path $PSScriptRoot 'tema-retrobat/tecnotics.xml') "$out/tecnotics.xml"
Copy-Item (Join-Path $PSScriptRoot 'tema-retrobat/CREDITOS.md') "$out/CREDITOS.md"
$manifest | ConvertTo-Json -Depth 3 | Set-Content "$out/originales/manifest.json" -Encoding utf8
[pscustomobject]@{sourceZipSha256=(Get-FileHash -LiteralPath $SourceZip).Hash.ToLower();originalFiles=$manifest.Count;theme='Tecnotics AluBrush RetroBat 1.0'} | ConvertTo-Json | Set-Content "$out/originales/procedencia.json" -Encoding utf8
& (Join-Path $PSScriptRoot 'Normalizar-Rutas-Tema.ps1') -ThemeDirectory $out
# Git debe conservar los bytes exactos, incluidos saltos de línea, del manifiesto.
Copy-Item "$out/.gitattributes" "$out/originales/sustituidos/.gitattributes.original"
[IO.File]::WriteAllText("$out/.gitattributes","* -text`n",[Text.UTF8Encoding]::new($false))
Write-Output "Tema construido: $out ($($manifest.Count) archivos de origen conservados)"





