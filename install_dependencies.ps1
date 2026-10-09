# Install dependencies into the Python interpreter used by Webots R2025a.
$python = "C:\Users\Sameer Gupta\AppData\Local\Programs\Python\Python313\python.exe"

if (-not (Test-Path $python)) {
    Write-Error "Python 3.13 was not found at: $python"
    Write-Host "Run: where.exe python"
    exit 1
}

& $python -m pip install --upgrade pip
& $python -m pip install numpy

if ($LASTEXITCODE -ne 0) {
    Write-Error "NumPy installation failed."
    exit $LASTEXITCODE
}

& $python -c "import numpy; print('NumPy OK:', numpy.__version__)"
