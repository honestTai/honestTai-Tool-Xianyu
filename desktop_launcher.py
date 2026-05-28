"""Executable launcher for the local web app.

The packaged exe starts the FastAPI backend and opens the user's default
browser. Spider workers reuse this same exe with ``--run-spider``.
"""

import os
import shutil
import socket
import sys
import threading
import time
import traceback
import urllib.request
import webbrowser
from pathlib import Path

APP_NAME = "honestTai-Tool-Xianyu"
APP_HOST = "127.0.0.1"
INSTANCE_CONTROL_PORT = 47681
INSTANCE_URL_PREFIX = "honesttai-url "
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
RUNTIME_DIR = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)
_DEVNULL_STREAMS = []
_SERVER_RUNTIME = {"server": None, "thread": None, "control_socket": None}


def _sync_runtime_asset(name: str) -> None:
    source = RESOURCE_DIR / name
    target = RUNTIME_DIR / name
    if not source.exists() or source.resolve() == target.resolve():
        return
    if source.is_dir():
        shutil.copytree(source, target, dirs_exist_ok=True)
    elif not target.exists():
        shutil.copy2(source, target)


def _log(message: str) -> None:
    try:
        log_dir = RUNTIME_DIR / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        with (log_dir / "desktop-launcher.log").open("a", encoding="utf-8") as handle:
            handle.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")
    except Exception:
        pass


def _ensure_standard_streams() -> None:
    for stream_name in ("stdout", "stderr"):
        if getattr(sys, stream_name) is None:
            stream = open(os.devnull, "w", encoding="utf-8")
            setattr(sys, stream_name, stream)
            _DEVNULL_STREAMS.append(stream)


def _prepare_environment() -> None:
    _ensure_standard_streams()
    for asset in ("dist", "static", "assets", ".env", ".env.example"):
        _sync_runtime_asset(asset)

    os.chdir(RUNTIME_DIR)
    if str(RESOURCE_DIR) not in sys.path:
        sys.path.insert(0, str(RESOURCE_DIR))


def _is_port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.4):
            return True
    except OSError:
        return False


def _health_url(url: str) -> str:
    return f"{url.rstrip('/')}/health"


def _is_app_healthy(url: str) -> bool:
    try:
        with urllib.request.urlopen(_health_url(url), timeout=1.0) as response:
            return 200 <= response.status < 300
    except Exception:
        return False


def _wait_for_app(url: str, timeout_seconds: float = 30.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if _is_app_healthy(url):
            return True
        time.sleep(0.2)
    return False


def _find_available_port(preferred_port: int) -> int:
    for port in range(preferred_port, preferred_port + 100):
        if not _is_port_open(APP_HOST, port):
            return port
    raise RuntimeError(f"No free local port found near {preferred_port}")


def _connect_to_existing_instance() -> str | None:
    try:
        with socket.create_connection((APP_HOST, INSTANCE_CONTROL_PORT), timeout=0.5) as client:
            client.sendall(b"url\n")
            client.settimeout(1.0)
            payload = client.recv(256).decode("utf-8", errors="ignore").strip()
    except OSError:
        return None

    if payload.startswith(INSTANCE_URL_PREFIX):
        url = payload[len(INSTANCE_URL_PREFIX):].strip()
        return url or None
    return None


def _wait_for_existing_instance_url(timeout_seconds: float = 10.0) -> str | None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        url = _connect_to_existing_instance()
        if url:
            return url
        time.sleep(0.25)
    return None


def _acquire_instance_control_socket() -> socket.socket | None:
    control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            control_socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            control_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        control_socket.bind((APP_HOST, INSTANCE_CONTROL_PORT))
        control_socket.listen(5)
        control_socket.settimeout(0.5)
        return control_socket
    except OSError:
        control_socket.close()
        return None


def _start_instance_control_server(
    control_socket: socket.socket,
    url: str,
    ready_event: threading.Event,
) -> threading.Thread:
    def run() -> None:
        _log(f"Browser launcher control listening on {APP_HOST}:{INSTANCE_CONTROL_PORT}")
        while True:
            try:
                conn, _ = control_socket.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            with conn:
                try:
                    command = conn.recv(64).decode("utf-8", errors="ignore").strip()
                except OSError:
                    command = ""
                if command in {"url", "open", "focus"}:
                    ready_event.wait(timeout=30)
                    try:
                        conn.sendall(f"{INSTANCE_URL_PREFIX}{url}\n".encode("utf-8"))
                    except OSError:
                        pass
                    _log("Shared browser URL with another launcher instance")

    thread = threading.Thread(target=run, name="honesttai-browser-instance", daemon=True)
    thread.start()
    return thread


def _start_embedded_server(app, port: int):
    import uvicorn

    config = uvicorn.Config(
        app,
        host=APP_HOST,
        port=port,
        log_level="info",
        reload=False,
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="honesttai-api", daemon=True)
    thread.start()
    return server, thread


def _open_browser(url: str) -> None:
    _log(f"Opening browser {url}")
    webbrowser.open(url, new=2)


def _serve_until_stopped(thread: threading.Thread) -> None:
    try:
        while thread.is_alive():
            thread.join(timeout=0.5)
    except KeyboardInterrupt:
        _log("Launcher interrupted by user")


def run_app() -> None:
    """Start the FastAPI backend and open the default browser."""
    try:
        _log(f"Starting {APP_NAME}; resource={RESOURCE_DIR}; runtime={RUNTIME_DIR}")
        _prepare_environment()

        existing_url = _connect_to_existing_instance()
        if existing_url:
            _open_browser(existing_url)
            return

        control_socket = _acquire_instance_control_socket()
        if control_socket is None:
            existing_url = _wait_for_existing_instance_url()
            if existing_url:
                _open_browser(existing_url)
                return
            raise RuntimeError("Another launcher instance is starting, but did not share a URL.")
        _SERVER_RUNTIME["control_socket"] = control_socket

        from src.infrastructure.config.settings import settings

        port = _find_available_port(settings.server_port)
        url = f"http://{APP_HOST}:{port}"
        if port != settings.server_port:
            _log(f"Configured port {settings.server_port} is busy, using {port}")

        ready_event = threading.Event()
        _start_instance_control_server(control_socket, url, ready_event)

        from src.app import app

        _log(f"Starting embedded server at {url}")
        server, thread = _start_embedded_server(app, port)
        _SERVER_RUNTIME["server"] = server
        _SERVER_RUNTIME["thread"] = thread

        if not _wait_for_app(url):
            raise RuntimeError(f"Server did not become healthy at {_health_url(url)}")

        ready_event.set()
        _open_browser(url)
        _serve_until_stopped(thread)
    except Exception:
        _log(traceback.format_exc())
        raise
    finally:
        server = _SERVER_RUNTIME.get("server")
        thread = _SERVER_RUNTIME.get("thread")
        control_socket = _SERVER_RUNTIME.get("control_socket")
        if server is not None:
            server.should_exit = True
        if thread is not None:
            thread.join(timeout=5)
        if control_socket is not None:
            try:
                control_socket.close()
            except OSError:
                pass


def run_spider() -> None:
    try:
        _log(f"Starting spider worker; resource={RESOURCE_DIR}; runtime={RUNTIME_DIR}")
        _prepare_environment()

        from src.services.license_runtime import LicenseError, license_manager

        try:
            license_manager.ensure_startup_authorized(interactive=False)
        except LicenseError as exc:
            _log(f"Spider license check failed: {exc.code} {exc.message}")
            raise RuntimeError(f"授权校验失败: {exc.message}") from exc

        args = sys.argv[1:]
        if args and args[0] == "--run-spider":
            args = args[1:]
        sys.argv = ["spider_v2.py", *args]

        import asyncio
        from spider_v2 import main as spider_main

        asyncio.run(spider_main())
    except Exception:
        _log(traceback.format_exc())
        raise


if __name__ == "__main__":
    if "--run-spider" in sys.argv:
        run_spider()
    else:
        run_app()
