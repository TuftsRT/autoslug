import mimetypes
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, Optional, Set, Tuple

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


def handle_affixes(
    stem: str, prefixes: Set[str], suffixes: Set[str]
) -> Tuple[str, str, str]:
    prefix_pattern = "|".join(re.escape(prefix) + "+" for prefix in prefixes)
    suffix_pattern = "|".join(re.escape(suffix) + "+" for suffix in suffixes)
    pattern = f"^({prefix_pattern})?(.+?)({suffix_pattern})?$"
    match = re.match(pattern, stem)
    if match:
        prefix = match.group(1) or ""
        stem = match.group(2) or ""
        suffix = match.group(3) or ""
    else:
        prefix = ""
        suffix = ""
    return prefix, stem, suffix


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
    suffixes: Set[str],
    max_length: Optional[int],
    n_digits: Optional[int],
) -> str:
    prefix, stem, suffix = handle_affixes(
        stem=stem, prefixes=prefixes, suffixes=suffixes
    )
    stem = parameterize(
        slugify(
            s=underscore(stem),
            ok=(SLUG_OK + "."),
            only_ascii=True,
        )
    )
    stem = dasherize(stem) if dash else underscore(stem)
    sep = "-" if dash else "_"
    stem = re.sub(f"{sep}+", sep, stem).strip(sep)
    digits, stem = extract_leading_digits(stem=stem, sep=sep, n=n_digits)
    if max_length is not None:
        if prefix is not None:
            max_length -= len(prefix)
            if len(digits) > 0:
                max_length -= len(digits) + len(sep)
        stem = shorten_stem(stem=stem, max_length=max_length, sep=sep)
    return prefix + (digits + sep if len(digits) > 0 else "") + stem + suffix


def process_ext(ext: str, mappings: Dict[str, str]) -> str:
    try:
        return mappings[ext]
    except KeyError:
        return ext


def os_rename(fs: FS, old: str, new: str) -> bool:
    try:
        os.rename(src=fs.getospath(old), dst=fs.getospath(new))
    except PermissionError:
        print(f"[ERROR] (access denied) {old} -> {new}")
        return False
    return True


def fs_rename(fs: FS, old: str, new: str) -> bool:
    try:
        if fs.isfile(old):
            fs.move(src_path=old, dst_path=new)
        else:
            fs.movedir(src_path=old, dst_path=new, create=True)
    except (FileExpected, DirectoryExpected):
        print(f"[ERROR] (access denied) {old} -> {new}")
        return False
    return True


def rename(fs: FS, old: str, new: str) -> bool:
    try:
        if fs.getmeta()["supports_rename"]:
            return os_rename(fs=fs, old=old, new=new)
    except KeyError:
        pass
    return fs_rename(fs=fs, old=old, new=new)


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
            if rename(fs=fs, old=path, new=new_path) and not quiet:
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
    suffixes: Set[str],
    ignore_exts: Set[str],
    verbose: bool,
    quiet: bool,
    warn_limit: Optional[int],
    error_limit: Optional[int],
    max_length: Optional[int],
    n_digits: Optional[int],
) -> bool:
    suffix = splitext(path)[1]
    if suffix in ignore_exts:
        if verbose and not quiet:
            print(f"[ignore] {path}")
        return True
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
            suffixes=suffixes,
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
    suffixes: Set[str],
    ignore_exts: Set[str],
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
                suffixes=suffixes,
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
                        suffixes=suffixes,
                        ignore_exts=ignore_exts,
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
    suffixes: Set[str],
    ignore_exts: Set[str],
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
            suffixes=suffixes,
            ignore_exts=ignore_exts,
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
            suffixes=suffixes,
            ignore_exts=ignore_exts,
            quiet=quiet,
            verbose=verbose,
            warn_limit=warn_limit,
            error_limit=error_limit,
            max_length=max_length,
            n_digits=n_digits,
        )
    else:
        return True


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
