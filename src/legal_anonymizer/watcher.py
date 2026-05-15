from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from watchdog.events import FileCreatedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from legal_anonymizer.config import INPUT_EXTENSIONS, RESTORE_EXTENSIONS
from legal_anonymizer.pipeline import anonymize_file, restore_file_auto
from legal_anonymizer.workspace import WorkspacePaths

StatusCallback = Callable[[str], None]


class LegalAnonymizerHandler(FileSystemEventHandler):
    def __init__(self, workspace: WorkspacePaths, status: StatusCallback) -> None:
        self.workspace = workspace
        self.status = status

    def on_created(self, event: FileCreatedEvent) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        time.sleep(0.5)
        try:
            if path.parent == self.workspace.pending and path.suffix.lower() in INPUT_EXTENSIONS:
                result = anonymize_file(path, self.workspace)
                if result.upload_allowed:
                    self.status(f"已通过自动漏扫，可上传 AI: {result.output_path.name}")
                else:
                    self.status(f"自动漏扫未通过，已放入需要复核目录: {result.output_path.name}")
            elif path.parent == self.workspace.restore_pending and path.suffix.lower() in RESTORE_EXTENSIONS:
                result = restore_file_auto(path, self.workspace)
                if result.unknown_placeholders:
                    self.status("已还原，但存在无法识别的占位符，请人工复核。")
                else:
                    self.status(f"已还原 AI 结果文件: {result.output_path.name}")
        except Exception as exc:
            self.status(f"处理失败: {exc}")


def start_observer(workspace: WorkspacePaths, status: StatusCallback) -> Observer:
    observer = Observer()
    handler = LegalAnonymizerHandler(workspace, status)
    observer.schedule(handler, str(workspace.pending), recursive=False)
    observer.schedule(handler, str(workspace.restore_pending), recursive=False)
    observer.start()
    return observer
