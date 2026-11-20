# Prepara Graphify en Windows desde cualquier carpeta de trabajo.
# Uso: powershell -ExecutionPolicy Bypass -File .\scripts\setup-graphify.ps1
[CmdletBinding()]
param([switch]$SkipExtract)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Push-Location $repo
try {
    $uv = Get-Command uv -ErrorAction SilentlyContinue
    if (-not $uv) {
        throw "Falta uv. Instálalo con: winget install astral-sh.uv (PowerShell sin administrador), y abre otra terminal."
    }
    uv tool install graphifyy
    if ($LASTEXITCODE -ne 0) { throw "Falló la instalación de graphifyy." }

    $candidate = Join-Path $HOME '.local\bin'
    if ((Test-Path $candidate) -and ($env:PATH -split ';' -notcontains $candidate)) {
        $env:PATH = "$candidate;$env:PATH"
    }
    $graphify = Get-Command graphify -ErrorAction SilentlyContinue
    if (-not $graphify) { throw "No se encuentra graphify. Prueba: uv tool update-shell y reinicia PowerShell." }

    # Integración en el perfil del usuario (Codex y Claude ya pueden tenerla).
    graphify install --platform codex
    if ($LASTEXITCODE -ne 0) { throw "Falló la integración con Codex." }
    graphify install --platform claude
    if ($LASTEXITCODE -ne 0) { throw "Falló la integración con Claude Code." }

    if (-not $SkipExtract) {
        graphify extract . --code-only
        if ($LASTEXITCODE -ne 0) { throw "Falló la construcción del grafo." }
    }
    Write-Host "Graphify listo en $repo"
    Write-Host "Ejemplo: graphify query 'scripts RetroBat' --budget 1000 --depth 2"
}
finally {
    Pop-Location
}
