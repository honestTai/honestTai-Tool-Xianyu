"""
桌面启动入口
使用 PyInstaller 打包后作为单一可执行文件的入口，自动启动 FastAPI 服务并打开浏览器。
"""
import os
import shutil
import socket
import sys
import threading
import time
import traceback
from pathlib import Path

APP_NAME = "honestTai-Tool-Xianyu"
APP_HOST = "127.0.0.1"
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
RUNTIME_DIR = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)
_DEVNULL_STREAMS = []


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
    """确保工作目录和模块路径正确"""
    _ensure_standard_streams()
    for asset in ("dist", "static", "assets", ".env.example"):
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


def _wait_for_server(host: str, port: int, timeout_seconds: float = 30.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if _is_port_open(host, port):
            return True
        time.sleep(0.2)
    return False


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


def _open_desktop_window(url: str) -> None:
    import webview

    icon_path = RUNTIME_DIR / "assets" / "app-icon.ico"
    storage_path = RUNTIME_DIR / "webview-data"
    webview.create_window(
        APP_NAME,
        url,
        width=1280,
        height=820,
        min_size=(1080, 720),
        text_select=True,
    )
    webview.start(
        debug=False,
        private_mode=False,
        storage_path=str(storage_path),
        icon=str(icon_path) if icon_path.exists() else None,
    )


def run_app() -> None:
    """Start the FastAPI backend and open a native desktop window."""
    server = None
    thread = None
    try:
        _log(f"Starting {APP_NAME}; resource={RESOURCE_DIR}; runtime={RUNTIME_DIR}")
        _prepare_environment()

        from src.app import app
        from src.infrastructure.config.settings import settings

        port = settings.server_port
        url = f"http://{APP_HOST}:{port}"
        if _is_port_open(APP_HOST, port):
            _log(f"Using existing server at {url}")
        else:
            _log(f"Starting embedded server at {url}")
            server, thread = _start_embedded_server(app, port)
            if not _wait_for_server(APP_HOST, port):
                raise RuntimeError(f"Server did not start on {APP_HOST}:{port}")

        _log(f"Opening desktop window {url}")
        _open_desktop_window(url)
    except Exception:
        _log(traceback.format_exc())
        raise
    finally:
        if server is not None:
            server.should_exit = True
        if thread is not None:
            thread.join(timeout=5)


def run_spider() -> None:
    try:
        _log(f"Starting spider worker; resource={RESOURCE_DIR}; runtime={RUNTIME_DIR}")
        _prepare_environment()

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
