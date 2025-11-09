# tests/conftest.py
import os
import sys
from pathlib import Path

# Абсолютный путь к корню репозитория: <repo_root>/
THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[1]

# В начало sys.path — чтобы `import modules` всегда работал
sys.path.insert(0, str(REPO_ROOT))

# На всякий случай выставим CWD в корень репозитория (иногда это важно для путей к файлам)
os.chdir(REPO_ROOT)
