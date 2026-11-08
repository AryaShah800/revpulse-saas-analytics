param([string]$NodeExecutable,[string]$NodeModules,[string]$BundledPython)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $NodeExecutable -or -not $NodeModules -or -not $BundledPython) {
    throw 'Supply the Node executable, Node modules directory and Python executable returned by load_workspace_dependencies.'
}
$buildDir = Join-Path $projectRoot '.local\artifact'
New-Item -ItemType Directory -Force $buildDir | Out-Null
if (-not (Test-Path (Join-Path $buildDir 'node_modules'))) {
    New-Item -ItemType Junction -Path (Join-Path $buildDir 'node_modules') -Target $NodeModules | Out-Null
}
& (Join-Path $projectRoot '.venv\Scripts\python.exe') (Join-Path $PSScriptRoot 'prepare_workbook.py')
if ($LASTEXITCODE) { throw 'Workbook input export failed' }
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'build_workbook.mjs') -Destination (Join-Path $buildDir 'build_workbook.mjs') -Force
& $NodeExecutable (Join-Path $buildDir 'build_workbook.mjs')
if ($LASTEXITCODE) { throw 'Artifact workbook export failed' }
& $BundledPython (Join-Path $PSScriptRoot 'add_native_pivots.py')
if ($LASTEXITCODE) { throw 'Native pivot packaging failed' }
& $BundledPython (Join-Path $PSScriptRoot 'verify_artifacts.py')
if ($LASTEXITCODE) { throw 'Workbook validation failed' }
