from logging import (
    DEBUG,
    INFO,
    FileHandler,
    Formatter,
    Logger,
    StreamHandler,
    getLogger,
)

from autoslug.config.defaults import (
    LOG_CONSOLE_FORMAT,
    LOG_DATE_FORMAT,
    LOG_FILE_FORMAT,
)


def get_logger(
    name: str = "autoslug",
    level: int = DEBUG,
    console_level: int = INFO,
    file_level=DEBUG,
    log_file: str = None,
) -> Logger:
    logger = getLogger(name)
    logger.setLevel(level)
    console_handler = StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(Formatter(LOG_CONSOLE_FORMAT, datefmt=LOG_DATE_FORMAT))
    logger.addHandler(console_handler)
    if log_file:
        file_handler = FileHandler(log_file)
        file_handler.setLevel(file_level)
        file_handler.setFormatter(Formatter(LOG_FILE_FORMAT, datefmt=LOG_DATE_FORMAT))
        logger.addHandler(file_handler)
    return logger


def log_access_denied(path: str, logger: Logger) -> None:
    logger.error(f"access denied: {path}")
    return None


def log_ignored(path: str, logger: Logger) -> None:
    logger.debug(f"ignored: {path}")
    return None


def log_ignored(path: str, logger: Logger) -> None:
    logger.debug(f"ignored: {path}")
    return None
