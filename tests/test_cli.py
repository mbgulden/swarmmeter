import subprocess
import sys


def test_cli_help():
    result = subprocess.run([sys.executable, "-m", "swarmmeter.cli", "--help"], capture_output=True, text=True, check=False)
    assert result.returncode == 0
    assert "Swarmmeter CLI" in result.stdout

def test_cli_status():
    result = subprocess.run([sys.executable, "-m", "swarmmeter.cli", "status"], capture_output=True, text=True, check=False)
    assert result.returncode == 0
    assert "Status: OK" in result.stdout
