from logging import Logger
from os import getcwd, rename
from pathlib import Path
from typing import Tuple

from fs.base import FS
from fs.errors import DirectoryExpected, FileExpected
from fs.memoryfs import MemoryFS
from fs.osfs import OSFS
from fs.path import join

from autoslug.logging import log_access_denied


def _os_rename(fs: FS, old: str, new: str) -> bool:
    try:
        rename(src=fs.getospath(old), dst=fs.getospath(new))
    except PermissionError:
        return False
    return True


def _fs_rename(fs: FS, old: str, new: str) -> bool:
    try:
        if fs.isfile(old):
            fs.move(src_path=old, dst_path=new)
        else:
            fs.movedir(src_path=old, dst_path=new, create=True)
    except (FileExpected, DirectoryExpected):
        return False
    return True


def rename(fs: FS, old: str, new: str) -> bool:
    try:
        if fs.getmeta()["supports_rename"]:
            return _os_rename(fs=fs, old=old, new=new)
    except KeyError:
        pass
    return _fs_rename(fs=fs, old=old, new=new)


def _copy_structure(
    src_fs: FS, dst_fs: FS, src_path: str, dst_path: str, logger: Logger
) -> bool:
    ok = True
    if src_fs.isdir(src_path):
        dst_fs.makedirs(dst_path, recreate=True)
        try:
            for subpath in src_fs.scandir(src_path):
                ok = (
                    _copy_structure(
                        src_fs=src_fs,
                        dst_fs=dst_fs,
                        src_path=join(src_path, subpath.name),
                        dst_path=join(dst_path, subpath.name),
                        logger=logger,
                    )
                    and ok
                )
        except DirectoryExpected:
            log_access_denied(path=src_path, logger=logger)
            return False
    elif src_fs.isfile(src_path):
        dst_fs.create(dst_path)
    return ok


def get_filesystem(
    path: Path, ignore_root: bool, dry_run: bool, logger: Logger
) -> Tuple[FS, str, bool, bool]:
    ok = True
    if path.resolve().as_posix() == Path(getcwd()).resolve().as_posix():
        ignore_root = True
        root = path.as_posix()
        start = "/"
    else:
        root = path.parent.as_posix()
        start = path.name
    if dry_run:
        fs = MemoryFS()
        with OSFS(root) as osfs:
            ok = _copy_structure(
                src_fs=osfs, dst_fs=fs, src_path=start, dst_path=start, logger=logger
            )
    else:
        fs = OSFS(root)
    return fs, start, ignore_root, ok
