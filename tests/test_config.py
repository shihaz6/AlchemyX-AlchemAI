import subprocess
import sys
from pathlib import Path

from alchemyx import config


def test_project_root():
    assert config.PROJECT_ROOT == Path(__file__).resolve().parents[1]


def test_dotenv_loaded_from_root():
    code = '''
from pathlib import Path
from unittest.mock import patch
with patch("dotenv.load_dotenv") as load:
    import alchemyx.config as config
    load.assert_called_once_with(config.PROJECT_ROOT / ".env")
'''
    import os
    env = dict(os.environ, PYTHONPATH=str(config.PROJECT_ROOT / "src"))
    subprocess.run([sys.executable, "-c", code], env=env, check=True)


def test_tesseract_override(monkeypatch):
    import importlib
    with monkeypatch.context() as patch:
        patch.setenv("TESSERACT_CMD", "/custom/tesseract")
        importlib.reload(config)
        assert config.TESSERACT_CMD == "/custom/tesseract"
    importlib.reload(config)
