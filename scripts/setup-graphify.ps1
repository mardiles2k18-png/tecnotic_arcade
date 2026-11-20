# Tecnotics Arcade: instala Graphify e integra Codex y Claude en cada PC Windows.
# Ejecutar desde la carpeta del repositorio:
# powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-graphify.ps1
[CmdletBinding()]
param([switch]$SkipExtract)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Push-Location $repo
try {
    # uv es suficiente: administra su propio Python compatible con graphifyy.
    $uvCmd = Get-Command uv -ErrorAction SilentlyContinue
    if (-not $uvCmd) {
        $candidateUv = Join-Path $HOME '.local\bin\uv.exe'
        if (Test-Path $candidateUv) { $env:PATH = "$(Split-Path $candidateUv);$env:PATH" }
        $uvCmd = Get-Command uv -ErrorAction SilentlyContinue
    }
    if (-not $uvCmd) {
        if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
            throw "No se encontró uv ni winget. Instala uv desde https://docs.astral.sh/uv/ y vuelve a ejecutar el script."
        }
        Write-Host "Instalando uv con winget para este usuario..."
        winget install --id astral-sh.uv --exact --scope user --accept-source-agreements --accept-package-agreements
        if ($LASTEXITCODE -ne 0) {
            throw "Falló winget. Abre PowerShell sin privilegios de administrador y repite la instalación."
        }
        foreach ($dir in @((Join-Path $HOME '.local\bin'), (Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Links'))) {
            if ((Test-Path $dir) -and (($env:PATH -split ';') -notcontains $dir)) { $env:PATH = "$dir;$env:PATH" }
        }
        $uvCmd = Get-Command uv -ErrorAction SilentlyContinue
        if (-not $uvCmd) { throw "uv se instaló, pero necesita reiniciar PowerShell para actualizar PATH. Luego repite este script." }
    }

    $installed = (& uv tool list 2>&1 | Out-String)
    if ($LASTEXITCODE -ne 0) { throw "No se pudo revisar la instalación de herramientas UV." }
    if ($installed -notmatch '(?m)^graphifyy(?:\s|$)') {
        Write-Host "Instalando graphifyy..."
        & uv tool install graphifyy
        if ($LASTEXITCODE -ne 0) { throw "Falló la instalación de graphifyy." }
    } else {
        Write-Host "graphifyy ya está instalado. No se reinstalará."
    }

    $bin = Join-Path $HOME '.local\bin'
    if ((Test-Path $bin) -and (($env:PATH -split ';') -notcontains $bin)) { $env:PATH = "$bin;$env:PATH" }
    if (-not (Get-Command graphify -ErrorAction SilentlyContinue)) {
        throw "graphify no está disponible. Ejecuta 'uv tool update-shell', reinicia PowerShell y repite."
    }

    & graphify install --platform codex
    if ($LASTEXITCODE -ne 0) { throw "Error instalando la skill de Codex." }
    & graphify install --platform claude
    if ($LASTEXITCODE -ne 0) { throw "Error instalando la skill de Claude Code." }

    if (-not $SkipExtract) {
        Write-Host "Generando grafo local sin llamadas API (--code-only)..."
        & graphify extract . --code-only
        if ($LASTEXITCODE -ne 0) { throw "Error al generar el grafo local." }
        if (-not (Test-Path 'graphify-out\graph.json')) { throw "No se creó graphify-out\graph.json." }
    }
    Write-Host "OK: Graphify configurado para esta cuenta de Windows y este checkout."
    Write-Host "Consulta: graphify query 'RetroBat' --budget 1000 --depth 2"
}
finally { Pop-Location }
