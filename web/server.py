#!/usr/bin/env python3
import base64
import json
import mimetypes
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import parse_qs, urlparse


ROOT_DIR = Path(__file__).resolve().parents[1]
WEB_DIR = Path(__file__).resolve().parent
STATIC_DIR = WEB_DIR / "static"
DATA_DIR = WEB_DIR / "data"
PIPELINE_PATH = ROOT_DIR / "pipeline.py"

HOST = "127.0.0.1"
PORT = 8000

DEFAULTS = {
    "distance": 50.0,
    "min_area_ratio": 0.5,
    "spacing": 2.0,
    "sigma_scale": 0.7,
    "sigma_min": 0.5,
    "alpha": 0.5,
}

LIMITS = {
    "distance": {"min": 0.1, "max": 500.0, "step": 0.1},
    "min_area_ratio": {"min": 0.01, "max": 1.0, "step": 0.01},
    "spacing": {"min": 0.1, "max": 100.0, "step": 0.1},
    "sigma_scale": {"min": 0.01, "max": 10.0, "step": 0.01},
    "sigma_min": {"min": 0.01, "max": 100.0, "step": 0.01},
    "alpha": {"min": 0.0, "max": 1.0, "step": 0.01},
}

STEPS = [
    {
        "label": "Step 1/4: Shrinking polygons",
        "progress": 25,
        "args": [
            "json-shrink",
            "--input",
            "{input_dir}",
            "--output",
            "{shrink_dir}",
            "--distance",
            "{distance}",
            "--min-area-ratio",
            "{min_area_ratio}",
            "--config",
            "{config_path}",
        ],
    },
    {
        "label": "Step 2/4: Converting polygons to points",
        "progress": 50,
        "args": [
            "json-convert",
            "--input",
            "{shrink_dir}",
            "--output",
            "{spotted_dir}",
            "--spacing",
            "{spacing}",
        ],
    },
    {
        "label": "Step 3/4: Applying gaussian blur",
        "progress": 75,
        "args": [
            "json-png",
            "--input",
            "{spotted_dir}",
            "--output",
            "{gt_dir}",
            "--config",
            "{config_path}",
            "--sigma-scale",
            "{sigma_scale}",
            "--sigma-min",
            "{sigma_min}",
        ],
    },
    {
        "label": "Step 4/4: Overlaying mask",
        "progress": 100,
        "args": [
            "mask-viz",
            "--image",
            "{input_dir}",
            "--mask",
            "{gt_dir}",
            "--output",
            "{vis_dir}",
            "--alpha",
            "{alpha}",
        ],
    },
]


def clamp_number(name: str, value: object) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid value for '{name}'.")

    bounds = LIMITS[name]
    if parsed < bounds["min"] or parsed > bounds["max"]:
        raise ValueError(
            f"'{name}' must be between {bounds['min']} and {bounds['max']}."
        )
    return parsed


def validate_stem_pair(image_name: str, json_name: str) -> None:
    image_stem = Path(image_name).stem
    json_stem = Path(json_name).stem
    if image_stem != json_stem:
        raise ValueError("Image and JSON filenames must share the same stem.")


def decode_payload_file(file_obj: dict, allowed_suffixes) -> tuple[str, bytes]:
    if not isinstance(file_obj, dict):
        raise ValueError("Missing file payload.")
    name = file_obj.get("name", "")
    content = file_obj.get("content", "")
    suffix = Path(name).suffix.lower()
    if suffix not in allowed_suffixes:
        raise ValueError(f"Unsupported file type: {suffix or 'unknown'}.")
    try:
        raw = base64.b64decode(content)
    except Exception as exc:
        raise ValueError(f"Failed to decode '{name}'.") from exc
    return name, raw


def validate_labelme_json(raw_json: bytes) -> None:
    try:
        data = json.loads(raw_json.decode("utf-8"))
    except Exception as exc:
        raise ValueError("JSON file is not valid UTF-8 Labelme JSON.") from exc

    if data.get("imageWidth") is None or data.get("imageHeight") is None:
        raise ValueError("JSON must include imageWidth and imageHeight.")
    shapes = data.get("shapes")
    if not isinstance(shapes, list) or not shapes:
        raise ValueError("JSON must include at least one shape.")
    if not any(shape.get("shape_type") == "polygon" for shape in shapes if isinstance(shape, dict)):
        raise ValueError("JSON must include at least one polygon shape.")


@dataclass
class TaskState:
    task_id: str
    status: str = "queued"
    progress: int = 0
    step_label: str = "Waiting to start"
    error: str = ""
    overlay_url: str = ""
    logs: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    work_dir: Optional[Path] = None
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def snapshot(self) -> dict:
        with self.lock:
            return {
                "taskId": self.task_id,
                "status": self.status,
                "progress": self.progress,
                "stepLabel": self.step_label,
                "error": self.error,
                "overlayUrl": self.overlay_url,
                "logs": list(self.logs[-50:]),
            }

    def update(self, **kwargs) -> None:
        with self.lock:
            for key, value in kwargs.items():
                setattr(self, key, value)
            self.updated_at = time.time()

    def append_log(self, line: str) -> None:
        with self.lock:
            self.logs.append(line)
            self.updated_at = time.time()


TASKS: Dict[str, TaskState] = {}
TASKS_LOCK = threading.Lock()


def create_task() -> TaskState:
    task_id = uuid.uuid4().hex
    task = TaskState(task_id=task_id)
    with TASKS_LOCK:
        TASKS[task_id] = task
    return task


def get_task(task_id: str) -> Optional[TaskState]:
    with TASKS_LOCK:
        return TASKS.get(task_id)


def run_pipeline_task(task: TaskState, image_name: str, image_bytes: bytes, json_name: str, json_bytes: bytes, params: dict) -> None:
    task_root = DATA_DIR / task.task_id
    input_dir = task_root / "input"
    output_dir = task_root / "output"
    shrink_dir = output_dir / "Shrinked"
    spotted_dir = output_dir / "Spotted"
    gt_dir = output_dir / "GT"
    vis_dir = output_dir / "Vis"
    config_path = output_dir / "Shrink_config.json"

    try:
        input_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)
        task.update(status="running", progress=5, step_label="Preparing input files", work_dir=task_root)

        image_path = input_dir / image_name
        json_path = input_dir / json_name
        image_path.write_bytes(image_bytes)
        json_path.write_bytes(json_bytes)

        formatter_values = {
            "input_dir": str(input_dir),
            "output_dir": str(output_dir),
            "shrink_dir": str(shrink_dir),
            "spotted_dir": str(spotted_dir),
            "gt_dir": str(gt_dir),
            "vis_dir": str(vis_dir),
            "config_path": str(config_path),
            **{k: str(v) for k, v in params.items()},
        }

        for step in STEPS:
            task.update(step_label=step["label"], progress=step["progress"] - 15)
            command = [sys.executable, str(PIPELINE_PATH)]
            command.extend(arg.format(**formatter_values) for arg in step["args"])
            task.append_log("$ " + " ".join(command))

            result = subprocess.run(
                command,
                cwd=str(ROOT_DIR),
                capture_output=True,
                text=True,
            )

            if result.stdout.strip():
                for line in result.stdout.strip().splitlines():
                    task.append_log(line)
            if result.stderr.strip():
                for line in result.stderr.strip().splitlines():
                    task.append_log(line)

            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Pipeline step failed.")

            task.update(progress=step["progress"])

        overlay_name = f"{Path(image_name).stem}_vis.png"
        overlay_path = vis_dir / overlay_name
        if not overlay_path.exists():
            raise RuntimeError("Overlay image was not generated.")

        task.update(
            status="completed",
            progress=100,
            step_label="Completed",
            overlay_url=f"/api/tasks/{task.task_id}/overlay",
        )
    except Exception as exc:
        task.update(
            status="failed",
            error=str(exc),
            step_label=task.step_label if task.step_label else "Failed",
        )


class DemoRequestHandler(BaseHTTPRequestHandler):
    server_version = "PanoDemoHTTP/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/" or path == "/index.html":
            self.serve_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
            return
        if path.startswith("/static/"):
            rel = path[len("/static/") :]
            self.serve_static_file(rel)
            return
        if path == "/api/config":
            self.send_json(
                {
                    "defaults": DEFAULTS,
                    "limits": LIMITS,
                    "sliderFields": ["distance", "spacing", "sigma_scale", "alpha"],
                    "steps": [step["label"] for step in STEPS],
                }
            )
            return
        if path.startswith("/api/tasks/") and path.endswith("/overlay"):
            task_id = path.split("/")[3]
            self.serve_overlay(task_id)
            return
        if path.startswith("/api/tasks/"):
            task_id = path.split("/")[3]
            self.serve_task(task_id)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/run":
            self.handle_run()
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def log_message(self, format: str, *args) -> None:
        return

    def read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise ValueError("Request body must be valid JSON.") from exc

    def send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def serve_file(self, path: Path, content_type: str) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def serve_static_file(self, rel_path: str) -> None:
        safe_path = (STATIC_DIR / rel_path).resolve()
        if not str(safe_path).startswith(str(STATIC_DIR.resolve())):
            self.send_error(HTTPStatus.FORBIDDEN, "Forbidden")
            return
        mime = mimetypes.guess_type(str(safe_path))[0] or "application/octet-stream"
        self.serve_file(safe_path, mime)

    def serve_task(self, task_id: str) -> None:
        task = get_task(task_id)
        if task is None:
            self.send_json({"error": "Task not found."}, status=404)
            return
        self.send_json(task.snapshot())

    def serve_overlay(self, task_id: str) -> None:
        task = get_task(task_id)
        if task is None or task.work_dir is None:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        candidates = list((task.work_dir / "output" / "Vis").glob("*_vis.png"))
        if not candidates:
            self.send_error(HTTPStatus.NOT_FOUND, "Overlay not found")
            return
        self.serve_file(candidates[0], "image/png")

    def handle_run(self) -> None:
        try:
            payload = self.read_json_body()
            image_name, image_bytes = decode_payload_file(
                payload.get("image"),
                {".jpg", ".jpeg", ".png"},
            )
            json_name, json_bytes = decode_payload_file(
                payload.get("annotation"),
                {".json"},
            )
            validate_stem_pair(image_name, json_name)
            validate_labelme_json(json_bytes)

            raw_params = payload.get("params", {})
            params = {
                "distance": clamp_number("distance", raw_params.get("distance", DEFAULTS["distance"])),
                "min_area_ratio": clamp_number(
                    "min_area_ratio",
                    raw_params.get("min_area_ratio", DEFAULTS["min_area_ratio"]),
                ),
                "spacing": clamp_number("spacing", raw_params.get("spacing", DEFAULTS["spacing"])),
                "sigma_scale": clamp_number("sigma_scale", raw_params.get("sigma_scale", DEFAULTS["sigma_scale"])),
                "sigma_min": clamp_number("sigma_min", raw_params.get("sigma_min", DEFAULTS["sigma_min"])),
                "alpha": clamp_number("alpha", raw_params.get("alpha", DEFAULTS["alpha"])),
            }

            task = create_task()
            worker = threading.Thread(
                target=run_pipeline_task,
                args=(task, image_name, image_bytes, json_name, json_bytes, params),
                daemon=True,
            )
            worker.start()
            self.send_json({"taskId": task.task_id}, status=202)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, status=400)
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=500)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if len(sys.argv) > 1:
        parsed = parse_qs(urlparse("?" + "&".join(sys.argv[1:])).query)
        if "port" in parsed:
            global PORT
            PORT = int(parsed["port"][0])

    server = ThreadingHTTPServer((HOST, PORT), DemoRequestHandler)
    print(f"Serving demo at http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
