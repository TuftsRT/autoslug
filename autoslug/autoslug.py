import re
from logging import Logger
from typing import Dict, Optional, Set, Tuple

from fs.base import FS
from fs.errors import DirectoryExpected
from fs.path import basename, dirname, join, splitext
from inflection import dasherize, parameterize, underscore
from slugify import SLUG_OK, slugify

from autoslug.filesystem import match_globs, rename
from autoslug.logging import log_access_denied, log_ignored


def _handle_affixes(
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


def _shorten_stem(stem: str, max_length: Optional[int], sep: str) -> str:
    if len(stem) <= max_length:
        return stem
    parts = stem.split(sep)
    new_stem = parts.pop(0)
    for part in parts:
        if len(new_stem) + len(sep) + len(part) > max_length:
            break
        new_stem += sep + part
    return new_stem


def _extract_leading_digits(stem: str, sep: str, n: Optional[int]) -> Tuple[str, str]:
    if n is not None:
        parts = stem.split(sep)
        try:
            if parts[0].isdigit() and parts[1].isalpha():
                number = str(min(int(parts[0]), 10**n - 1)).zfill(n)
                return number, sep.join(parts[1:])
        except IndexError:
            pass
    return "", stem


def _process_stem(
    stem: str,
    dash: bool,
    prefixes: Set[str],
    suffixes: Set[str],
    max_length: Optional[int],
    n_digits: Optional[int],
) -> str:
    prefix, stem, suffix = _handle_affixes(
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
    digits, stem = _extract_leading_digits(stem=stem, sep=sep, n=n_digits)
    if max_length is not None:
        if prefix is not None:
            max_length -= len(prefix)
            if len(digits) > 0:
                max_length -= len(digits) + len(sep)
        stem = _shorten_stem(stem=stem, max_length=max_length, sep=sep)
    return prefix + (digits + sep if len(digits) > 0 else "") + stem + suffix


def _process_ext(ext: str, mappings: Dict[str, str]) -> str:
    try:
        return mappings[ext]
    except KeyError:
        return ext


def _check_conflict(fs: FS, path: str, new_path: str) -> bool:
    try:
        if fs.getmeta()["case_insensitive"]:
            if path.lower() == new_path.lower():
                return False
    except KeyError:
        pass
    return fs.exists(new_path)


def _process_change(
    fs: FS,
    path: str,
    new_path: str,
    logger: Logger,
    warn_limit: Optional[int],
    error_limit: Optional[int],
) -> bool:
    change = path != new_path
    new_path_len = len(new_path)
    if change:
        if _check_conflict(fs=fs, path=path, new_path=new_path):
            logger.error(f"conflict preventing renaming: {path} -> {new_path}")
        else:
            if rename(fs=fs, old=path, new=new_path):
                logger.info(f"renamed: {path} -> {new_path}")
            else:
                log_access_denied(path=path, logger=logger)
                return False
    else:
        logger.debug(f"unchanged: {path}")
    if error_limit is not None:
        if new_path_len > error_limit:
            logger.error(f"error (path exceeds {error_limit} characters): {new_path}")
        return False
    if warn_limit is not None:
        logger.warning(f"warning (path exceeds {warn_limit} characters): {new_path}")
    return not change


def _process_file(
    fs: FS,
    path: str,
    ok_exts: Set[str],
    no_dash_exts: Set[str],
    ext_map: Dict[str, str],
    prefixes: Set[str],
    suffixes: Set[str],
    logger: Logger,
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
        _process_stem(
            stem=stem,
            dash=dash,
            prefixes=prefixes,
            suffixes=suffixes,
            max_length=max_length,
            n_digits=n_digits,
        )
        + _process_ext(ext=suffix, mappings=ext_map),
    )
    return _process_change(
        fs=fs,
        path=path,
        new_path=new_path,
        logger=logger,
        warn_limit=warn_limit,
        error_limit=error_limit,
    )


def _process_dir(
    fs: FS,
    path: str,
    ignore_globs: Set[str],
    ok_exts: Set[str],
    no_dash_exts: Set[str],
    ext_map: Dict[str, str],
    prefixes: Set[str],
    suffixes: Set[str],
    ignore_root: bool,
    no_recurse: bool,
    logger: Logger,
    warn_limit: Optional[int],
    error_limit: Optional[int],
    max_length: Optional[int],
    n_digits: Optional[int],
) -> bool:
    ok = True
    if not ignore_root:
        new_path = join(
            dirname(path),
            _process_stem(
                stem=basename(path),
                dash=True,
                prefixes=prefixes,
                suffixes=suffixes,
                max_length=max_length,
                n_digits=n_digits,
            ),
        )
        ok = (
            _process_change(
                fs=fs,
                path=path,
                new_path=new_path,
                logger=logger,
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
                        ignore_globs=ignore_globs,
                        ok_exts=ok_exts,
                        no_dash_exts=no_dash_exts,
                        ext_map=ext_map,
                        prefixes=prefixes,
                        suffixes=suffixes,
                        ignore_root=False,
                        no_recurse=False,
                        logger=logger,
                        warn_limit=warn_limit,
                        error_limit=error_limit,
                        max_length=max_length,
                        n_digits=n_digits,
                    )
                    and ok
                )
        except DirectoryExpected:
            log_access_denied(path=path, logger=logger)
            return False
    else:
        log_ignored(path=path, logger=logger)
    return ok


def process_path(
    fs: FS,
    path: str,
    ignore_globs: Set[str],
    ok_exts: Set[str],
    no_dash_exts: Set[str],
    ext_map: Dict[str, str],
    prefixes: Set[str],
    suffixes: Set[str],
    ignore_root: bool,
    no_recurse: bool,
    logger: Logger,
    warn_limit: Optional[int],
    error_limit: Optional[int],
    max_length: Optional[int],
    n_digits: Optional[int],
) -> bool:
    if match_globs(fs=fs, path=path, globs=ignore_globs):
        log_ignored(path=path, logger=logger)
        return True
    elif fs.isdir(path):
        return _process_dir(
            fs=fs,
            path=path,
            ignore_globs=ignore_globs,
            ok_exts=ok_exts,
            no_dash_exts=no_dash_exts,
            ext_map=ext_map,
            prefixes=prefixes,
            suffixes=suffixes,
            ignore_root=ignore_root,
            no_recurse=no_recurse,
            logger=logger,
            warn_limit=warn_limit,
            error_limit=error_limit,
            max_length=max_length,
            n_digits=n_digits,
        )
    elif fs.isfile(path):
        return _process_file(
            fs=fs,
            path=path,
            ok_exts=ok_exts,
            no_dash_exts=no_dash_exts,
            ext_map=ext_map,
            prefixes=prefixes,
            suffixes=suffixes,
            logger=logger,
            warn_limit=warn_limit,
            error_limit=error_limit,
            max_length=max_length,
            n_digits=n_digits,
        )
    else:
        logger.debug(f"skipped (not a file or directory): {path}")
        return True
