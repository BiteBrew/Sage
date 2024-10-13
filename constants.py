import os
from pathlib import Path

HOME_DIR = str(Path.home())
SAGE_DIR = os.path.join(HOME_DIR, '.sage')
CAPTURE_FILE = os.path.join(SAGE_DIR, 'capture.png')