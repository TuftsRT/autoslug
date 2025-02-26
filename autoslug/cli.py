import argparse
from typing import Optional, Set

from fs.base import FS

from autoslug.autoslug import (
    assert_path,
    check_git_repository,
    get_fs,
    get_ok_exts,
    process_path,
)


def get_help_text(
    message: str, defaults: Set[str], suffix: Optional[str] = None
) -> str:
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
        "--ignore-root",
        action="store_true",
        help=(
            "only process children of the specified path\n"
            "(implied when running in current directory)"
        ),
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
    ok_exts = {
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
    ext_map = {".yml": ".yaml"}
    ignore_stems = {".DS_Store", ".git", "README", "LICENSE", "__pycache__"}
    no_dash_exts = {".py"}
    prefixes = {".", "_"}
    suffixes = {"_"}

    args = parse_arguments(
        ok_exts=ok_exts,
        ignore_stems=ignore_stems,
        no_dash_exts=no_dash_exts,
        prefixes=prefixes,
        suffixes=suffixes,
    )

    ok_exts.update(args.ok_ext)
    ignore_stems.update(args.ignore)
    no_dash_exts.update(args.no_dash)
    prefixes.update(args.prefix)
    suffixes.update(args.suffix)

    assert_path(args.path)
    check_git_repository(path=args.path, force=args.force)

    fs: FS
    start: str
    ignore_root: bool
    ok: bool

    fs, start, ignore_root, ok = get_fs(
        path=args.path, ignore_root=args.ignore_root, dry_run=args.dry_run
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
            ignore_root=ignore_root,
            no_recurse=args.no_recurse,
            verbose=args.verbose,
            quiet=args.quiet,
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
