from flask import Flask, request, send_file
import subprocess, uuid, os, shutil

app = Flask(__name__)

@app.route("/render", methods=["POST"])
def render():
    data = request.get_json(silent=True)
    if not data or "code" not in data:
        return "Invalid request", 400

    code = data["code"]

    if len(code) > 50000:
        return "Too large", 400

    job_id = str(uuid.uuid4())
    path = f"/tmp/{job_id}"
    os.mkdir(path)

    try:
        file_path = f"{path}/input.asy"
        with open(file_path, "w") as f:
            f.write(code)

        result = subprocess.run(
            ["asy", "-f", "png", "input.asy"],
            cwd=path,
            timeout=3
        )

        if result.returncode != 0:
            return "Asymptote error", 400

        return send_file(f"{path}/input.png", mimetype="image/png")

    except subprocess.TimeoutExpired:
        return "Timeout", 400

    finally:
        shutil.rmtree(path, ignore_errors=True)