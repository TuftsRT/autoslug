import logging

from autoslug.defaults import LOG_CONSOLE_FORMAT, LOG_DATE_FORMAT, LOG_FILE_FORMAT


def get_logger(
    name: str = "autoslug",
    level: int = logging.DEBUG,
    console_level: int = logging.INFO,
    file_level=logging.DEBUG,
    log_file: str = None,
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(
        logging.Formatter(LOG_CONSOLE_FORMAT, datefmt=LOG_DATE_FORMAT)
    )
    logger.addHandler(console_handler)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(file_level)
        file_handler.setFormatter(
            logging.Formatter(LOG_FILE_FORMAT, datefmt=LOG_DATE_FORMAT)
        )
        logger.addHandler(file_handler)
    return logger
