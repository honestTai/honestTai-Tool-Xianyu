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
import base64
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
_SERVER_RUNTIME = {"server": None, "thread": None}


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


def _find_available_port(preferred_port: int) -> int:
    for port in range(preferred_port, preferred_port + 100):
        if not _is_port_open(APP_HOST, port):
            return port
    raise RuntimeError(f"No free local port found near {preferred_port}")


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


def _asset_data_uri(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    except Exception:
        return ""


def _loading_html() -> str:
    icon_uri = _asset_data_uri(RUNTIME_DIR / "assets" / "app-icon.png")
    icon_html = f'<img src="{icon_uri}" alt="" />' if icon_uri else '<div class="fallback-icon"></div>'
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      height: 100vh;
      display: grid;
      place-items: center;
      font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
      color: #eaf2ff;
      background:
        radial-gradient(circle at 30% 20%, rgba(0, 209, 255, 0.28), transparent 28%),
        radial-gradient(circle at 70% 76%, rgba(48, 235, 145, 0.22), transparent 30%),
        linear-gradient(135deg, #06111f, #0b2346 52%, #07111f);
    }}
    .shell {{
      width: min(520px, calc(100vw - 48px));
      padding: 38px 34px;
      border: 1px solid rgba(255,255,255,0.12);
      border-radius: 26px;
      background: rgba(8, 22, 43, 0.68);
      box-shadow: 0 24px 80px rgba(0,0,0,0.34);
      text-align: center;
      backdrop-filter: blur(18px);
    }}
    img, .fallback-icon {{
      width: 92px;
      height: 92px;
      border-radius: 24px;
      margin-bottom: 22px;
      filter: drop-shadow(0 18px 32px rgba(0, 188, 255, 0.26));
    }}
    .fallback-icon {{
      margin-inline: auto;
      background: linear-gradient(135deg, #16d9ff, #2f7cff);
    }}
    h1 {{
      margin: 0;
      font-size: 26px;
      letter-spacing: 0;
      font-weight: 800;
    }}
    p {{
      margin: 12px 0 0;
      color: #aebfda;
      font-size: 15px;
    }}
    .loader {{
      height: 6px;
      overflow: hidden;
      margin-top: 30px;
      border-radius: 999px;
      background: rgba(255,255,255,0.12);
    }}
    .loader::before {{
      content: "";
      display: block;
      width: 42%;
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, #27f1ff, #34e89e);
      animation: sweep 1.15s ease-in-out infinite;
    }}
    @keyframes sweep {{
      0% {{ transform: translateX(-110%); }}
      100% {{ transform: translateX(260%); }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    {icon_html}
    <h1>honestTai-Tool-Xianyu</h1>
    <p>正在启动本地服务，请稍等...</p>
    <div class="loader" aria-hidden="true"></div>
  </main>
</body>
</html>"""


def _startup_error_html(message: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <style>
    body {{
      margin: 0;
      height: 100vh;
      display: grid;
      place-items: center;
      font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
      color: #1f2937;
      background: #f8fafc;
    }}
    main {{
      max-width: 560px;
      padding: 32px;
      border: 1px solid #e2e8f0;
      border-radius: 18px;
      background: #fff;
      box-shadow: 0 24px 80px rgba(15, 23, 42, 0.12);
    }}
    h1 {{ margin: 0 0 12px; font-size: 22px; }}
    pre {{ white-space: pre-wrap; color: #ef4444; }}
  </style>
</head>
<body>
  <main>
    <h1>启动失败</h1>
    <pre>{message}</pre>
  </main>
</body>
</html>"""


def _start_server_and_load(window, preferred_port: int) -> None:
    try:
        from src.app import app

        port = _find_available_port(preferred_port)
        url = f"http://{APP_HOST}:{port}"
        if port != preferred_port:
            _log(f"Configured port {preferred_port} is busy, using {port}")

        _log(f"Starting embedded server at {url}")
        server, thread = _start_embedded_server(app, port)
        _SERVER_RUNTIME["server"] = server
        _SERVER_RUNTIME["thread"] = thread

        if not _wait_for_server(APP_HOST, port):
            raise RuntimeError(f"Server did not start on {APP_HOST}:{port}")

        _log(f"Loading desktop window {url}")
        window.load_url(url)
    except Exception as exc:
        _log(traceback.format_exc())
        window.load_html(_startup_error_html(str(exc)))


def _open_desktop_window(preferred_port: int) -> None:
    import webview

    icon_path = RUNTIME_DIR / "assets" / "app-icon.ico"
    storage_path = RUNTIME_DIR / "webview-data"
    window = webview.create_window(
        APP_NAME,
        html=_loading_html(),
        width=1280,
        height=820,
        min_size=(1080, 720),
        text_select=True,
    )
    webview.start(
        _start_server_and_load,
        (window, preferred_port),
        debug=False,
        private_mode=False,
        storage_path=str(storage_path),
        icon=str(icon_path) if icon_path.exists() else None,
    )


def run_app() -> None:
    """Start the FastAPI backend and open a native desktop window."""
    try:
        _log(f"Starting {APP_NAME}; resource={RESOURCE_DIR}; runtime={RUNTIME_DIR}")
        _prepare_environment()

        from src.infrastructure.config.settings import settings

        _log("Opening desktop window with startup loading screen")
        _open_desktop_window(settings.server_port)
    except Exception:
        _log(traceback.format_exc())
        raise
    finally:
        server = _SERVER_RUNTIME.get("server")
        thread = _SERVER_RUNTIME.get("thread")
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
