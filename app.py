from flask import Flask, request, send_file
from flask_cors import CORS
import subprocess, uuid, os, shutil, io

app = Flask(__name__)
CORS(app)

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

    # Initialize container out of try scope
    img_data = None

    try:
        file_path = f"{path}/input.asy"
        with open(file_path, "w") as f:
            f.write(code)

        result = subprocess.run(
            ["asy", "-f", "png", "-render=4", "input.asy"],
            cwd=path,
            timeout=3,
            capture_output=True,
            text=True
        )

        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        print("RETURN CODE:", result.returncode)

        if result.returncode != 0:
            return {
                "error": "Asymptote error",
                "stdout": result.stdout,
                "stderr": result.stderr
            }, 400

        # FIX: Read file completely into memory before the finally cleanup runs
        with open(f"{path}/input.png", "rb") as img_file:
            img_data = io.BytesIO(img_file.read())

    except subprocess.TimeoutExpired:
        return "Timeout", 400
    except FileNotFoundError:
        return "Compiled image file missing", 500
    finally:
        shutil.rmtree(path, ignore_errors=True)

    # Stream out of the memory buffer instead of the disk file
    return send_file(img_data, mimetype="image/png")
