from mimetypes import types_map
from pathlib import Path
from typing import Set

from autoslug.defaults import IGNORE_GLOBS, NO_DASH_EXTS, OK_EXTS, PREFIXES, SUFFIXES


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
        "help": "exit failure if any path exceeds this character limit",
        "metavar": "<int>",
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
        "help": "log output to specified file",
        "metavar": "<path>",
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
        "help": "do not recurse into subdirectories",
    },
    "num_digits": {
        "default": None,
        "help": "number of digits any numerical prefixes should consist of",
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
        "help": "suppress all output except errors",
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
            "output information about all paths processed "
            "(only renamed paths outputted by default)"
        ),
        "shorthands": ["v"],
    },
    "warn_limit": {
        "default": None,
        "help": "output warning if path exceeds this character limit",
        "metavar": "<n>",
        "type": int,
    },
}
