from __future__ import annotations

import os
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, redirect, render_template, request, url_for

from classroom_lite.meals import get_meal
from classroom_lite.neis import NeisError, search_schools
from classroom_lite.settings_store import (
    SettingsError,
    SettingsStore,
    public_settings,
)
from classroom_lite.timetable import get_timetable


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


_load_local_env()


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    if test_config:
        app.config.update(test_config)

    store = SettingsStore(app.config.get("DATA_DIR"))
    cache_dir = store.data_dir / "cache"
    app.extensions["settings_store"] = store

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
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
                "timetable": timetable,
            }
        )

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
