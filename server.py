"""
server.py — local web server for the POD Go patch agent.

Run:  python server.py   (then open http://localhost:8000)

Everything stays on your machine: the UI talks to this server, this server
talks to your local Ollama. No data leaves the box.
"""

import io
import os
import uuid
import copy

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import patch_engine as pe
import agent

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(HERE, "template_newpreset.pgp")

app = FastAPI(title="POD Go Patch Agent")

# In-memory sessions: id -> {patch, history}. Fine for a single local user.
SESSIONS = {}


def _new_session(patch, is_build=False, base_patch=None):
    sid = uuid.uuid4().hex[:12]
    SESSIONS[sid] = {"patch": patch, "history": [], "is_build": is_build,
                     "base_patch": base_patch}
    return sid


def _load_template():
    with open(TEMPLATE_PATH, "rb") as f:
        return pe.load_patch(f.read())


def _state(sid):
    s = SESSIONS.get(sid)
    if not s:
        raise HTTPException(404, "Unknown session. Reload the page.")
    return s


def _chain_payload(patch):
    s = pe.summarize(patch)
    return {"name": s["name"], "tempo": s["tempo"],
            "snapshots": s["snapshots"], "blocks": s["blocks"],
            "chain_text": pe.chain_text(patch)}


# ─── Models ───
class ChatIn(BaseModel):
    session_id: str
    message: str
    model: str | None = None
    build: bool = False


# ─── Routes ───
@app.get("/", response_class=HTMLResponse)
def index():
    with open(os.path.join(HERE, "static", "index.html"), encoding="utf-8") as f:
        return f.read()


@app.post("/api/new")
def new_from_template():
    """Start a fresh session from the bundled clean template."""
    try:
        patch = _load_template()
    except Exception as e:
        raise HTTPException(500, f"Couldn't load template: {e}")
    sid = _new_session(patch)
    return {"session_id": sid, **_chain_payload(patch)}


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    """Start a session from an uploaded .pgp preset."""
    raw = await file.read()
    try:
        patch = pe.load_patch(raw)
    except Exception as e:
        raise HTTPException(400, str(e))
    sid = _new_session(patch, base_patch=copy.deepcopy(patch))
    return {"session_id": sid, "filename": file.filename, **_chain_payload(patch)}


@app.post("/api/chat")
def chat(body: ChatIn):
    s = _state(body.session_id)
    if body.build:
        try:
            # Prefer an uploaded preset as the build base — its model IDs are
            # device-verified. Fall back to the bundled template if nothing has
            # been uploaded this session.
            base = s.get("base_patch") or _load_template()
            s["patch"] = pe.prepare_build_canvas(base)
            s["history"] = []
            s["is_build"] = True
        except Exception as e:
            raise HTTPException(500, f"Couldn't load template: {e}")
    model = body.model or agent.DEFAULT_MODEL
    try:
        result = agent.run_turn(
            s["patch"], body.message, history=s["history"], model=model,
            build_mode=body.build)
    except RuntimeError as e:
        # Ollama not reachable, etc. — surface cleanly to the UI.
        raise HTTPException(503, str(e))

    # In build mode, finalize the patch immediately so the UI chain and the
    # downloaded file are always in sync (no disconnect between what you see
    # and what lands on the device).
    if s.get("is_build"):
        out_patch = pe.finalize_build_patch(result["patch"])
    else:
        out_patch = result["patch"]
    s["patch"] = out_patch

    # Keep a compact rolling history so the model has conversational context
    # without resending the whole preset each turn (the engine re-derives that).
    s["history"].append({"role": "user", "content": body.message})
    s["history"].append({"role": "assistant", "content": result["reply"]})
    s["history"] = s["history"][-12:]

    applied = result["applied"]
    rejected = result["rejected"]
    if s.get("is_build"):
        # In build mode, hide "enabled → True/False" noise — only show what
        # actually describes the tone (param changes, model swaps, renames).
        applied  = [a for a in applied  if " enabled " not in a]
        rejected = [r for r in rejected if " enabled " not in r]

    return {
        "reply": result["reply"],
        "applied": applied,
        "rejected": rejected,
        "build_complete": s.get("is_build", False) and bool(result["applied"]),
        **_chain_payload(out_patch),
    }


@app.get("/api/download/{session_id}")
def download(session_id: str):
    s = _state(session_id)
    patch = s["patch"]  # already finalized in the chat endpoint for build sessions
    data = pe.save_patch(patch)
    name = pe.summarize(patch)["name"] or "patch"
    safe = "".join(c for c in name if c.isalnum() or c in " -_").strip() or "patch"
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{safe}.pgp"'},
    )


@app.get("/api/health")
def health():
    return {"ok": True, "default_model": agent.DEFAULT_MODEL}


if __name__ == "__main__":
    import uvicorn
    print("POD Go Patch Agent → http://localhost:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)
