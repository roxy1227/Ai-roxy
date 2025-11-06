cd app

uv sync

uv pip uninstall torch torchvision torchaudio

uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130

echo Ok
pause