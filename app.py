from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import subprocess, uuid, os, shutil, io

app = Flask(__name__)

CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    allow_headers=["Content-Type"],
    methods=["GET", "POST", "OPTIONS"]
)

# ── Bundle olympiad.asy inline so Render doesn't need it installed ──────────
OLYMPIAD_ASY = r"""
// Olympiad Asymptote Package — By Maria Monks and AoPS community
include graph;
include math;
real markscalefactor=0.03;
pair origin; origin=(0,0);
pair waypoint(path p, real r){ return point(p,reltime(p,r)); }
pair midpoint(path p){ return waypoint(p,.5); }
pair foot(pair P, pair A, pair B){
    real s=dot(P-A,unit(B-A));
    return (scale(s)*unit(B-A)+A);
}
pair bisectorpoint(pair A ... pair[] BC){
    pair P,B,C,M;
    if(BC.length==1){ B=BC[0]; M=midpoint(A--B); P=unit(rotate(90,M)*A-M)+M; }
    else if(BC.length==2){ B=BC[0]; C=BC[1]; P=unit(midpoint((unit(A-B)+B)--(unit(C-B)+B))-B)+B; }
    return P;
}
pair circumcenter(pair A=(0,0), pair B=(0,0), pair C=(0,0)){
    pair M=midpoint(A--B), N=midpoint(B--C);
    return extension(M,rotate(90,M)*A,N,rotate(90,N)*B);
}
real circumradius(pair A, pair B, pair C){ return abs(circumcenter(A,B,C)-A); }
guide circumcircle(pair A=(0,0), pair B=(0,0), pair C=(0,0)){
    return Circle(circumcenter(A,B,C),circumradius(A,B,C));
}
pair incenter(pair A=(0,0), pair B=(0,0), pair C=(0,0)){
    pair P=rotate((angle(C-A)-angle(B-A))*90/pi,A)*B;
    pair Q=rotate((angle(A-B)-angle(C-B))*90/pi,B)*C;
    return extension(A,P,B,Q);
}
real inradius(pair A, pair B, pair C){
    real a=abs(B-C), b=abs(A-C), c=abs(B-A), s=(a+b+c)/2;
    return sqrt(s*(s-a)*(s-b)*(s-c))/s;
}
guide incircle(pair A=(0,0), pair B=(0,0), pair C=(0,0)){
    return Circle(incenter(A,B,C),inradius(A,B,C));
}
pair tangent(pair P, pair O, real r, int n=1){
    real d=abs(P-O); if(d<r) return O;
    real R=sqrt(d^2-r^2);
    pair X=intersectionpoint(circle(O,r),O--P), T;
    if(n==1) T=intersectionpoint(circle(P,R),Arc(O,r,degrees(X-O),degrees(X-O)+180));
    else if(n==2) T=intersectionpoint(circle(P,R),Arc(O,r,degrees(X-O)+180,degrees(X-O)+360));
    else T=O;
    return T;
}
bool cyclic(pair A, pair B, pair C, pair D){
    return abs(circumcenter(A,B,C).x-circumcenter(A,B,D).x)<1/10^5
        && abs(circumcenter(A,B,C).y-circumcenter(A,B,D).y)<1/10^5;
}
bool concurrent(pair A, pair B, pair C, pair D, pair E, pair F){
    return (abs(extension(A,B,C,D).x-extension(C,D,E,F).x)<1/10^5
         && abs(extension(A,B,C,D).y-extension(C,D,E,F).y)<1/10^5)
        || (extension(A,B,C,D)==(infinity,infinity) && (infinity,infinity)==extension(C,D,E,F));
}
bool collinear(pair A, pair B, pair C){
    return A==B || B==C || A==C
        || abs(unit(B-A)-unit(C-A))<1/10^5
        || abs(unit(B-A)+unit(C-A))<1/10^5;
}
pair centroid(pair A, pair B, pair C){ return (A+B+C)/3; }
pair orthocenter(pair A, pair B, pair C){
    return extension(A,foot(A,B,C),B,foot(B,A,C));
}
path rightanglemark(pair A, pair B, pair C, real s=8){
    pair P=s*markscalefactor*unit(A-B)+B;
    pair R=s*markscalefactor*unit(C-B)+B;
    return P--(P+R-B)--R;
}
path anglemark(pair A, pair B, pair C, real t=8 ... real[] s){
    pair M=t*markscalefactor*unit(A-B)+B, N=t*markscalefactor*unit(C-B)+B;
    path mark=arc(B,M,N); int n=s.length;
    pair[] P,Q;
    for(int i=0;i<n;++i){ P[i]=s[i]*markscalefactor*unit(A-B)+B; Q[i]=s[i]*markscalefactor*unit(C-B)+B; }
    for(int i=0;i<n;++i){
        if(i%2==0) mark=mark--reverse(arc(B,P[i],Q[i]));
        else mark=mark--arc(B,P[i],Q[i]);
    }
    if(n%2==0 && n!=0) mark=(mark--B--P[n-1]);
    else if(n!=0) mark=(mark--B--Q[n-1]);
    else mark=(mark--B--cycle);
    return mark;
}
picture pathticks(path g, int n=1, real r=.5, real spacing=6, real s=8, pen p=currentpen){
    picture pict;
    real l=arclength(g), space=spacing*markscalefactor, halftick=s*markscalefactor/2;
    real startpt=r*l-(n-1)/2*space;
    for(int i=0;i<n;++i){
        real t=startpt+i*space;
        pair direct=unit(dir(g,arctime(g,r*l)));
        pair B=point(g,arctime(g,t))+(0,1)*halftick*direct;
        draw(pict,B--(B+2*(0,-1)*halftick*direct),p);
    }
    return pict;
}
"""

# ── Write bundled packages to a temp dir once at startup ────────────────────
PKG_DIR = "/tmp/asy-packages"
os.makedirs(PKG_DIR, exist_ok=True)
with open(f"{PKG_DIR}/olympiad.asy", "w") as f:
    f.write(OLYMPIAD_ASY)
# cse5 is also common — write a minimal stub so import doesn't error
CSE5_STUB = r"""
// cse5 stub — minimal definitions to avoid import errors
import olympiad;
"""
with open(f"{PKG_DIR}/cse5.asy", "w") as f:
    f.write(CSE5_STUB)

PRELUDE = r"""
settings.outformat = "png";
defaultpen(linewidth(0.8));
import graph;
import geometry;
import math;
pair O = (0,0);
pair origin = (0,0);
pair midpoint(pair A, pair B) { return (A+B)/2; }
pair foot(pair P, pair A, pair B) { return projection(A,B)*P; }
pair reflectline(pair P, pair A, pair B) { pair F=foot(P,A,B); return 2F-P; }
pair rotatearound(pair P, pair C, real angle) { return rotate(angle,C)*P; }
pair dirdeg(real angle) { return dir(angle); }
void drawpoly(pair[] pts, pen p=currentpen) {
    for(int i=0; i<pts.length; ++i) draw(pts[i]--pts[(i+1)%pts.length], p);
}
void dotlabel(string s, pair P, pair dir=NE) { dot(P); label(s, P, dir); }
pen invisible = opacity(0);
size(250);
"""

def error_response(error_type, message, status=400, extra=None):
    payload = {"status": "error", "type": error_type, "message": message}
    if extra:
        payload.update(extra)
    response = jsonify(payload)
    response.status_code = status
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

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
        return error_response("invalid_request", "Missing 'code' field in request body")
    code = data["code"]
    if len(code) > 50000:
        return error_response("payload_too_large", "Asymptote code exceeds 50,000 characters",
                              extra={"limit": 50000, "received": len(code)})

    code = PRELUDE + "\n" + code

    job_id = str(uuid.uuid4())
    path = f"/tmp/{job_id}"
    os.mkdir(path)

    try:
        with open(f"{path}/input.asy", "w") as f:
            f.write(code)

        env = os.environ.copy()
        # Tell Asymptote to look in our package dir for olympiad, cse5, etc.
        env["ASYMPTOTE_DIR"] = PKG_DIR

        result = subprocess.run(
            ["asy", "-f", "png", "-render=4", "input.asy"],
            cwd=path,
            timeout=10,
            capture_output=True,
            text=True,
            env=env
        )

        if result.returncode != 0:
            return error_response(
                "asymptote_error", "Asymptote compilation failed",
                extra={"stdout": result.stdout, "stderr": result.stderr,
                       "return_code": result.returncode}
            )

        img_path = f"{path}/input.png"
        if not os.path.exists(img_path):
            return error_response("missing_output", "Asymptote did not produce output image")

        with open(img_path, "rb") as img_file:
            img_data = io.BytesIO(img_file.read())

        response = send_file(img_data, mimetype="image/png")
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response

    except subprocess.TimeoutExpired:
        return error_response("timeout", "Asymptote rendering exceeded time limit",
                              extra={"limit_seconds": 10})
    except Exception as e:
        return error_response("internal_error", "Unexpected server error",
                              status=500, extra={"exception": str(e)})
    finally:
        shutil.rmtree(path, ignore_errors=True)