"""Compatibility entry point: regenerate all 16 figures through the browser renderer."""
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "学术图像"


def main():
    npm = shutil.which("npm.cmd" if sys.platform == "win32" else "npm")
    if not npm:
        raise SystemExit("需要 Node.js/npm。安装后在 学术图像 中执行 npm ci。")
    if not (APP / "node_modules/vite/bin/vite.js").is_file():
        raise SystemExit("请先在 学术图像 目录执行 npm ci。")
    subprocess.run([sys.executable, str(APP / "scripts/prepare_data.py")], cwd=ROOT, check=True)
    subprocess.run([npm, "run", "build"], cwd=APP, check=True)
    subprocess.run([npm, "run", "export"], cwd=APP, check=True)


if __name__ == "__main__":
    main()
