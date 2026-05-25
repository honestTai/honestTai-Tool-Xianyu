"""
桌面启动入口
使用 PyInstaller 打包后作为单一可执行文件的入口，自动启动 FastAPI 服务并打开浏览器。
"""
import os
import shutil
import sys
import time
import traceback
import webbrowser
from pathlib import Path

APP_NAME = "honestTai-Tool-Xianyu"
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
    for asset in ("dist", "static", ".env.example"):
        _sync_runtime_asset(asset)

    os.chdir(RUNTIME_DIR)
    if str(RESOURCE_DIR) not in sys.path:
        sys.path.insert(0, str(RESOURCE_DIR))


def run_app() -> None:
    """启动 FastAPI 应用并自动打开浏览器"""
    try:
        _log(f"Starting {APP_NAME}; resource={RESOURCE_DIR}; runtime={RUNTIME_DIR}")
        _prepare_environment()

        from src.app import app
        from src.infrastructure.config.settings import settings
        import uvicorn

        url = f"http://127.0.0.1:{settings.server_port}"
        _log(f"Opening {url}")
        webbrowser.open(url)
        time.sleep(0.5)

        uvicorn.run(
            app,
            host="127.0.0.1",
            port=settings.server_port,
            log_level="info",
            reload=False,
        )
    except Exception:
        _log(traceback.format_exc())
        raise


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
