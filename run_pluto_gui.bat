@echo off
python - <<PY
import importlib, sys
modules = ["PySide6", "pyqtgraph", "numpy", "scipy", "adi", "iio", "sigmf"]
missing = []
for mod in modules:
    try:
        importlib.import_module(mod)
    except Exception:
        missing.append(mod)

if missing:
    print("Missing dependencies: " + ", ".join(missing))
    sys.exit(1)
PY
if %ERRORLEVEL% NEQ 0 (
    echo Please install missing dependencies with pip install -r requirements.txt
    pause
    exit /b %ERRORLEVEL%
)
python "%~dp0main.py"
