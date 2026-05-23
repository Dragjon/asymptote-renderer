from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import subprocess, uuid, os, shutil, io

app = Flask(__name__)
CORS(app)

def error_response(error_type, message, status=400, extra=None):
    payload = {
        "status": "error",
        "type": error_type,
        "message": message
    }
    if extra:
        payload.update(extra)
    return jsonify(payload), status


@app.route("/render", methods=["POST"])
def render():
    data = request.get_json(silent=True)

    if not data or "code" not in data:
        return error_response(
            "invalid_request",
            "Missing 'code' field in request body"
        )

    code = data["code"]

    if len(code) > 50000:
        return error_response(
            "payload_too_large",
            "Asymptote code exceeds 50,000 characters",
            extra={"limit": 50000, "received": len(code)}
        )

    job_id = str(uuid.uuid4())
    path = f"/tmp/{job_id}"
    os.mkdir(path)

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
            return error_response(
                "asymptote_error",
                "Asymptote compilation failed",
                extra={
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "return_code": result.returncode
                }
            )

        img_path = f"{path}/input.png"

        if not os.path.exists(img_path):
            return error_response(
                "missing_output",
                "Asymptote did not produce output image",
                extra={"expected_file": img_path}
            )

        with open(img_path, "rb") as img_file:
            img_data = io.BytesIO(img_file.read())

        return send_file(img_data, mimetype="image/png")

    except subprocess.TimeoutExpired:
        return error_response(
            "timeout",
            "Asymptote rendering exceeded time limit",
            extra={"limit_seconds": 3}
        )

    except Exception as e:
        return error_response(
            "internal_error",
            "Unexpected server error",
            status=500,
            extra={"exception": str(e)}
        )

    finally:
        shutil.rmtree(path, ignore_errors=True)