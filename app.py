from __future__ import annotations

import hashlib
import ipaddress
import os
import sys
import threading
from copy import deepcopy
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Any

import segno
from flask import Flask, Response, jsonify, redirect, render_template, request, url_for

from classroom_lite.meals import get_meal
from classroom_lite.neis import NeisError, search_schools
from classroom_lite.settings_store import (
    SettingsError,
    SettingsStore,
    public_settings,
)
from classroom_lite.timetable import get_timetable
from classroom_lite.updater import AppUpdater, UpdateError


def _load_local_env() -> None:
    env_path = Path(__file__).with_name(".env")
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, value = stripped.split("=", 1)
        os.environ.setdefault(name.strip(), value.strip().strip("\"'"))


def _with_env_neis(settings: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(settings)
    mappings = {
        "NEIS_API_KEY": "api_key",
        "NEIS_SCHOOL_CODE": "school_code",
        "NEIS_OFFICE_CODE": "office_code",
    }
    for env_name, setting_name in mappings.items():
        value = os.environ.get(env_name, "").strip()
        if value:
            result["neis"][setting_name] = value
    return result


def _is_loopback(address: str | None) -> bool:
    try:
        return ipaddress.ip_address(address or "").is_loopback
    except ValueError:
        return False


def _restart_process() -> None:
    os.execv(sys.executable, [sys.executable, str(Path(__file__).resolve())])


_load_local_env()


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    if test_config:
        app.config.update(test_config)

    store = SettingsStore(app.config.get("DATA_DIR"))
    cache_dir = store.data_dir / "cache"
    app.extensions["settings_store"] = store
    updater = app.config.get("UPDATER") or AppUpdater()
    app.extensions["app_updater"] = updater

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        if request.path == "/api/notion-qr" and response.status_code < 400:
            response.headers["Cache-Control"] = "private, max-age=86400"
        else:
            response.headers["Cache-Control"] = (
                "no-store"
                if request.path.startswith("/api/")
                else "no-cache, max-age=0"
            )
        return response

    @app.get("/")
    def dashboard():
        if not store.is_configured():
            return redirect(url_for("setup"))
        return render_template("index.html")

    @app.get("/setup")
    def setup():
        return render_template("setup.html", mode="setup")

    @app.get("/settings")
    def settings_page():
        return render_template("setup.html", mode="settings")

    @app.get("/api/settings")
    def settings_get():
        return jsonify(public_settings(_with_env_neis(store.load())))

    @app.post("/api/settings")
    def settings_save():
        try:
            settings = store.save(request.get_json(force=True))
            return jsonify(
                {"ok": True, "settings": public_settings(_with_env_neis(settings))}
            )
        except SettingsError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    def update_request_error():
        if not _is_loopback(request.remote_addr):
            return jsonify(
                {"error": "업데이트는 서버 기기의 localhost에서만 실행할 수 있습니다."}
            ), 403
        fetch_site = request.headers.get("Sec-Fetch-Site")
        if fetch_site not in {None, "none", "same-origin"}:
            return jsonify({"error": "다른 사이트에서는 업데이트할 수 없습니다."}), 403
        return None

    @app.get("/api/update")
    def update_check():
        denied = update_request_error()
        if denied:
            return denied
        try:
            return jsonify(updater.check(fetch=True))
        except UpdateError as exc:
            return jsonify({"error": str(exc)}), 409

    @app.post("/api/update")
    def update_apply():
        denied = update_request_error()
        if denied:
            return denied
        if not request.is_json:
            return jsonify({"error": "올바른 업데이트 요청이 아닙니다."}), 415
        try:
            result = updater.apply()
        except UpdateError as exc:
            return jsonify({"error": str(exc)}), 409

        restart_scheduled = bool(result["updated"] and not app.config.get("TESTING"))
        if restart_scheduled:
            restart_callback = app.config.get("RESTART_CALLBACK", _restart_process)
            timer = threading.Timer(2.0, restart_callback)
            timer.daemon = True
            timer.start()
        return jsonify({**result, "restart_scheduled": restart_scheduled})

    @app.get("/api/settings/export")
    def settings_export():
        settings = store.load()
        if request.args.get("include_key") != "1":
            settings = public_settings(settings)
            settings["neis"].pop("api_key_configured", None)
        response = jsonify(settings)
        response.headers["Content-Disposition"] = (
            'attachment; filename="classroom-tv-lite-settings.json"'
        )
        return response

    @app.route("/api/schools/search", methods=["GET", "POST"])
    def schools_search():
        payload = request.get_json(silent=True) or request.args
        api_key = str(payload.get("api_key") or "").strip()
        if not api_key:
            api_key = os.environ.get("NEIS_API_KEY", "").strip()
        if not api_key:
            api_key = store.load()["neis"].get("api_key", "")
        if not api_key:
            return jsonify({"error": "먼저 NEIS API 키를 입력하세요."}), 400
        name = str(payload.get("name") or "").strip()
        if len(name) < 2:
            return jsonify({"error": "학교명을 두 글자 이상 입력하세요."}), 400
        try:
            schools = search_schools(api_key, name)
            return jsonify({"schools": schools})
        except NeisError as exc:
            return jsonify({"error": str(exc)}), 502

    @app.get("/api/dashboard")
    def dashboard_data():
        settings = _with_env_neis(store.load())
        if not store.is_configured():
            return jsonify({"error": "초기 설정이 필요합니다."}), 428
        target = _request_date()
        timetable = get_timetable(
            settings,
            cache_dir,
            target,
            refresh=request.args.get("refresh") == "1",
        )
        return jsonify(
            {
                "date": target.isoformat(),
                "classroom_name": settings["classroom_name"],
                "notice": settings["notice"],
                "help_url": settings["help_url"],
                "display": settings["display"],
                "timetable": timetable,
            }
        )

    @app.get("/api/notion-qr")
    def notion_qr():
        help_url = store.load().get("help_url", "")
        if not help_url:
            return jsonify({"error": "Notion 상세 가이드 주소가 설정되지 않았습니다."}), 404

        output = BytesIO()
        segno.make(help_url, error="m").save(
            output,
            kind="svg",
            scale=4,
            border=2,
            dark="#0d1420",
            light="#e8eef7",
            xmldecl=False,
        )
        response = Response(output.getvalue(), mimetype="image/svg+xml")
        response.set_etag(hashlib.sha256(help_url.encode("utf-8")).hexdigest())
        return response.make_conditional(request)

    @app.get("/api/meals")
    def meals_data():
        settings = _with_env_neis(store.load())
        if not store.is_configured():
            return jsonify({"error": "초기 설정이 필요합니다."}), 428
        try:
            meal = get_meal(
                settings,
                cache_dir,
                _request_date(),
                refresh=request.args.get("refresh") == "1",
            )
            return jsonify(meal)
        except NeisError as exc:
            return jsonify({"error": str(exc), "items": []}), 502

    @app.get("/api/timetable")
    def timetable_data():
        settings = _with_env_neis(store.load())
        if not store.is_configured():
            return jsonify({"error": "초기 설정이 필요합니다."}), 428
        return jsonify(
            get_timetable(
                settings,
                cache_dir,
                _request_date(),
                refresh=request.args.get("refresh") == "1",
            )
        )

    @app.get("/health")
    def health():
        return jsonify({"ok": True, "configured": store.is_configured()})

    return app


def _request_date() -> date:
    value = request.args.get("date")
    if value:
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    return date.today()


app = create_app()


if __name__ == "__main__":
    from waitress import serve

    host = os.environ.get("CLASSROOM_HOST", "127.0.0.1")
    port = int(os.environ.get("CLASSROOM_PORT", "53111"))
    print(f"Classroom TV Lite: http://localhost:{port}")
    print(f"설정 저장 위치: {Path(app.extensions['settings_store'].data_dir)}")
    serve(app, host=host, port=port, threads=4)
