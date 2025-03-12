import logging
from pathlib import Path
from subprocess import DEVNULL, CalledProcessError, run
from typing import Optional, Tuple

from autoslug.autoslug import process_path
from autoslug.config.arguments import OPTIONAL, POSITIONAL
from autoslug.config.defaults import DESCRIPTION, EXT_MAP
from autoslug.utils.filesystem import get_filesystem
from autoslug.utils.logging import get_logger
from autoslug.utils.parser import parse_arguments


def get_log_level(level: str, quiet: bool, verbose: bool) -> int:
    if level != "INFO":
        return getattr(logging, level)
    elif verbose:
        return logging.DEBUG
    elif quiet:
        return logging.ERROR
    else:
        return getattr(logging, "INFO")


def is_git_repository(path: Path) -> Optional[bool]:
    try:
        run(
            ["git", "-C", path.as_posix(), "rev-parse"],
            check=True,
            stdout=DEVNULL,
            stderr=DEVNULL,
        )
        return True
    except CalledProcessError:
        return False
    except FileNotFoundError:
        return None


def check_git_repository(path: Path, force: bool, logger: logging.Logger) -> bool:
    git_status = is_git_repository(path=path)
    if git_status:
        return True
    elif git_status is not None:
        msg = "specified path is not within a git repository"
    else:
        msg = "unable to determine whether path is within git repository"
    if not force:
        logger.critical(f"{msg}: {path.as_posix()}")
        logger.warning("actions might be destructive and irreversible")
        logger.info("run again with --force to override and process anyway")
        exit(1)
    return False


def assert_path(path: Path, logger: logging.Logger) -> None:
    if not path.exists():
        logger.critical(f"specified path does not exist: {path.as_posix()}")
        exit(1)
    return None


def perform_checks(path: Path, force: bool, logger: logging.Logger) -> bool:
    assert_path(path=path, logger=logger)
    return check_git_repository(path=path, force=force, logger=logger)


def main() -> None:

    args = parse_arguments(
        description=DESCRIPTION, positional=POSITIONAL, optional=OPTIONAL
    )

    logger = get_logger(
        console_level=get_log_level(
            level=args["log_level"], quiet=args["quiet"], verbose=args["verbose"]
        ),
        log_file=args["log_file"],
    )

    is_git_repo = perform_checks(path=args["path"], force=args["force"], logger=logger)

    if args["force"]:
        logger.warning("disabling protections and forcing processing")
    if args["dry_run"]:
        logger.info("beginning dry run (no changes will be made)")

    fs, start, ignore_root, ok = get_filesystem(
        path=args["path"],
        ignore_root=args["ignore_root"],
        dry_run=args["dry_run"],
        logger=logger,
    )

    ok = (
        process_path(
            error_limit=args["error_limit"],
            ext_map=EXT_MAP,
            fs=fs,
            ignore_globs=args["ignore_globs"],
            ignore_root=ignore_root,
            logger=logger,
            max_length=args["max_length"],
            n_digits=args["num_digits"],
            no_dash_exts=args["no_dash_exts"],
            no_recurse=args["no_recurse"],
            ok_exts=args["ok_exts"],
            path=start,
            prefixes=args["prefixes"],
            suffixes=args["suffixes"],
            warn_limit=args["warn_limit"],
        )
        and ok
    )

    fs.close()

    if not ok:
        exit(1)


if __name__ == "__main__":
    main()
