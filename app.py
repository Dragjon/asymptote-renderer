from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import subprocess, uuid, os, shutil, io

app = Flask(__name__)

# 🔥 STRONG CORS CONFIG (fixes preflight issues)
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    allow_headers=["Content-Type"],
    methods=["GET", "POST", "OPTIONS"]
)

PRELUDE = r"""
// ---------- Common settings ----------
settings.outformat = "png";
defaultpen(linewidth(0.8));

// ---------- Standard imports ----------
import graph;
import geometry;
import olympiad;
import math;
import fontsize;
import patterns;
import markers;
import palette;
import three;
import solids;
import contour;

// ---------- Common aliases ----------
pair O = (0,0);
pair origin = (0,0);

// ---------- Common constants ----------
real pi = 3.14159265358979323846;

// ---------- Utility helper functions ----------

// Distance squared
real norm2(pair P) {
    return P.x^2 + P.y^2;
}

// Midpoint fallback
pair midpoint(pair A, pair B) {
    return (A + B)/2;
}

// Foot of perpendicular fallback
pair foot(pair P, pair A, pair B) {
    return projection(A,B)*P;
}

// Reflection of P across line AB
pair reflectline(pair P, pair A, pair B) {
    pair F = foot(P,A,B);
    return 2F - P;
}

// Rotate point P around C by angle degrees
pair rotatearound(pair P, pair C, real angle) {
    return rotate(angle, C)*P;
}

// Unit direction vector from angle in degrees
pair dirdeg(real angle) {
    return dir(angle);
}

// ---------- Common drawing helpers ----------

// Safer dot labeling
void dotlabel(string s, pair P, pair dir=NE) {
    dot(P);
    label(s, P, dir);
}

// Safer draw polygon
void drawpoly(pair[] pts, pen p=currentpen) {
    for(int i=0; i<pts.length; ++i) {
        draw(pts[i]--pts[(i+1)%pts.length], p);
    }
}

// ---------- Frequently used colors ----------
pen invisible = opacity(0);

// ---------- Compatibility aliases ----------
pair footpoint(pair P, pair A, pair B) {
    return foot(P,A,B);
}

// ---------- Default size ----------
size(250);
"""

def error_response(error_type, message, status=400, extra=None):
    payload = {
        "status": "error",
        "type": error_type,
        "message": message
    }
    if extra:
        payload.update(extra)

    response = jsonify(payload)
    response.status_code = status

    # 🔥 ENSURE CORS EVEN ON ERRORS
    response.headers["Access-Control-Allow-Origin"] = "*"

    return response


# 🔥 EXPLICIT PRE-FLIGHT SUPPORT (important for Render)
@app.route("/render", methods=["OPTIONS"])
def render_options():
    response = jsonify({"status": "ok"})
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    return response


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

    # 🔥 inject safe runtime
    code = PRELUDE + "\n" + code

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
            timeout=10,
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

        response = send_file(img_data, mimetype="image/png")

        # 🔥 CORS on success too
        response.headers["Access-Control-Allow-Origin"] = "*"

        return response

    except subprocess.TimeoutExpired:
        return error_response(
            "timeout",
            "Asymptote rendering exceeded time limit",
            extra={"limit_seconds": 10}
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