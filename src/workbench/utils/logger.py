import logging.config
import logging

DEFAULT_LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "style": "{",
            "format": "{asctime}.{msecs:03.0f} - {name:<30} - {levelname} - [{threadName:<20}] - {funcName}(): {message}",
            "datefmt": "%H:%M:%S",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "stream": "ext://sys.stdout",
        }
    },
    "loggers": {
        "": {"level": "INFO", "handlers": ["console"]},
        ".core.blocks": {"level": "DEBUG"},
    },
}


def configure_logger():
    logging.config.dictConfig(DEFAULT_LOGGING)
