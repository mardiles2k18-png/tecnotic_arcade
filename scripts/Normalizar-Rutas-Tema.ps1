param([Parameter(Mandatory=$true)][string]$ThemeDirectory)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath($ThemeDirectory)
foreach($file in Get-ChildItem $root -Recurse -File -Filter *.xml | Where-Object {$_.FullName -notlike "$root\originales\*" -and $_.Name -ne 'tecnotics.xml'}) {
 $old=[IO.File]::ReadAllText($file.FullName)
 $new=[regex]::Replace($old,'(?<=>)(?:\./|\.\./)+art/([^<]+)(?=<)','${themePath}/art/$1')
 foreach($name in @('white.png','darkwheel.png','centerfade_v.png')) { $new=$new.Replace('./../'+$name,'${themePath}/art/'+$name) }
 if($new -ne $old) {
  $rel=$file.FullName.Substring($root.Length+1)
  $backup=Join-Path "$root/originales/sustituidos" $rel
  if($rel -notin @('theme.xml','_splash.xml') -and !(Test-Path $backup)) {New-Item (Split-Path $backup) -ItemType Directory -Force | Out-Null; Copy-Item -LiteralPath $file.FullName -Destination $backup}
  [IO.File]::WriteAllText($file.FullName,$new,[Text.UTF8Encoding]::new($false))
 }
}
