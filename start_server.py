import subprocess
import time

# Start FastAPI server
api_process = subprocess.Popen(["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"])

# Give it time to start
time.sleep(3)

print("Server started")
