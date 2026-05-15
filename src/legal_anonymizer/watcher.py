from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from watchdog.events import FileCreatedEvent, FileModifiedEvent, FileMovedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from legal_anonymizer.config import INPUT_EXTENSIONS, RESTORE_EXTENSIONS
from legal_anonymizer.learning import mark_processed, was_processed
from legal_anonymizer.pipeline import anonymize_file, restore_file_auto
from legal_anonymizer.workspace import WorkspacePaths

StatusCallback = Callable[[str], None]


class LegalAnonymizerHandler(FileSystemEventHandler):
    def __init__(self, workspace: WorkspacePaths, status: StatusCallback) -> None:
        self.workspace = workspace
        self.status = status
        self._processed: set[Path] = set()

    def on_created(self, event: FileCreatedEvent) -> None:
        if not event.is_directory:
            self.handle_path(Path(event.src_path))

    def on_modified(self, event: FileModifiedEvent) -> None:
        if not event.is_directory:
            self.handle_path(Path(event.src_path))

    def on_moved(self, event: FileMovedEvent) -> None:
        if not event.is_directory:
            self.handle_path(Path(event.dest_path))

    def scan_existing(self) -> None:
        for folder in (self.workspace.pending, self.workspace.restore_pending):
            for path in folder.iterdir():
                if path.is_file():
                    self.handle_path(path)

    def handle_path(self, path: Path) -> None:
        path = path.resolve()
        if path in self._processed or path.name.startswith("~$"):
            return
        try:
            _wait_until_stable(path)
            pending = self.workspace.pending.resolve()
            restore_pending = self.workspace.restore_pending.resolve()
            if path.parent == pending and path.suffix.lower() in INPUT_EXTENSIONS:
                if was_processed(path, self.workspace.mappings):
                    return
                self._processed.add(path)
                self.status(f"开始匿名化: {path.name}")
                result = anonymize_file(path, self.workspace)
                mark_processed(path, self.workspace.mappings)
                if result.upload_allowed:
                    self.status(f"已通过自动漏扫，可上传 AI: {result.output_path.name}")
                else:
                    self.status(f"自动漏扫未通过，已放入需要复核目录: {result.output_path.name}")
            elif path.parent == restore_pending and path.suffix.lower() in RESTORE_EXTENSIONS:
                if was_processed(path, self.workspace.mappings):
                    return
                self._processed.add(path)
                self.status(f"开始还原: {path.name}")
                result = restore_file_auto(path, self.workspace)
                mark_processed(path, self.workspace.mappings)
                if result.unknown_placeholders:
                    self.status("已还原，但存在无法识别的占位符，请人工复核。")
                else:
                    self.status(f"已还原 AI 结果文件: {result.output_path.name}")
            elif path.parent == pending:
                self.status(f"暂不支持该文件类型: {path.name}。请使用 .docx、可复制 PDF、txt 或 md。")
        except Exception as exc:
            self._processed.discard(path)
            self.status(f"处理失败: {path.name}: {exc}")


def start_observer(workspace: WorkspacePaths, status: StatusCallback) -> Observer:
    observer = Observer()
    handler = LegalAnonymizerHandler(workspace, status)
    observer.schedule(handler, str(workspace.pending), recursive=False)
    observer.schedule(handler, str(workspace.restore_pending), recursive=False)
    observer.start()
    handler.scan_existing()
    return observer


def _wait_until_stable(path: Path, attempts: int = 10, delay: float = 0.4) -> None:
    previous_size = -1
    for _ in range(attempts):
        if not path.exists():
            time.sleep(delay)
            continue
        current_size = path.stat().st_size
        if current_size == previous_size:
            return
        previous_size = current_size
        time.sleep(delay)
