from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from legal_anonymizer.mapping_store import load_mapping_table
from legal_anonymizer.pipeline import (
    latest_prompt_path,
    restore_pasted_text,
    restore_pasted_text_latest,
)
from legal_anonymizer.watcher import start_observer
from legal_anonymizer.workspace import create_workspace


class MainWindow(QMainWindow):
    status_changed = Signal(str)

    def __init__(self, root: Path) -> None:
        super().__init__()
        self.workspace = create_workspace(root)
        self.status_changed.connect(self.set_status)
        self.observer = start_observer(self.workspace, self.status_changed.emit)
        self.setWindowTitle("律师本地匿名化助手")
        self.status_label = QLabel("状态：正在监听文件夹")
        self.paste_box = QTextEdit()
        self.paste_box.setPlaceholderText("如果 AI 不能下载结果，把 AI 回复粘贴到这里，然后点击“粘贴AI回复并还原”。")
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(110)
        self.log_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.log_box.setPlaceholderText("处理记录会显示在这里。")

        open_pending = QPushButton("打开待匿名化文件夹")
        open_pending.clicked.connect(lambda: self.open_folder(self.workspace.pending))
        open_anonymized = QPushButton("打开可上传AI文件夹")
        open_anonymized.clicked.connect(lambda: self.open_folder(self.workspace.anonymized))
        open_review = QPushButton("打开需要复核文件夹")
        open_review.clicked.connect(lambda: self.open_folder(self.workspace.review_required))
        open_restore = QPushButton("打开AI结果待还原文件夹")
        open_restore.clicked.connect(lambda: self.open_folder(self.workspace.restore_pending))
        copy_prompt = QPushButton("复制AI提示词")
        copy_prompt.clicked.connect(self.copy_latest_prompt)
        restore_paste = QPushButton("粘贴AI回复并还原")
        restore_paste.clicked.connect(self.restore_pasted)
        restore_paste_manual = QPushButton("手动选择映射表还原")
        restore_paste_manual.clicked.connect(self.restore_pasted_manual)
        open_output = QPushButton("查看最近处理结果")
        open_output.clicked.connect(lambda: self.open_folder(self.workspace.restored))

        layout = QVBoxLayout()
        layout.addWidget(QLabel("第一步：把客户文件放进“待匿名化”。第二步：只上传“可上传AI”里的文件。第三步：AI结果下载后放回待还原，不能下载就粘贴还原。"))
        layout.addWidget(QLabel("请只上传“02-已匿名化-可上传AI”文件夹中的文件。"))
        layout.addWidget(QLabel("请不要上传“99-本地映射表-不要上传”文件夹。"))
        row = QHBoxLayout()
        for button in (
            open_pending,
            open_anonymized,
            open_review,
            copy_prompt,
            open_restore,
            restore_paste,
            restore_paste_manual,
            open_output,
        ):
            row.addWidget(button)
        layout.addLayout(row)
        layout.addWidget(self.paste_box)
        layout.addWidget(self.status_label)
        layout.addWidget(self.log_box)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        self.add_log("程序已启动。请先点击“打开待匿名化文件夹”，放入客户文件。")

    def closeEvent(self, event: Any) -> None:  # noqa: N802
        self.observer.stop()
        self.observer.join(timeout=2)
        super().closeEvent(event)

    def open_folder(self, path: Path) -> None:
        os.startfile(str(path))

    def set_status(self, message: str) -> None:
        self.status_label.setText(f"状态：{message}")
        self.add_log(message)

    def add_log(self, message: str) -> None:
        self.log_box.append(f"- {message}")

    def copy_latest_prompt(self) -> None:
        try:
            prompt_path = latest_prompt_path(self.workspace)
            QApplication.clipboard().setText(prompt_path.read_text(encoding="utf-8"))
        except Exception as exc:
            QMessageBox.warning(self, "无法复制", str(exc))
            return
        self.set_status("已复制最近一次 AI 提示词，可以粘贴到 Kimi/ChatGPT。")

    def restore_pasted(self) -> None:
        text = self.paste_box.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "无法还原", "请先粘贴 AI 回复。")
            return
        try:
            result = restore_pasted_text_latest(text, self.workspace)
        except Exception as exc:
            QMessageBox.warning(self, "无法自动还原", f"{exc}\n\n请点击“手动选择映射表还原”。")
            return
        self._finish_restore(result)

    def restore_pasted_manual(self) -> None:
        text = self.paste_box.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "无法还原", "请先粘贴 AI 回复。")
            return
        mapping_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择本地映射表",
            str(self.workspace.mappings),
            "Mapping (*.mapping.json)",
        )
        if not mapping_path:
            return
        try:
            load_mapping_table(Path(mapping_path))
            result = restore_pasted_text(text, Path(mapping_path), self.workspace)
        except Exception as exc:
            QMessageBox.critical(self, "无法还原", str(exc))
            return
        self._finish_restore(result)

    def _finish_restore(self, result) -> None:
        if result.unknown_placeholders:
            QMessageBox.warning(self, "需要人工复核", "AI 回复中存在无法识别的占位符。")
        self.set_status(f"已还原: {result.output_path.name}")


def run_app(root: Path) -> int:
    app = QApplication([])
    window = MainWindow(root)
    window.resize(780, 420)
    window.show()
    return app.exec()
