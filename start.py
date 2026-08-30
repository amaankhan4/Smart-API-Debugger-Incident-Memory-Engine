"""
Starts the API, both background workers and the frontend as one supervised group,
after verifying that MongoDB, Redis and Upstash Vector are actually reachable. Every
failure mode reports what broke and how to fix it instead of dying with a traceback.

    python start.py              # everything
    python start.py --check      # preflight checks only, start nothing
    python start.py --no-frontend --no-workers
"""

from __future__ import annotations

import argparse
import os
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, urlparse

ROOT = Path(__file__).resolve().parent
UI_DIR = ROOT / "ui"
IS_WINDOWS = os.name == "nt"

API_HOST = "127.0.0.1"
API_PORT = 8000
UI_PORT = 5173
SHUTDOWN_GRACE_SECONDS = 10


# --------------------------------------------------------------------------- output


def _supports_colour() -> bool:
    if not sys.stdout.isatty():
        return False
    if IS_WINDOWS:
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            # Enable ANSI escape processing on the console (Windows 10+).
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            return False
    return True


COLOUR = _supports_colour()
_PALETTE = {
    "api": "\033[38;5;75m",
    "embed": "\033[38;5;177m",
    "cluster": "\033[38;5;215m",
    "ui": "\033[38;5;114m",
    "boot": "\033[38;5;245m",
    "ok": "\033[38;5;114m",
    "warn": "\033[38;5;215m",
    "err": "\033[38;5;203m",
    "reset": "\033[0m",
    "bold": "\033[1m",
}


def paint(text: str, key: str) -> str:
    if not COLOUR:
        return text
    return f"{_PALETTE.get(key, '')}{text}{_PALETTE['reset']}"


def log(message: str, key: str = "boot") -> None:
    print(f"{paint('▪', key)} {message}", flush=True)


def ok(message: str) -> None:
    print(f"{paint('✓', 'ok')} {message}", flush=True)


def warn(message: str) -> None:
    print(f"{paint('!', 'warn')} {message}", flush=True)


def fail(message: str) -> None:
    print(f"{paint('✗', 'err')} {message}", file=sys.stderr, flush=True)


def banner() -> None:
    title = "Incident Memory Engine — development stack"
    print()
    print(paint(title, "bold"))
    print(paint("─" * len(title), "boot"))


# --------------------------------------------------------------------------- env


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip("'\"")
    return values


PLACEHOLDER_SECRET = "dev-insecure-secret-change-me"


def ensure_backend_env() -> dict[str, str]:
    """Create .env from the example on first run, with a real generated secret."""
    env_path = ROOT / ".env"
    example = ROOT / ".env.example"

    if not env_path.is_file():
        if not example.is_file():
            raise LauncherError(
                "No .env or .env.example found. Cannot determine how to reach the datastores."
            )
        content = example.read_text(encoding="utf-8").replace(
            f"JWT_SECRET={PLACEHOLDER_SECRET}", f"JWT_SECRET={secrets.token_urlsafe(48)}"
        )
        env_path.write_text(content, encoding="utf-8")
        ok("Created .env from .env.example with a freshly generated JWT_SECRET")

    values = read_env_file(env_path)
    current_secret = values.get("JWT_SECRET")

    if not current_secret or current_secret == PLACEHOLDER_SECRET:
        generated = secrets.token_urlsafe(48)
        text = env_path.read_text(encoding="utf-8")

        if current_secret == PLACEHOLDER_SECRET:
            text = text.replace(f"JWT_SECRET={PLACEHOLDER_SECRET}", f"JWT_SECRET={generated}")
            message = "Replaced the placeholder JWT_SECRET with a generated value"
        else:
            # The key is absent entirely, so appending is the only way to set it.
            separator = "" if text.endswith("\n") or not text else "\n"
            text = f"{text}{separator}JWT_SECRET={generated}\n"
            message = "Added a generated JWT_SECRET to .env"

        env_path.write_text(text, encoding="utf-8")
        values["JWT_SECRET"] = generated
        ok(message)

    missing = [
        key
        for key in (
            "MONGODB_URI",
            "MONGODB_DB",
            "UPSTASH_VECTOR_REST_URL",
            "UPSTASH_VECTOR_REST_TOKEN",
            "UPLOAD_DIR",
        )
        if not values.get(key)
    ]
    if not resolve_redis_url(values):
        missing.append("REDIS_URL (or UPSTASH_REDIS_REST_URL + UPSTASH_REDIS_REST_TOKEN)")
    if missing:
        raise LauncherError(f".env is missing required settings: {', '.join(missing)}")

    return values


def ensure_frontend_env() -> None:
    ui_env = UI_DIR / ".env"
    if not ui_env.is_file():
        ui_env.write_text(
            f"VITE_API_BASE_URL=http://{API_HOST}:{API_PORT}/api/v1\n", encoding="utf-8"
        )
        ok("Created ui/.env pointing at the local API")


# --------------------------------------------------------------------------- checks


class LauncherError(RuntimeError):
    """A problem the user can fix, reported without a traceback."""


def port_is_free(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) != 0


def check_python_packages() -> None:
    required = {
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "motor": "motor",
        "redis": "redis",
        "upstash_vector": "upstash-vector",
        "sentence_transformers": "sentence-transformers",
        "sklearn": "scikit-learn",
        "jwt": "pyjwt",
        "bcrypt": "bcrypt",
    }
    import importlib.util

    missing = [pkg for module, pkg in required.items() if importlib.util.find_spec(module) is None]
    if missing:
        raise LauncherError(
            "Missing Python packages: "
            + ", ".join(missing)
            + "\n  Fix with:  pip install -r requirements.txt"
        )
    ok("Python dependencies present")


def check_frontend_install() -> None:
    if not (UI_DIR / "node_modules").is_dir():
        raise LauncherError(
            "Frontend dependencies are not installed.\n  Fix with:  cd ui && npm install"
        )
    ok("Frontend dependencies present")


def check_mongo(uri: str) -> tuple[bool, str]:
    """Probe MongoDB. Hints never echo the URI, which carries credentials."""
    try:
        from pymongo import MongoClient
        from pymongo.errors import (
            ConfigurationError,
            OperationFailure,
            ServerSelectionTimeoutError,
        )

        client = MongoClient(uri, serverSelectionTimeoutMS=2500)
        try:
            client.admin.command("ping")
            return True, "reachable"
        finally:
            client.close()
    except ConfigurationError:
        return False, (
            "SRV/DNS lookup failed — check your internet connection, or whether the "
            "Atlas cluster still exists and is not paused"
        )
    except OperationFailure:
        return False, "authentication failed — check the username and password"
    except ServerSelectionTimeoutError:
        return False, "no server responded — is it running, and is your IP allow-listed in Atlas?"
    except Exception as exc:
        return False, type(exc).__name__


def resolve_redis_url(values: dict[str, str]) -> str:
    """Mirror Settings.redis_url: an Upstash REST token doubles as the TCP password."""
    if values.get("REDIS_URL"):
        return values["REDIS_URL"]
    host = urlparse(values.get("UPSTASH_REDIS_REST_URL", "")).hostname
    token = values.get("UPSTASH_REDIS_REST_TOKEN")
    if host and token:
        return f"rediss://default:{quote(token, safe='')}@{host}:6379"
    return ""


def check_redis(url: str) -> tuple[bool, str]:
    try:
        import redis

        client = redis.Redis.from_url(url, socket_connect_timeout=2.5)
        try:
            client.ping()
            return True, "reachable"
        finally:
            client.close()
    except Exception as exc:
        name = type(exc).__name__
        if name in {"ConnectionError", "TimeoutError"}:
            return False, "not running — start it with Docker or a local Redis server"
        return False, name


def check_vector(url: str, token: str) -> tuple[bool, str]:
    try:
        from upstash_vector import Index

        info = Index(url=url, token=token, retries=0).info()
    except Exception as exc:
        return False, type(exc).__name__

    if info.dimension != 384:
        return False, f"index is {info.dimension}-dim, but the embedding model emits 384"
    if info.similarity_function.upper() != "COSINE":
        return False, f"index metric is {info.similarity_function}, expected COSINE"
    return True, "reachable"


def docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        result = subprocess.run(
            ["docker", "info"], capture_output=True, timeout=20, cwd=ROOT
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def start_infra_with_docker() -> bool:
    log("Starting MongoDB and Redis with Docker Compose…")
    try:
        result = subprocess.run(
            ["docker", "compose", "up", "-d", "mongodb", "redis"],
            cwd=ROOT,
            timeout=300,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        fail(f"Could not run Docker Compose: {exc}")
        return False
    if result.returncode != 0:
        fail("Docker Compose failed to start the datastores.")
        return False
    return True


def wait_for_datastores(env: dict[str, str], attempts: int = 30) -> None:
    """Poll each datastore until all are reachable or the budget runs out."""
    statuses: dict[str, tuple[bool, str]] = {}

    for attempt in range(1, attempts + 1):
        statuses = {
            "MongoDB": check_mongo(env["MONGODB_URI"]),
            "Redis": check_redis(resolve_redis_url(env)),
            "Upstash Vector": check_vector(
                env["UPSTASH_VECTOR_REST_URL"], env["UPSTASH_VECTOR_REST_TOKEN"]
            ),
        }
        if all(healthy for healthy, _ in statuses.values()):
            for name in statuses:
                ok(f"{name} reachable")
            return
        if attempt == 1 and attempts > 1:
            log("Waiting for datastores…")
        time.sleep(2 if attempts > 1 else 0)

    broken = "\n".join(
        f"    • {name}: {detail}" for name, (healthy, detail) in statuses.items() if not healthy
    )

    if shutil.which("docker"):
        remedy = "\n\n  Start the local ones with:  docker compose up -d mongodb redis"
    else:
        remedy = (
            "\n\n  Docker is not installed, so there is nothing running locally. Either:"
            "\n    1. Install Docker Desktop, then:  docker compose up -d mongodb redis"
            "\n    2. Or point .env at free hosted instances:"
            "\n       MongoDB Atlas (free M0), Upstash Redis (free), Upstash Vector (free)"
        )

    raise LauncherError("These datastores are not reachable:\n" + broken + remedy)


def preflight(env: dict[str, str], *, use_docker: bool, want_frontend: bool) -> None:
    check_python_packages()
    if want_frontend:
        check_frontend_install()

    statuses = {
        "MongoDB": check_mongo(env["MONGODB_URI"]),
        "Redis": check_redis(resolve_redis_url(env)),
        "Upstash Vector": check_vector(
            env["UPSTASH_VECTOR_REST_URL"], env["UPSTASH_VECTOR_REST_TOKEN"]
        ),
    }
    down = [name for name, (healthy, _) in statuses.items() if not healthy]

    if not down:
        for name in statuses:
            ok(f"{name} reachable")
    elif use_docker and docker_available():
        warn(f"Not reachable: {', '.join(down)} — attempting to start them with Docker")
        if not start_infra_with_docker():
            raise LauncherError("Could not start the datastores automatically.")
        wait_for_datastores(env)
    else:
        wait_for_datastores(env, attempts=1)

    for port, label in ((API_PORT, "API"), (UI_PORT, "frontend")):
        if label == "frontend" and not want_frontend:
            continue
        if not port_is_free(port):
            raise LauncherError(
                f"Port {port} is already in use, so the {label} cannot start.\n"
                f"  Find it with:  netstat -ano | findstr :{port}"
                if IS_WINDOWS
                else f"  Find it with:  lsof -i :{port}"
            )
    ok("Required ports are free")


# --------------------------------------------------------------------------- processes


@dataclass
class Service:
    name: str
    command: list[str]
    cwd: Path
    colour: str
    process: subprocess.Popen | None = None


def build_services(*, workers: bool, frontend: bool, reload: bool) -> list[Service]:
    python = sys.executable
    services = [
        Service(
            name="api",
            command=[
                python,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                API_HOST,
                "--port",
                str(API_PORT),
                *(["--reload"] if reload else []),
            ],
            cwd=ROOT,
            colour="api",
        )
    ]

    if workers:
        services.append(
            Service("embed", [python, "-m", "app.workers.embedding_workers"], ROOT, "embed")
        )
        services.append(
            Service("cluster", [python, "-m", "app.workers.clustering_worker"], ROOT, "cluster")
        )

    if frontend:
        npm = shutil.which("npm")
        if npm is None:
            raise LauncherError("npm was not found on PATH. Install Node.js 20+ to run the frontend.")
        services.append(Service("ui", [npm, "run", "dev"], UI_DIR, "ui"))

    return services


def spawn(service: Service) -> None:
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if IS_WINDOWS else 0
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")

    try:
        service.process = subprocess.Popen(
            service.command,
            cwd=service.cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
            start_new_session=not IS_WINDOWS,
            env=env,
        )
    except FileNotFoundError as exc:
        raise LauncherError(f"Could not start '{service.name}': {exc}") from exc


def pump_output(service: Service, stop: threading.Event) -> None:
    stream = service.process.stdout if service.process else None
    if stream is None:
        return
    label = paint(f"{service.name:>7} │", service.colour)
    for raw in iter(stream.readline, b""):
        if stop.is_set():
            break
        line = raw.decode("utf-8", errors="replace").rstrip()
        if line:
            print(f"{label} {line}", flush=True)
    stream.close()


def stop_service(service: Service) -> None:
    process = service.process
    if process is None or process.poll() is not None:
        return

    # Prefer the signal our workers handle so they can shut down cleanly.
    try:
        if IS_WINDOWS:
            os.kill(process.pid, signal.CTRL_BREAK_EVENT)
        else:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    except (OSError, ValueError, AttributeError):
        process.terminate()

    try:
        process.wait(timeout=SHUTDOWN_GRACE_SECONDS)
        return
    except subprocess.TimeoutExpired:
        pass

    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def run(services: list[Service]) -> int:
    stop = threading.Event()
    threads: list[threading.Thread] = []
    started: list[Service] = []

    try:
        for service in services:
            spawn(service)
            started.append(service)
            thread = threading.Thread(target=pump_output, args=(service, stop), daemon=True)
            thread.start()
            threads.append(thread)
            log(f"started {service.name} (pid {service.process.pid})", service.colour)

        print()
        ok(f"API      http://{API_HOST}:{API_PORT}")
        ok(f"Docs     http://{API_HOST}:{API_PORT}/docs")
        if any(service.name == "ui" for service in started):
            ok(f"Frontend http://localhost:{UI_PORT}")
        print(paint("\nPress Ctrl+C to stop everything.\n", "boot"))

        while True:
            for service in started:
                code = service.process.poll() if service.process else None
                if code is not None:
                    if code == 0:
                        warn(f"'{service.name}' exited normally — shutting the stack down.")
                    else:
                        fail(f"'{service.name}' exited with code {code} — shutting the stack down.")
                    return code or 1
            time.sleep(0.4)

    except KeyboardInterrupt:
        print()
        log("Ctrl+C received — stopping services…")
        return 0
    finally:
        stop.set()
        for service in reversed(started):
            stop_service(service)
        for thread in threads:
            thread.join(timeout=2)
        log("All services stopped.")


# --------------------------------------------------------------------------- entry


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Start the Incident Memory Engine development stack."
    )
    parser.add_argument("--check", action="store_true", help="run preflight checks and exit")
    parser.add_argument("--no-frontend", action="store_true", help="do not start the Vite dev server")
    parser.add_argument("--no-workers", action="store_true", help="do not start the background workers")
    parser.add_argument(
        "--no-docker",
        action="store_true",
        help="never try to start the datastores with Docker Compose",
    )
    parser.add_argument("--no-reload", action="store_true", help="disable API auto-reload")
    args = parser.parse_args()

    banner()

    try:
        env = ensure_backend_env()
        want_frontend = not args.no_frontend
        if want_frontend:
            ensure_frontend_env()

        preflight(env, use_docker=not args.no_docker, want_frontend=want_frontend)

        if args.check:
            print()
            ok("Preflight checks passed. Nothing was started (--check).")
            return 0

        services = build_services(
            workers=not args.no_workers, frontend=want_frontend, reload=not args.no_reload
        )
        print()
        return run(services)

    except LauncherError as exc:
        print()
        fail(str(exc))
        return 1
    except KeyboardInterrupt:
        return 0
    except Exception as exc:  # last resort: never dump a raw traceback at a user
        print()
        fail(f"Unexpected launcher error: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
