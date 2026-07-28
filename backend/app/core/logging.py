import logging
import logging.config


def configure_logging(level: str) -> None:
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": (
                        "%(asctime)s %(levelname)s %(name)s "
                        "request_id=%(request_id)s %(message)s"
                    ),
                }
            },
            "filters": {"request_context": {"()": "app.core.middleware.RequestIdFilter"}},
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "filters": ["request_context"],
                }
            },
            "root": {"handlers": ["default"], "level": level},
        }
    )

