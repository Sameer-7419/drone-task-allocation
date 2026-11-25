# Install dependencies into the interpreter that Webots is configured to use.
# Override this when Webots uses a non-default interpreter, for example:
# .\install_dependencies.ps1 -PythonExecutable "C:\Python312\python.exe"
param([string]$PythonExecutable = "")

if (-not $PythonExecutable) {
    $command = Get-Command python -ErrorAction SilentlyContinue
    if ($command) { $PythonExecutable = $command.Source }
}

if (-not $PythonExecutable -or -not (Test-Path $PythonExecutable)) {
    Write-Error "No Python interpreter was found. Pass -PythonExecutable with the interpreter configured in Webots."
    exit 1
}

& $PythonExecutable -m pip install --upgrade pip
& $PythonExecutable -m pip install numpy torch

if ($LASTEXITCODE -ne 0) {
    Write-Error "NumPy installation failed."
    exit $LASTEXITCODE
}

& $PythonExecutable -c "import numpy, torch; print('NumPy OK:', numpy.__version__); print('PyTorch OK:', torch.__version__)"
