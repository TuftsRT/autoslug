import argparse
import logging
import mimetypes
import subprocess
from pathlib import Path
from typing import Optional, Set, Tuple

from fs.base import FS

from autoslug.autoslug import get_fs, process_path
from autoslug.defaults import (
    EXT_MAP,
    IGNORE_EXTS,
    IGNORE_STEMS,
    NO_DASH_EXTS,
    OK_EXTS,
    PREFIXES,
    SUFFIXES,
)
from autoslug.logging import get_logger


def get_log_level(quiet: bool, verbose: bool) -> int:
    if quiet:
        return logging.ERROR
    elif verbose:
        return logging.DEBUG
    return logging.INFO


def get_ok_exts(additions: Set[str]) -> Set[str]:
    ext_set = set(mimetypes.types_map.keys())
    ext_set.update(additions)
    return ext_set


def is_git_repository(path: str) -> Tuple[bool, Optional[bool]]:
    try:
        subprocess.run(
            ["git", "-C", path, "rev-parse"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True, True
    except subprocess.CalledProcessError:
        return True, False
    except FileNotFoundError:
        return False, None


def check_git_repository(path: str, force: bool, logger: logging.Logger) -> None:
    test_ok, is_git = is_git_repository(path=path)
    if not test_ok:
        msg = "unable to determine whether path is within git repository"
    elif not is_git:
        msg = "specified path is not within a git repository"
    if (not test_ok or not is_git) and not force:
        logger.critical(f"{msg}: {path}")
        logger.warning("actions might be destructive and irreversible")
        logger.info("run again with --force to override and process anyway")
        exit(1)
    return None


def assert_path(path: str, logger: logging.Logger) -> None:
    if not Path(path).exists():
        logger.critical(f"specified path does not exist: {path}")
        exit(1)
    return None


def perform_checks(path: str, force: bool, logger: logging.Logger) -> None:
    assert_path(path=path, logger=logger)
    check_git_repository(path=path, force=force, logger=logger)
    return None


def get_help_text(
    message: str, defaults: Set[str], suffix: Optional[str] = None
) -> str:
    if not defaults:
        return message
    defaults: list[str] = sorted(defaults)
    text = message + " in addition to "
    if len(defaults) >= 2 and suffix is not None:
        text += '"' + '", "'.join(defaults) + '", and ' + suffix
    elif len(defaults) > 2:
        text += '"' + '", "'.join(defaults[:-1]) + '", and "' + defaults[-1] + '"'
    elif len(defaults) == 2:
        text += f'"{defaults[0]}" and "{defaults[1]}"'
    elif suffix is not None:
        text += '"' + defaults[0] + '" and ' + suffix
    else:
        text += '"' + defaults[0] + '"'
    return text


def parse_arguments(
    ok_exts: Set[str],
    ignore_stems: Set[str],
    ignore_exts: Set[str],
    no_dash_exts: Set[str],
    prefixes: Set[str],
    suffixes: Set[str],
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="automatically rename files and directories to be URL-friendly",
    )
    parser.add_argument(
        "path",
        type=str,
        help="path to the file or directory to process",
        metavar="<path>",
    )
    parser.add_argument(
        "-d",
        "-n",
        "--dry-run",
        action="store_true",
        help="do not actually rename files or directories",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="disable protections and force processing",
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="suppress all output except errors"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help=(
            "output information about all paths processed\n"
            "(only renamed paths outputted by default)"
        ),
    )
    parser.add_argument(
        "--error-limit",
        type=int,
        default=None,
        help="exit failure if any path exceeds this character limit",
        metavar="<int>",
    )
    parser.add_argument(
        "--ignore",
        type=str,
        nargs="*",
        default=[],
        help=get_help_text(
            message="stems to ignore (without extension)", defaults=ignore_stems
        ),
        metavar="<str>",
    )
    parser.add_argument(
        "--ignore-ext",
        type=str,
        nargs="*",
        default=[],
        help=get_help_text(
            message="file extensions (with period) to ignore", defaults=ignore_exts
        ),
        metavar="<str>",
    )
    parser.add_argument(
        "--ignore-root",
        action="store_true",
        help=(
            "only process children of the specified path\n"
            "(implied when running in current directory)"
        ),
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default=None,
        help="log output to specified file",
        metavar="<path>",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=None,
        help=(
            "attempt to shorten file and directory names to not\n"
            "exceed this number of characters (excluding extension)"
        ),
        metavar="<int>",
    )
    parser.add_argument(
        "--no-dash",
        type=str,
        nargs="*",
        default=[],
        help=get_help_text(
            message=(
                "file extensions (with period) where "
                "underscores should be used instead of dashes"
            ),
            defaults=no_dash_exts,
        ),
        metavar="<str>",
    )
    parser.add_argument(
        "--no-recurse",
        action="store_true",
        help="do not recurse into subdirectories",
    )
    parser.add_argument(
        "--num-digits",
        type=int,
        default=None,
        help="number of digits any numerical prefixes should consist of",
        metavar="<int>",
    )
    parser.add_argument(
        "--ok-ext",
        type=str,
        nargs="*",
        default=[],
        help=get_help_text(
            message="file extensions (with period) to recognize",
            defaults=ok_exts,
            suffix="common MIME types",
        ),
        metavar="<str>",
    )
    parser.add_argument(
        "--prefix",
        type=str,
        nargs="*",
        default=[],
        help=get_help_text(message="prefixes to not change", defaults=prefixes),
        metavar="<str>",
    )
    parser.add_argument(
        "--suffix",
        type=str,
        nargs="*",
        default=[],
        help=get_help_text(message="suffixes to not change", defaults=suffixes),
        metavar="<str>",
    )
    parser.add_argument(
        "--warn-limit",
        type=int,
        default=None,
        help="output warning if path exceeds this character limit",
        metavar="<int>",
    )
    return parser.parse_args()


def main() -> None:
    ok_exts = OK_EXTS.copy()
    ext_map = EXT_MAP.copy()
    ignore_stems = IGNORE_STEMS.copy()
    no_dash_exts = NO_DASH_EXTS.copy()
    prefixes = PREFIXES.copy()
    suffixes = SUFFIXES.copy()
    ignore_exts = IGNORE_EXTS.copy()

    args = parse_arguments(
        ok_exts=ok_exts,
        ignore_stems=ignore_stems,
        ignore_exts=ignore_exts,
        no_dash_exts=no_dash_exts,
        prefixes=prefixes,
        suffixes=suffixes,
    )

    ok_exts.update(args.ok_ext)
    ignore_stems.update(args.ignore)
    no_dash_exts.update(args.no_dash)
    prefixes.update(args.prefix)
    suffixes.update(args.suffix)
    ignore_exts.update(args.ignore_ext)

    logger = get_logger(
        console_level=get_log_level(args.quiet, args.verbose), log_file=args.log_file
    )

    perform_checks(path=args.path, force=args.force, logger=logger)

    fs: FS
    start: str
    ignore_root: bool
    ok: bool

    fs, start, ignore_root, ok = get_fs(
        path=args.path,
        ignore_root=args.ignore_root,
        dry_run=args.dry_run,
        logger=logger,
    )

    ok = (
        process_path(
            fs=fs,
            path=start,
            ignore_stems=ignore_stems,
            ok_exts=get_ok_exts(additions=ok_exts),
            no_dash_exts=no_dash_exts,
            ext_map=ext_map,
            prefixes=prefixes,
            suffixes=suffixes,
            ignore_exts=ignore_exts,
            ignore_root=ignore_root,
            no_recurse=args.no_recurse,
            logger=logger,
            warn_limit=args.warn_limit,
            error_limit=args.error_limit,
            max_length=args.max_length,
            n_digits=args.num_digits,
        )
        and ok
    )

    fs.close()

    if not ok:
        exit(1)


if __name__ == "__main__":
    main()
