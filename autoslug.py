import argparse
import mimetypes
import textwrap
from pathlib import Path

from inflection import dasherize, parameterize, underscore
from slugify import SLUG_OK, slugify


def get_ok_exts(additions: set[str]) -> set[str]:
    ext_set = set(mimetypes.types_map.keys())
    ext_set.update(additions)
    return ext_set


def handle_prefix(stem: str, prefixes: set[str]) -> tuple[str, str]:
    prefix = ""
    while stem[0] in prefixes:
        prefix += stem[0]
        stem = stem[1:]
    return prefix, stem


def process_stem(stem: str, dash: bool, prefixes: set[str]) -> str:
    prefix, stem = handle_prefix(stem=stem, prefixes=prefixes)
    new_stem = parameterize(
        slugify(
            s=underscore(stem),
            ok=(SLUG_OK + "."),
            only_ascii=True,
        )
    )
    new_stem = dasherize(new_stem) if dash else underscore(new_stem)
    return prefix + new_stem


def process_ext(ext: str, mappings: dict[str, str]) -> str:
    try:
        return mappings[ext]
    except KeyError:
        return ext


def process_change(
    path: Path,
    new_path: Path,
    verbose: bool,
    quiet: bool,
    dry_run: bool,
    warn_limit: int,
    error_limit: int,
) -> bool:
    change = path != new_path
    new_path_str = new_path.as_posix()
    new_path_len = len(new_path_str)
    if change:
        if new_path.exists():
            if not quiet:
                print(
                    "[ERROR] (conflict preventing renaming) "
                    f"{path.as_posix()} -> {new_path_str}"
                )
        else:
            if not dry_run:
                path.rename(new_path)
            if not quiet:
                print(f"[rename] {path.as_posix()} -> {new_path_str}")
    else:
        if verbose and not quiet:
            print(f"[ok] {new_path_str}")
    if error_limit is not None:
        if new_path_len > error_limit:
            print(f"[ERROR] (path exceeds {error_limit} characters) {new_path_str}")
        return False
    if warn_limit is not None:
        if new_path_len > warn_limit and not quiet:
            print(f"[WARNING] (path exceeds {warn_limit} characters) {new_path_str}")
    return not change


def process_file(
    path: Path,
    ok_exts: set[str],
    no_dash_exts: set[str],
    ext_map: dict[str, str],
    prefixes: set[str],
    verbose: bool,
    quiet: bool,
    dry_run: bool,
    warn_limit: int,
    error_limit: int,
) -> bool:
    suffix = path.suffix
    if suffix in ok_exts:
        stem = path.stem
    else:
        stem = path.name
        suffix = ""
    new_stem = (
        process_stem(stem=stem, dash=False, prefixes=prefixes)
        if suffix in no_dash_exts
        else process_stem(stem=stem, dash=True, prefixes=prefixes)
    )
    new_path = path.parent / (new_stem + process_ext(ext=suffix, mappings=ext_map))
    return process_change(
        path=path,
        new_path=new_path,
        verbose=verbose,
        quiet=quiet,
        dry_run=dry_run,
        warn_limit=warn_limit,
        error_limit=error_limit,
    )


def process_dir(
    path: Path,
    ignore_stems: set[str],
    ok_exts: set[str],
    no_dash_exts: set[str],
    ext_map: dict[str, str],
    prefixes: set[str],
    ignore_root: bool,
    no_recurse: bool,
    verbose: bool,
    quiet: bool,
    dry_run: bool,
    warn_limit: int,
    error_limit: int,
) -> bool:
    ok = True
    if not no_recurse:
        for subpath in path.iterdir():
            ok = (
                process_path(
                    path=subpath,
                    ignore_stems=ignore_stems,
                    ok_exts=ok_exts,
                    no_dash_exts=no_dash_exts,
                    ext_map=ext_map,
                    prefixes=prefixes,
                    ignore_root=False,
                    no_recurse=False,
                    quiet=quiet,
                    verbose=verbose,
                    dry_run=dry_run,
                    warn_limit=warn_limit,
                    error_limit=error_limit,
                )
                and ok
            )
    if not ignore_root:
        new_path = path.parent / process_stem(
            stem=path.name, dash=True, prefixes=prefixes
        )
        ok = (
            process_change(
                path=path,
                new_path=new_path,
                verbose=verbose,
                quiet=quiet,
                dry_run=dry_run,
                warn_limit=warn_limit,
                error_limit=error_limit,
            )
            and ok
        )
    elif verbose and not quiet:
        print(f"[ignore] {path.as_posix()}")
    return ok


def process_path(
    path: Path,
    ignore_stems: set[str],
    ok_exts: set[str],
    no_dash_exts: set[str],
    ext_map: dict[str, str],
    prefixes: set[str],
    ignore_root: bool,
    no_recurse: bool,
    verbose: bool,
    quiet: bool,
    dry_run: bool,
    warn_limit: int,
    error_limit: int,
) -> bool:
    if not path.exists():
        raise SystemExit(f"[ERROR] (specified path does not exist) {path.as_posix()}")
    elif path.stem in ignore_stems:
        if verbose and not quiet:
            print(f"[ignore] {path.as_posix()}")
        return True
    elif path.is_dir():
        return process_dir(
            path=path,
            ignore_stems=ignore_stems,
            ok_exts=ok_exts,
            no_dash_exts=no_dash_exts,
            ext_map=ext_map,
            prefixes=prefixes,
            ignore_root=ignore_root,
            no_recurse=no_recurse,
            verbose=verbose,
            quiet=quiet,
            dry_run=dry_run,
            warn_limit=warn_limit,
            error_limit=error_limit,
        )
    elif path.is_file():
        return process_file(
            path=path,
            ok_exts=ok_exts,
            no_dash_exts=no_dash_exts,
            ext_map=ext_map,
            prefixes=prefixes,
            quiet=quiet,
            verbose=verbose,
            dry_run=dry_run,
            warn_limit=warn_limit,
            error_limit=error_limit,
        )
    else:
        if verbose and not quiet:
            print(f"[skip] {path.as_posix()}")
        return True


def get_help_text(
    message: str, defaults: set[str], chars: int = 55, suffix: str | None = None
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
    return textwrap.fill(text, width=chars)


def parse_arguments(
    ok_exts: set[str],
    ignore_stems: set[str],
    no_dash_exts: set[str],
    prefixes: set[str],
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="automatically rename files and directories to be URL-friendly",
        usage="%(prog)s [options] PATH",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "path",
        type=str,
        help="path to the file or directory to process",
        metavar="PATH",
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
        "--no-recurse",
        action="store_true",
        help="do not recurse into subdirectories",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help=(
            "output information about all paths processed\n"
            "(only renamed paths outputted by default)"
        ),
    )
    parser.add_argument(
        "--quiet", action="store_true", help="suppress all output except errors"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="do not actually rename files or directories",
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
        metavar="STR",
    )
    parser.add_argument(
        "--ignore",
        type=str,
        nargs="*",
        default=[],
        help=get_help_text(
            message="stems to ignore (without extension)", defaults=ignore_stems
        ),
        metavar="STR",
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
        metavar="STR",
    )
    parser.add_argument(
        "--prefix",
        type=str,
        nargs="*",
        default=[],
        help=get_help_text(message="prefixes to not change", defaults=prefixes),
        metavar="STR",
    )
    parser.add_argument(
        "--warn-limit",
        type=int,
        default=None,
        help="output warning if path exceeds this character limit",
        metavar="INT",
    )
    parser.add_argument(
        "--error-limit",
        type=int,
        default=None,
        help="exit failure if any path exceeds this character limit",
        metavar="INT",
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
    ignore_stems = {".DS_Store", ".git", "README", "LICENSE"}
    no_dash_exts = {".py"}
    prefixes = {"_", "."}

    args = parse_arguments(
        ok_exts=ok_exts,
        ignore_stems=ignore_stems,
        no_dash_exts=no_dash_exts,
        prefixes=prefixes,
    )

    ok_exts.update(args.ok_ext)
    ignore_stems.update(args.ignore)
    no_dash_exts.update(args.no_dash)
    prefixes.update(args.prefix)

    ok = process_path(
        path=Path(args.path),
        ignore_stems=ignore_stems,
        ok_exts=get_ok_exts(additions=ok_exts),
        no_dash_exts=no_dash_exts,
        ext_map=ext_map,
        prefixes=prefixes,
        ignore_root=(True if args.path == "." else args.ignore_root),
        no_recurse=args.no_recurse,
        verbose=args.verbose,
        quiet=args.quiet,
        dry_run=args.dry_run,
        warn_limit=args.warn_limit,
        error_limit=args.error_limit,
    )

    if not ok:
        exit(1)


if __name__ == "__main__":
    main()
