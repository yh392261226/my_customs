"""
跨进程非阻塞文件锁
==================

用于同一台机器上多个 NewReader 实例之间抢占一次性任务（如静置自动一键爬取）。

Unix/macOS 使用 ``fcntl.flock``，进程异常退出时由内核自动释放锁；
Windows 使用 ``msvcrt.locking``，兼容本机多实例场景。
"""

from __future__ import annotations

import os
import time
from typing import Optional


class NonBlockingFileLock:
    """非阻塞独占文件锁；一个对象对应一个锁文件。"""

    def __init__(self, path: str) -> None:
        self.path = os.path.abspath(os.path.expanduser(path))
        self._fd: Optional[int] = None

    @property
    def is_held(self) -> bool:
        """当前对象是否持有锁。"""
        return self._fd is not None

    def acquire(self) -> bool:
        """尝试加锁；已被其它进程持有时立即返回 False。"""
        if self._fd is not None:
            return True

        directory = os.path.dirname(self.path) or "."
        os.makedirs(directory, exist_ok=True)
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            if os.name == "nt":
                import msvcrt
                os.lseek(fd, 0, os.SEEK_SET)
                if os.fstat(fd).st_size == 0:
                    os.write(fd, b" ")
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

            os.ftruncate(fd, 0)
            os.lseek(fd, 0, os.SEEK_SET)
            os.write(fd, f"pid={os.getpid()} time={time.time()}\n".encode("utf-8"))
            os.fsync(fd)
            self._fd = fd
            return True
        except (BlockingIOError, OSError):
            try:
                os.close(fd)
            except OSError:
                pass
            return False

    def release(self) -> None:
        """释放当前对象持有的锁。"""
        if self._fd is None:
            return
        fd, self._fd = self._fd, None
        try:
            if os.name == "nt":
                import msvcrt
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            try:
                os.close(fd)
            except OSError:
                pass


def is_locked_by_other(path: str) -> bool:
    """检测锁文件当前是否被其它进程占用。"""
    probe = NonBlockingFileLock(path)
    if probe.acquire():
        probe.release()
        return False
    return True
