import os
import sys
import json
from pathlib import Path
from typing import Any, Dict, Optional

APP_NAME = "StockOracle"

def _default_app_dir() -> Path:
    """根据操作系统决定默认应用数据目录。"""
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return Path(base) / APP_NAME
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        return Path.home() / ".config" / APP_NAME


def is_develop_mode() -> bool:
    """开发模式：项目根目录下存在 .git 或 run.py 位于当前工作目录。"""
    project_root = Path(__file__).resolve().parent.parent.parent
    return (project_root / "run.py").exists() or (project_root / ".git").exists()


def get_app_dir() -> Path:
    project_root = Path(__file__).resolve().parent.parent.parent
    if is_develop_mode():
        d = project_root / "data"
    else:
        d = _default_app_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_db_path() -> Path:
    return get_app_dir() / "oracle.db"


def get_user_rules_dir() -> Path:
    d = get_app_dir() / "user_rules"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_user_portfolios_dir() -> Path:
    d = get_app_dir() / "user_portfolios"
    d.mkdir(parents=True, exist_ok=True)
    return d


_DEFAULT_CONFIG: Dict[str, Any] = {
    "data_provider": "akshare",
    "refresh_interval_sec": 5,
    "enable_sound": False,
    "sound_file": "",
    "http_proxy": "",
    "https_proxy": "",
    "rate_limit_min_sec": 0.3,
    "rate_limit_max_sec": 1.0,
    "kline_history_days": 500,
}


def _config_path() -> Path:
    return get_app_dir() / "config.json"


def load_config() -> Dict[str, Any]:
    path = _config_path()
    if not path.exists():
        save_config(_DEFAULT_CONFIG)
        return dict(_DEFAULT_CONFIG)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = dict(_DEFAULT_CONFIG)
        merged.update(data or {})
        return merged
    except Exception:
        return dict(_DEFAULT_CONFIG)


def save_config(cfg: Dict[str, Any]) -> None:
    path = _config_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def get(key: str, default: Any = None) -> Any:
    return load_config().get(key, default)


def set(key: str, value: Any) -> None:
    cfg = load_config()
    cfg[key] = value
    save_config(cfg)
