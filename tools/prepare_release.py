import importlib.metadata
import shutil
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / "dist/ModelDock"
licenses = target / "licenses"
licenses.mkdir(parents=True, exist_ok=True)
for name in ["PySide6", "PySide6-Essentials", "shiboken6", "psutil", "pyinstaller"]:
    dist = importlib.metadata.distribution(name)
    folder = licenses / name
    folder.mkdir(exist_ok=True)
    for item in dist.files or []:
        source = Path(dist.locate_file(item))
        if source.is_file() and ".dist-info" in str(item) and any(word in source.name.upper() for word in ["LICENSE", "COPYING", "METADATA"]):
            shutil.copy2(source, folder / source.name)
python_license = Path(sys.base_prefix) / "LICENSE.txt"
if python_license.exists():
    shutil.copy2(python_license, licenses / "Python-LICENSE.txt")
for name in ["LGPL-3.0.txt", "GPL-3.0.txt"]:
    shutil.copy2(root / "licenses" / name, licenses / name)
for name in ["README.md", "THIRD_PARTY_NOTICES.md", "RELEASE_NOTES.md"]:
    shutil.copy2(root / name, target / name)
source = target / "source"
source.mkdir(exist_ok=True)
for name in ["modeldock", "tools", "tests", "licenses", "assets"]:
    shutil.copytree(root / name, source / name, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
for name in ["main.py", "requirements.txt", "requirements-dev.txt", "build.ps1", "README.md", "THIRD_PARTY_NOTICES.md", "RELEASE_NOTES.md"]:
    shutil.copy2(root / name, source / name)
print("Prepared portable release with notices and application source.")
