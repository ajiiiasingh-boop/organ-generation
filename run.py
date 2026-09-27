"""
Start the Anatomical Matrix Generator with one command:

    python run.py

It checks that the libraries the app needs are installed (and new enough),
installs anything missing, then starts the website — the same as typing
`streamlit run app.py`. Press Ctrl + C in the terminal to stop it.
"""

import importlib.metadata
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# package name -> oldest version the app works with
REQUIRED = {
    "streamlit": (1, 64),
    "pandas": (2, 2),
    "numpy": (1, 26),
    "matplotlib": (3, 8),
    "plotly": (5, 24),
}


def installed_version(package):
    """(major, minor) of an installed package, or None if it isn't installed."""
    try:
        text = importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None
    numbers = []
    for part in text.split(".")[:2]:
        digits = "".join(ch for ch in part if ch.isdigit())
        numbers.append(int(digits) if digits else 0)
    return tuple(numbers)


def main():
    to_install = []
    for package, minimum in REQUIRED.items():
        version = installed_version(package)
        if version is None or version < minimum:
            to_install.append(f"{package}>={minimum[0]}.{minimum[1]}")

    if to_install:
        print("Installing / updating:", ", ".join(to_install))
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", *to_install])

    print("Starting the app — it will open in your browser. Press Ctrl + C here to stop it.")
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", str(HERE / "app.py")], cwd=HERE)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
