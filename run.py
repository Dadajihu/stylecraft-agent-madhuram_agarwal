"""
Entry point for the RetailMind Product Intelligence Agent.
Run this file to launch the Streamlit application:
    python run.py
"""

import subprocess
import sys

if __name__ == "__main__":
    subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"])
