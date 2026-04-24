import logging
import logging.config
from pathlib import Path


def setup_logging(service: str = "api", level: str = "INFO") -> None:
    base_dir = Path(__file__).resolve().parents[2]
    log_dir = base_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{service}.log"

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "level": level,
                },
                "file": {
                    "class": "logging.handlers.TimedRotatingFileHandler",
                    "formatter": "default",
                    "level": level,
                    "filename": str(log_file),
                    "encoding": "utf-8",
                    "when": "midnight",
                    "interval": 1,
                    "backupCount": 14,
                    "utc": False,
                },
            },
            "root": {"handlers": ["console", "file"], "level": level},
            "loggers": {
                "uvicorn": {"handlers": ["console", "file"], "level": level, "propagate": False},
                "uvicorn.error": {"handlers": ["console", "file"], "level": level, "propagate": False},
                "uvicorn.access": {"handlers": ["console", "file"], "level": level, "propagate": False},
                "majorerp": {"handlers": ["console", "file"], "level": level, "propagate": False},
                "majorerp.api": {"handlers": ["console", "file"], "level": level, "propagate": False},
                "majorerp.api.requests": {"handlers": ["console", "file"], "level": level, "propagate": False},
                "majorerp.worker": {"handlers": ["console", "file"], "level": level, "propagate": False},
            },
        }
    )
