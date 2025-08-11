import subprocess
import time
import sys
import os

# Start FastAPI backend (app.py) using uvicorn
backend = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "8000"],
    cwd=os.path.dirname(__file__)
)

# Wait a bit to ensure backend is up
time.sleep(2)

try:
    # Start Gradio frontend
    subprocess.run([sys.executable, "gradio_frontend.py"], cwd=os.path.dirname(__file__))
finally:
    # Terminate backend when done
    backend.terminate()