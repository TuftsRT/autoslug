import argparse
import mimetypes
import os
import subprocess
from pathlib import Path
from typing import Callable, Dict, Optional, Set, Tuple

from fs.base import FS
from fs.errors import DirectoryExpected, FileExpected
from fs.memoryfs import MemoryFS
from fs.osfs import OSFS
from fs.path import basename, dirname, join, splitext
from inflection import dasherize, parameterize, underscore
from slugify import SLUG_OK, slugify


def copy_structure(src_fs: FS, dst_fs: FS, src_path: str, dst_path: str) -> bool:
    ok = True
    if src_fs.isdir(src_path):
        dst_fs.makedirs(dst_path, recreate=True)
        try:
            for subpath in src_fs.scandir(src_path):
                ok = (
                    copy_structure(
                        src_fs=src_fs,
                        dst_fs=dst_fs,
                        src_path=join(src_path, subpath.name),
                        dst_path=join(dst_path, subpath.name),
                    )
                    and ok
                )
        except DirectoryExpected:
            print(f"[ERROR] (access denied) {src_path}")
            return False
    elif src_fs.isfile(src_path):
        dst_fs.create(dst_path)
    return ok


def get_ok_exts(additions: Set[str]) -> Set[str]:
    ext_set = set(mimetypes.types_map.keys())
    ext_set.update(additions)
    return ext_set


def handle_prefix(stem: str, prefixes: Set[str]) -> Tuple[str, str]:
    prefix = ""
    while stem[0] in prefixes:
        prefix += stem[0]
        stem = stem[1:]
    return prefix, stem


def shorten_stem(stem: str, max_length: Optional[int], sep: str) -> str:
    if len(stem) <= max_length:
        return stem
    parts = stem.split(sep)
    new_stem = parts.pop(0)
    for part in parts:
        if len(new_stem) + len(sep) + len(part) > max_length:
            break
        new_stem += sep + part
    return new_stem


def extract_leading_digits(stem: str, sep: str, n: Optional[int]) -> Tuple[str, str]:
    if n is not None:
        parts = stem.split(sep)
        try:
            if parts[0].isdigit() and parts[1].isalpha():
                number = str(min(int(parts[0]), 10**n - 1)).zfill(n)
                return number, sep.join(parts[1:])
        except IndexError:
            pass
    return "", stem


def process_stem(
    stem: str,
    dash: bool,
    prefixes: Set[str],
    max_length: Optional[int],
    n_digits: Optional[int],
) -> str:
    prefix, stem = handle_prefix(stem=stem, prefixes=prefixes)
    stem = parameterize(
        slugify(
            s=underscore(stem),
            ok=(SLUG_OK + "."),
            only_ascii=True,
        )
    )
    stem = dasherize(stem) if dash else underscore(stem)
    sep = "-" if dash else "_"
    digits, stem = extract_leading_digits(stem=stem, sep=sep, n=n_digits)
    if max_length is not None:
        if prefix is not None:
            max_length -= len(prefix)
            if len(digits) > 0:
                max_length -= len(digits) + len(sep)
        stem = shorten_stem(stem=stem, max_length=max_length, sep=sep)
    return prefix + (digits + sep if len(digits) > 0 else "") + stem


def process_ext(ext: str, mappings: Dict[str, str]) -> str:
    try:
        return mappings[ext]
    except KeyError:
        return ext


def get_rename_function(fs: FS, path: str) -> Callable[[str, str], bool]:
    try:
        if fs.getmeta()["supports_rename"]:

            def rename(old: str, new: str) -> bool:
                try:
                    os.rename(src=fs.getospath(old), dst=Path(new).name)
                except PermissionError:
                    print(f"[ERROR] (access denied) {old} -> {new}")
                    return False
                return True

    except KeyError:
        pass
    if fs.isfile(path):

        def rename(old: str, new: str) -> bool:
            try:
                fs.move(src_path=old, dst_path=new)
            except FileExpected:
                print(f"[ERROR] (access denied) {old} -> {new}")
                return False
            return True

    else:

        def rename(old: str, new: str) -> bool:
            try:
                fs.movedir(src_path=old, dst_path=new, create=True)
            except DirectoryExpected:
                print(f"[ERROR] (access denied) {old} -> {new}")
                return False
            return True

    return rename


def check_conflict(fs: FS, path: str, new_path: str) -> bool:
    try:
        if fs.getmeta()["case_insensitive"]:
            if path.lower() == new_path.lower():
                return False
    except KeyError:
        pass
    return fs.exists(new_path)


def process_change(
    fs: FS,
    path: str,
    new_path: str,
    verbose: bool,
    quiet: bool,
    warn_limit: Optional[int],
    error_limit: Optional[int],
) -> bool:
    change = path != new_path
    new_path_len = len(new_path)
    if change:
        if check_conflict(fs=fs, path=path, new_path=new_path):
            print("[ERROR] (conflict preventing renaming) " f"{path} -> {new_path}")
        else:
            if get_rename_function(fs=fs, path=path)(path, new_path) and not quiet:
                print(f"[rename] {path} -> {new_path}")
    else:
        if verbose and not quiet:
            print(f"[ok] {new_path}")
    if error_limit is not None:
        if new_path_len > error_limit:
            print(f"[ERROR] (path exceeds {error_limit} characters) {new_path}")
        return False
    if warn_limit is not None:
        if new_path_len > warn_limit and not quiet:
            print(f"[WARNING] (path exceeds {warn_limit} characters) {new_path}")
    return not change


def process_file(
    fs: FS,
    path: str,
    ok_exts: Set[str],
    no_dash_exts: Set[str],
    ext_map: Dict[str, str],
    prefixes: Set[str],
    verbose: bool,
    quiet: bool,
    warn_limit: Optional[int],
    error_limit: Optional[int],
    max_length: Optional[int],
    n_digits: Optional[int],
) -> bool:
    suffix = splitext(path)[1]
    if suffix in ok_exts:
        stem = splitext(basename(path))[0]
    else:
        stem = basename(path)
        suffix = ""
    dash = suffix not in no_dash_exts
    new_path = join(
        dirname(path),
        process_stem(
            stem=stem,
            dash=dash,
            prefixes=prefixes,
            max_length=max_length,
            n_digits=n_digits,
        )
        + process_ext(ext=suffix, mappings=ext_map),
    )
    return process_change(
        fs=fs,
        path=path,
        new_path=new_path,
        verbose=verbose,
        quiet=quiet,
        warn_limit=warn_limit,
        error_limit=error_limit,
    )


def process_dir(
    fs: FS,
    path: str,
    ignore_stems: Set[str],
    ok_exts: Set[str],
    no_dash_exts: Set[str],
    ext_map: Dict[str, str],
    prefixes: Set[str],
    ignore_root: bool,
    no_recurse: bool,
    verbose: bool,
    quiet: bool,
    warn_limit: Optional[int],
    error_limit: Optional[int],
    max_length: Optional[int],
    n_digits: Optional[int],
) -> bool:
    ok = True
    if not ignore_root:
        new_path = join(
            dirname(path),
            process_stem(
                stem=basename(path),
                dash=True,
                prefixes=prefixes,
                max_length=max_length,
                n_digits=n_digits,
            ),
        )
        ok = (
            process_change(
                fs=fs,
                path=path,
                new_path=new_path,
                verbose=verbose,
                quiet=quiet,
                warn_limit=warn_limit,
                error_limit=error_limit,
            )
            and ok
        )
        path = new_path
    if not no_recurse:
        try:
            for subpath in fs.scandir(path):
                ok = (
                    process_path(
                        fs=fs,
                        path=join(path, subpath.name),
                        ignore_stems=ignore_stems,
                        ok_exts=ok_exts,
                        no_dash_exts=no_dash_exts,
                        ext_map=ext_map,
                        prefixes=prefixes,
                        ignore_root=False,
                        no_recurse=False,
                        quiet=quiet,
                        verbose=verbose,
                        warn_limit=warn_limit,
                        error_limit=error_limit,
                        max_length=max_length,
                        n_digits=n_digits,
                    )
                    and ok
                )
        except DirectoryExpected:
            print(f"[ERROR] (access denied) {path}")
            return False
    elif verbose and not quiet:
        print(f"[ignore] {path}")
    return ok


def process_path(
    fs: FS,
    path: str,
    ignore_stems: Set[str],
    ok_exts: Set[str],
    no_dash_exts: Set[str],
    ext_map: Dict[str, str],
    prefixes: Set[str],
    ignore_root: bool,
    no_recurse: bool,
    verbose: bool,
    quiet: bool,
    warn_limit: Optional[int],
    error_limit: Optional[int],
    max_length: Optional[int],
    n_digits: Optional[int],
) -> bool:
    if splitext(basename(path))[0] in ignore_stems:
        if verbose and not quiet:
            print(f"[ignore] {path}")
        return True
    elif fs.isdir(path):
        return process_dir(
            fs=fs,
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
            warn_limit=warn_limit,
            error_limit=error_limit,
            max_length=max_length,
            n_digits=n_digits,
        )
    elif fs.isfile(path):
        return process_file(
            fs=fs,
            path=path,
            ok_exts=ok_exts,
            no_dash_exts=no_dash_exts,
            ext_map=ext_map,
            prefixes=prefixes,
            quiet=quiet,
            verbose=verbose,
            warn_limit=warn_limit,
            error_limit=error_limit,
            max_length=max_length,
            n_digits=n_digits,
        )
    else:
        return True


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
        "--warn-limit",
        type=int,
        default=None,
        help="output warning if path exceeds this character limit",
        metavar="<int>",
    )
    return parser.parse_args()


def get_fs(path: str, ignore_root: bool, dry_run: bool) -> FS:
    ok = True
    path_obj = Path(path).resolve()
    if path_obj.as_posix() == Path(os.getcwd()).resolve().as_posix():
        ignore_root = True
        root = path_obj.as_posix()
        start = "/"
    else:
        root = path_obj.parent.as_posix()
        start = path_obj.name
    if dry_run:
        fs = MemoryFS()
        with OSFS(root) as osfs:
            ok = copy_structure(
                src_fs=osfs,
                dst_fs=fs,
                src_path=start,
                dst_path=start,
            )
    else:
        fs = OSFS(root)
    return fs, start, ignore_root, ok


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


def check_git_repository(path: str, force: bool) -> None:
    test_ok, is_git = is_git_repository(path=path)
    if not test_ok:
        msg = "unable to determine whether path is within git repository"
    elif not is_git:
        msg = "specified path is not within a git repository"
    if (not test_ok or not is_git) and not force:
        raise SystemExit(
            f"[ERROR] ({msg}) {path}\n"
            "[WARNING] actions might be destructive and irreversible\n"
            "[INFO] run again with --force to override and process anyway"
        )
    return None


def assert_path(path: str) -> None:
    if not Path(path).exists():
        raise SystemExit(f"[ERROR] (specified path does not exist) {path}")
    return None


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
