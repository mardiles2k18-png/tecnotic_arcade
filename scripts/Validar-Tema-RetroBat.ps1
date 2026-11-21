param([Parameter(Mandatory=$true)][string]$ThemeDirectory)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath($ThemeDirectory)
$errors=@(); $warnings=@(); $xmlCount=0; $checked=0
if(!(Test-Path "$root/theme.xml")) { throw 'Falta theme.xml principal' }
$manifest=Get-Content "$root/originales/manifest.json" -Raw | ConvertFrom-Json
foreach($item in $manifest) {
 $candidate=Join-Path $root $item.path
 if($item.path -eq '.gitattributes') { $candidate=Join-Path $root 'originales/sustituidos/.gitattributes.original' }
 elseif($item.path -in @('theme.xml','_splash.xml')) { $candidate=Join-Path "$root/originales" $item.path }
 elseif(Test-Path (Join-Path "$root/originales/sustituidos" $item.path)) { $candidate=Join-Path "$root/originales/sustituidos" $item.path }
 if(!(Test-Path -LiteralPath $candidate)) { $errors+="Original ausente: $($item.path)"; continue }
 if((Get-FileHash -LiteralPath $candidate).Hash.ToLower() -ne $item.sha256) { $errors+="Original alterado sin copia: $($item.path)" }
 $checked++
}
foreach($file in Get-ChildItem $root -Recurse -File -Filter *.xml | Where-Object {$_.FullName -notlike "$root\originales\*"}) {
 try { [xml]$doc=Get-Content -LiteralPath $file.FullName -Raw } catch { $errors+="XML inválido: $($file.FullName)"; continue }
 $xmlCount++
 foreach($node in $doc.SelectNodes('//include|//fontPath')) {
  $value=$node.InnerText.Trim().Replace('${themePath}',$root); if(!$value -or $value -match '\$|\{|^:|^https?://') { continue }
  $target=if([IO.Path]::IsPathRooted($value)) { [IO.Path]::GetFullPath($value) } else { [IO.Path]::GetFullPath((Join-Path $file.DirectoryName $value)) }
  if(!(Test-Path -LiteralPath $target)) { $errors+="Referencia ausente: $($file.Name) -> $value" }
 }
 # Informar recursos estáticos ausentes sin rechazar rutas alternativas de imágenes.
 foreach($node in $doc.SelectNodes('//path|//imagePath|//gunPath|//wheelPath')) {
  $value=$node.InnerText.Trim().Replace('${themePath}',$root); if(!$value -or $value -eq 'none' -or $value -match '\$|\{|^:|^https?://') {continue}
  $target=if([IO.Path]::IsPathRooted($value)) { [IO.Path]::GetFullPath($value) } else { [IO.Path]::GetFullPath((Join-Path $file.DirectoryName $value)) }
  if(!(Test-Path -LiteralPath $target)) { $warnings+="$($file.FullName.Substring($root.Length+1)): $value" }
 }
}
foreach($system in @('fbneo','mame','windows')) {
 foreach($ext in @('jpg','png')) {if(!(Test-Path "$root/art/tecnotics/systems/$system.$ext")) {$errors+="Falta $system.$ext"}}
}
[pscustomobject]@{originalFiles=$manifest.Count;originalFilesVerified=$checked;activeXmlFiles=$xmlCount;errors=$errors;optionalResourceWarnings=$warnings;runtimeTest='Pendiente en RetroBat: la validación estática no prueba renderizado ni mandos.'} | ConvertTo-Json -Depth 4
if($errors.Count) {throw "Falló validación: $($errors.Count) errores"}



