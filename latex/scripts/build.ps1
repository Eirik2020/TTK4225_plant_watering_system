[CmdletBinding()]
param(
    [switch]$Clean,
    [switch]$Docker,
    [switch]$Native,
    [string]$DockerImage = 'ghcr.io/xu-cheng/texlive-historic-debian:2024'
)

$ErrorActionPreference = 'Stop'

if ($Docker -and $Native) {
    throw 'Choose either -Docker or -Native, not both.'
}

$reportDir = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$buildDir = Join-Path $reportDir 'build'
$distDir = Join-Path $reportDir 'dist'
$pdfSource = Join-Path $buildDir 'main.pdf'
$pdfDestination = Join-Path $distDir 'report.pdf'

if ($Clean) {
    if (Test-Path -LiteralPath $buildDir) {
        Remove-Item -LiteralPath $buildDir -Recurse -Force
    }
    if (Test-Path -LiteralPath $pdfDestination) {
        Remove-Item -LiteralPath $pdfDestination -Force
    }
    Write-Host 'Removed report build output.'
    exit 0
}

$latexmk = Get-Command latexmk -ErrorAction SilentlyContinue
$useDocker = $Docker -or (-not $Native -and -not $latexmk)

if ($Native -and -not $latexmk) {
    throw 'latexmk was not found. Install TeX Live/MiKTeX or use -Docker.'
}

New-Item -ItemType Directory -Force $buildDir, $distDir | Out-Null
Push-Location $reportDir

try {
    if ($useDocker) {
        if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
            throw 'Docker was not found. Install Docker or a native TeX distribution.'
        }

        $savedErrorPreference = $ErrorActionPreference
        $ErrorActionPreference = 'SilentlyContinue'
        & docker info --format '{{.ServerVersion}}' 2>$null | Out-Null
        $dockerInfoExitCode = $LASTEXITCODE
        $ErrorActionPreference = $savedErrorPreference
        if ($dockerInfoExitCode -ne 0) {
            throw 'Docker is installed but its engine is not running. Start Docker Desktop and retry.'
        }

        Write-Host "Building with Docker image $DockerImage"
        & docker run --rm --volume "${reportDir}:/work" --workdir /work $DockerImage `
            latexmk main.tex
    }
    else {
        Write-Host 'Building with the native TeX installation'
        & latexmk main.tex
    }

    if ($LASTEXITCODE -ne 0) {
        throw "LaTeX build failed with exit code $LASTEXITCODE."
    }

    if (-not (Test-Path -LiteralPath $pdfSource)) {
        throw "The build completed without producing $pdfSource."
    }

    Copy-Item -LiteralPath $pdfSource -Destination $pdfDestination -Force
    Write-Host "Created $pdfDestination"
}
finally {
    Pop-Location
}
