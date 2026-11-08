param([string]$VerificationRoot = 'D:\RevPulseRuntime\verification')
$ErrorActionPreference = 'Stop'
$sourceRoot = Split-Path -Parent $PSScriptRoot
if (Test-Path -LiteralPath $VerificationRoot) { throw 'Use a new empty verification directory to preserve prior evidence.' }
New-Item -ItemType Directory -Path $VerificationRoot | Out-Null
foreach ($name in @('src','sql','tests','config','scripts')) {
    Copy-Item -LiteralPath (Join-Path $sourceRoot $name) -Destination $VerificationRoot -Recurse
}
foreach ($name in @('pyproject.toml','requirements-lock.txt')) {
    Copy-Item -LiteralPath (Join-Path $sourceRoot $name) -Destination $VerificationRoot
}
New-Item -ItemType Directory -Path (Join-Path $VerificationRoot '.local') | Out-Null
Copy-Item -LiteralPath (Join-Path $sourceRoot '.local\database.json') -Destination (Join-Path $VerificationRoot '.local\database.json')
$env:TEMP='D:\RevPulseRuntime\temp'
$env:TMP='D:\RevPulseRuntime\temp'
python -m venv (Join-Path $VerificationRoot '.venv')
if ($LASTEXITCODE) { throw 'Clean virtual environment creation failed' }
$pythonExe=Join-Path $VerificationRoot '.venv\Scripts\python.exe'
& $pythonExe -m pip install --no-cache-dir -r (Join-Path $VerificationRoot 'requirements-lock.txt')
if ($LASTEXITCODE) { throw 'Locked dependency installation failed' }
& $pythonExe -m pip install --no-deps -e $VerificationRoot
if ($LASTEXITCODE) { throw 'Package installation failed' }
Push-Location $VerificationRoot
try {
    & $pythonExe -m pytest tests -q --junitxml=reports/fresh_tests.xml
    if ($LASTEXITCODE) { throw 'Fresh-environment tests failed' }
    & $pythonExe -m revpulse.cli all --workspace $VerificationRoot
    if ($LASTEXITCODE) { throw 'Fresh-environment pipeline failed' }
} finally { Pop-Location }
Copy-Item -LiteralPath (Join-Path $VerificationRoot 'reports\fresh_tests.xml') -Destination (Join-Path $sourceRoot 'reports\fresh_environment_tests.xml')
Write-Output 'Fresh environment installation, tests, PostgreSQL pipeline, training and scoring passed.'
