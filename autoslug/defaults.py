from typing import Dict, Final, Set

EXT_MAP: Final[Dict[str, str]] = {
    ".yml": ".yaml",
}
IGNORE_EXTS: Final[Set[str]] = set()
IGNORE_STEMS: Final[Set[str]] = {
    "__pycache__",
    ".DS_Store",
    ".git",
    "LICENSE",
    "README",
}
NO_DASH_EXTS: Final[Set[str]] = {
    ".py",
}
OK_EXTS: Final[Set[str]] = {
    ".cmd",
    ".ipynb",
    ".md",
    ".ps1",
    ".R",
    ".Rmd",
    ".rst",
    ".yaml",
    ".yml",
}
PREFIXES: Final[Set[str]] = {
    "_",
    ".",
}
SUFFIXES: Final[Set[str]] = {
    "_",
}

LOG_CONSOLE_FORMAT: Final[str] = "[%(levelname)s] %(message)s"
LOG_FILE_FORMAT: Final[str] = "%(asctime)s [%(levelname)s] %(message)s"
LOG_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"
