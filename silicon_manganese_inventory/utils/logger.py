import logging
import os
import sys
import traceback
from logging.handlers import RotatingFileHandler
from datetime import datetime

_logger = None


def get_logger(name="SiliconMnInventory"):
    global _logger
    if _logger is not None:
        return _logger

    _logger = logging.getLogger(name)
    _logger.setLevel(logging.DEBUG)

    log_dir = _get_log_dir()
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, f"app_{datetime.now().strftime('%Y%m%d')}.log")
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "[%(asctime)s] %(levelname)-7s %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    _logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        "%(levelname)-7s | %(message)s"
    ))
    _logger.addHandler(console_handler)

    _logger.info("=" * 60)
    _logger.info(f"应用启动 v1.0.0")
    _logger.info(f"日志目录: {log_dir}")
    return _logger


def _get_log_dir():
    if sys.platform == "win32":
        base = os.getenv("APPDATA", os.path.expanduser("~"))
    elif sys.platform == "darwin":
        base = os.path.join(os.path.expanduser("~"), "Library", "Logs")
    else:
        base = os.getenv("XDG_STATE_HOME", os.path.join(os.path.expanduser("~"), ".local", "state"))
    return os.path.join(base, "SiliconMnInventory", "logs")


def install_excepthook():
    logger = get_logger()

    def _handler(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logger.critical("未捕获异常:", exc_info=(exc_type, exc_value, exc_tb))

    sys.excepthook = _handler


def log_db_operation(operation, duration_ms=None, **kwargs):
    logger = get_logger()
    details = ", ".join(f"{k}={v}" for k, v in kwargs.items())
    if duration_ms is not None:
        logger.debug(f"DB | {operation} | {duration_ms:.1f}ms | {details}")
    else:
        logger.debug(f"DB | {operation} | {details}")


def log_user_action(user, action, target=None, detail=""):
    logger = get_logger()
    parts = [f"USER | {user}", action]
    if target:
        parts.append(str(target))
    if detail:
        parts.append(detail)
    logger.info(" | ".join(parts))
