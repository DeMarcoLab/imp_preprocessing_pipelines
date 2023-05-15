from fastapi import FastAPI
import subprocess

# Instantiate app
app = FastAPI()

# Root call
@app.get("/")
def read_root():
    return {"status": "ready"}

# Insecure use for testing only
# Passthrough commands
@app.get("/run")
def run(command: str):
    p = subprocess.run(command, shell=True, capture_output=True)
    return {
        "return_code": p.returncode,
        "stdout": p.stdout,
        "stderr": p.stderr
    }
