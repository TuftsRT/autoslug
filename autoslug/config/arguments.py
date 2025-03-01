from mimetypes import types_map
from pathlib import Path
from typing import Set

from autoslug.config.defaults import (
    IGNORE_GLOBS,
    NO_DASH_EXTS,
    OK_EXTS,
    PREFIXES,
    SUFFIXES,
)


def add_mime_types(exts: Set[str]) -> Set[str]:
    return exts.union(set(types_map.keys()))


POSITIONAL = [
    {
        "path": {
            "help": "path to the file or directory to process",
            "metavar": "<path>",
            "type": str,
            "postprocess": [lambda x: Path(x).resolve()],
        }
    }
]

OPTIONAL = {
    "dry_run": {
        "action": "store_true",
        "help": "do not actually rename files or directories",
        "shorthands": ["d", "n"],
    },
    "error_limit": {
        "default": None,
        "help": (
            "set exit level to failure if any paths exceed this character limit "
            "(will still attempt to process all paths)"
        ),
        "metavar": "<n>",
        "type": int,
    },
    "force": {
        "action": "store_true",
        "help": "disable protections and force processing",
        "shorthands": ["f"],
    },
    "ignore_globs": {
        "action": "extend",
        "default": list(IGNORE_GLOBS),
        "help": "glob patterns to ignore",
        "metavar": "<glob>",
        "nargs": "*",
        "postprocess": [set],
        "type": str,
    },
    "ignore_root": {
        "action": "store_true",
        "help": (
            "only process children of the specified path "
            "(implied when running in current directory)"
        ),
    },
    "log_file": {
        "default": None,
        "help": (
            "log output to specified file "
            "(all messages logged to file regardless of log level)"
        ),
        "metavar": "<path>",
        "type": str,
    },
    "log_level": {
        "choices": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        "default": "INFO",
        "help": (
            "set the console logging level to one of "
            "DEBUG, INFO (default), WARNING, ERROR, or CRITICAL "
            "(overrides --quiet and --verbose)"
        ),
        "metavar": "<level>",
        "type": str,
    },
    "max_length": {
        "default": None,
        "help": (
            "attempt to shorten file and directory names "
            "to not exceed this number of characters (excluding extension)"
        ),
        "metavar": "<n>",
        "type": int,
    },
    "no_dash_exts": {
        "action": "extend",
        "default": list(NO_DASH_EXTS),
        "help": (
            "file extensions (without periods) "
            "where underscores should be used instead of dashes"
        ),
        "metavar": "<ext>",
        "nargs": "*",
        "postprocess": [set, lambda x: {f".{ext}" for ext in x}],
        "type": str,
    },
    "no_recurse": {
        "action": "store_true",
        "help": "do not recurse into subdirectories (only process specified path)",
    },
    "num_digits": {
        "default": None,
        "help": (
            "attempt to pad or round any existing numerical prefixes "
            "to consist of this many digits"
        ),
        "metavar": "<n>",
        "type": int,
    },
    "ok_exts": {
        "action": "extend",
        "default": list(OK_EXTS),
        "help": "file extensions (without periods) to recognize",
        "help_suffix": (
            "and common MIME types "
            "(all other extensions are treated as part of the filename)"
        ),
        "metavar": "<ext>",
        "nargs": "*",
        "postprocess": [
            set,
            lambda x: {f".{ext}" for ext in x},
            lambda x: add_mime_types(x),
        ],
        "type": str,
    },
    "prefixes": {
        "action": "extend",
        "default": list(PREFIXES),
        "help": "file or directory name prefixes to leave unchanged",
        "metavar": "<prefix>",
        "nargs": "*",
        "postprocess": [set],
        "type": str,
    },
    "quiet": {
        "action": "store_true",
        "help": (
            "suppress all output except errors "
            "(equivalent to setting --log-level=ERROR)"
        ),
        "shorthands": ["q"],
    },
    "suffixes": {
        "action": "extend",
        "default": list(SUFFIXES),
        "help": "file or directory name suffices (before extension) to leave unchanged",
        "metavar": "<suffix>",
        "nargs": "*",
        "postprocess": [set],
        "type": str,
    },
    "verbose": {
        "action": "store_true",
        "help": (
            "report skipped and ignored paths in addition to renamed ones"
            "(equivalent to setting --log-level=DEBUG, overrides --quiet)"
        ),
        "shorthands": ["v"],
    },
    "warn_limit": {
        "default": None,
        "help": (
            "output warning if path exceeds this character limit "
            "(does not affect exit level)"
        ),
        "metavar": "<n>",
        "type": int,
    },
}
