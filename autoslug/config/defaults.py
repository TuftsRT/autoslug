from typing import Dict, Final, Set

EXT_MAP: Final[Dict[str, str]] = {
    "yml": "yaml",
}
IGNORE_GLOBS: Final[Set[str]] = {
    "**/__pycache__",
    "**/.DS_Store",
    "**/.git",
    "**/.ipynb_checkpoints",
    "**/LICENSE*",
    "**/README*",
}
NO_DASH_EXTS: Final[Set[str]] = {
    "py",
}
OK_EXTS: Final[Set[str]] = {
    "cmd",
    "ipynb",
    "md",
    "ps1",
    "R",
    "Rmd",
    "rst",
    "toml",
    "yaml",
    "yml",
}
PREFIXES: Final[Set[str]] = {
    "_",
    ".",
}
SUFFIXES: Final[Set[str]] = {
    "_",
}

DESCRIPTION: Final[str] = (
    "automatically rename files and directories to be URL-friendly"
)

LOG_CONSOLE_FORMAT: Final[str] = "[%(levelname)s] %(message)s"
LOG_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"
LOG_FILE_FORMAT: Final[str] = "%(asctime)s [%(levelname)s] %(message)s"
