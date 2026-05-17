from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from legal_anonymizer.learning import add_memory_entry, clear_learning_memory, learning_entry_count
from legal_anonymizer.mapping_store import load_mapping_table
from legal_anonymizer.pipeline import (
    latest_prompt_path,
    restore_pasted_text,
    restore_pasted_text_latest,
)
from legal_anonymizer.watcher import start_observer
from legal_anonymizer.workspace import create_workspace


APP_STYLE = """
QWidget {
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 10pt;
    color: #1f2933;
    background: #f7f8fa;
}
QLabel#title {
    font-size: 18pt;
    font-weight: 700;
    color: #111827;
}
QLabel#subtitle {
    color: #4b5563;
}
QLabel#instruction {
    color: #1f2937;
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    padding: 10px 12px;
}
QLabel#hint {
    color: #7c2d12;
    background: #fff7ed;
    border: 1px solid #fed7aa;
    border-radius: 6px;
    padding: 8px 10px;
}
QLabel#statusLabel {
    color: #0f172a;
    background: #ecfdf5;
    border: 1px solid #bbf7d0;
    border-radius: 6px;
    padding: 8px 10px;
}
QPushButton {
    min-height: 34px;
    padding: 6px 12px;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    background: #ffffff;
}
QPushButton:hover {
    background: #f1f5f9;
}
QPushButton#primaryButton {
    font-weight: 600;
    color: #ffffff;
    border: 1px solid #2563eb;
    background: #2563eb;
}
QPushButton#primaryButton:hover {
    background: #1d4ed8;
}
QPushButton#warningButton {
    color: #9a3412;
    border: 1px solid #fdba74;
    background: #fff7ed;
}
QTextEdit {
    border: 1px solid #d1d5db;
    border-radius: 6px;
    background: #ffffff;
    padding: 8px;
}
QLineEdit, QComboBox {
    min-height: 32px;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    background: #ffffff;
    padding: 4px 8px;
}
QFrame#divider {
    color: #e5e7eb;
}
"""


class MainWindow(QMainWindow):
    status_changed = Signal(str)

    def __init__(self, root: Path) -> None:
        super().__init__()
        self.workspace = create_workspace(root)
        self.status_changed.connect(self.set_status)
        self.observer = start_observer(self.workspace, self.status_changed.emit)
        self.setWindowTitle("律师本地匿名化助手")
        self.setStyleSheet(APP_STYLE)

        title = QLabel("律师本地匿名化助手")
        title.setObjectName("title")
        subtitle = QLabel("本地处理客户文件，生成可上传 AI 的匿名版本；本地映射表不要上传。")
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)

        self.status_label = QLabel("状态：正在监听文件夹")
        self.status_label.setObjectName("statusLabel")
        self.paste_box = QTextEdit()
        self.paste_box.setPlaceholderText(
            "如果 AI 不能下载结果，把 AI 回复粘贴到这里，然后点击“粘贴AI回复并还原”。"
        )
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(140)
        self.log_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.log_box.setPlaceholderText("处理记录会显示在这里。")
        self.memory_value = QLineEdit()
        self.memory_value.setPlaceholderText("发现漏掉的姓名、公司、项目名，或不想脱敏的普通词，填在这里")
        self.memory_category = QComboBox()
        self.memory_category.addItems(["PERSON", "COMPANY", "ADDRESS", "PROJECT", "PHONE", "EMAIL", "ID", "CUSTOM"])

        open_pending = QPushButton("放原文件")
        open_pending.setObjectName("primaryButton")
        open_pending.clicked.connect(lambda: self.open_folder(self.workspace.pending))
        open_anonymized = QPushButton("拿去上传AI")
        open_anonymized.setObjectName("primaryButton")
        open_anonymized.clicked.connect(lambda: self.open_folder(self.workspace.anonymized))
        open_restore = QPushButton("放AI结果")
        open_restore.setObjectName("primaryButton")
        open_restore.clicked.connect(lambda: self.open_folder(self.workspace.restore_pending))
        open_output = QPushButton("看还原结果")
        open_output.setObjectName("primaryButton")
        open_output.clicked.connect(lambda: self.open_folder(self.workspace.restored))

        open_review = QPushButton("需要复核")
        open_review.setObjectName("warningButton")
        open_review.clicked.connect(lambda: self.open_folder(self.workspace.review_required))
        rescan = QPushButton("重新扫描")
        rescan.clicked.connect(self.rescan_folders)
        copy_prompt = QPushButton("复制AI提示词")
        copy_prompt.clicked.connect(self.copy_latest_prompt)
        restore_paste = QPushButton("粘贴AI回复并还原")
        restore_paste.clicked.connect(self.restore_pasted)
        restore_paste_manual = QPushButton("手动选择映射表还原")
        restore_paste_manual.clicked.connect(self.restore_pasted_manual)
        clear_memory = QPushButton("清空本地学习记忆")
        clear_memory.clicked.connect(self.clear_memory)
        add_blacklist = QPushButton("加入一定脱敏")
        add_blacklist.setObjectName("primaryButton")
        add_blacklist.clicked.connect(lambda: self.add_memory_rule("blacklist"))
        add_whitelist = QPushButton("加入一定不脱敏")
        add_whitelist.clicked.connect(lambda: self.add_memory_rule("whitelist"))

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        instruction = QLabel("1. 放原文件  2. 拿匿名文件上传 AI  3. 放回或粘贴 AI 结果  4. 查看还原结果")
        instruction.setObjectName("instruction")
        instruction.setWordWrap(True)
        layout.addWidget(instruction)

        warning = QLabel("旧版 .doc 处理失败时，请先用 Word/WPS 另存为 .docx。不要上传“99-本地映射表-不要上传”。")
        warning.setObjectName("hint")
        warning.setWordWrap(True)
        layout.addWidget(warning)

        review_hint = QLabel("复核补充：如果发现漏脱敏，把原词填入并点“一定脱敏”；如果普通法律词被误脱敏，点“一定不脱敏”。")
        review_hint.setObjectName("instruction")
        review_hint.setWordWrap(True)
        layout.addWidget(review_hint)

        memory_row = QHBoxLayout()
        memory_row.setSpacing(8)
        memory_row.addWidget(self.memory_category)
        memory_row.addWidget(self.memory_value, stretch=1)
        memory_row.addWidget(add_blacklist)
        memory_row.addWidget(add_whitelist)
        layout.addLayout(memory_row)

        main_row = QHBoxLayout()
        main_row.setSpacing(8)
        for button in (open_pending, open_anonymized, open_restore, open_output):
            main_row.addWidget(button)
        layout.addLayout(main_row)

        secondary_row = QHBoxLayout()
        secondary_row.setSpacing(8)
        for button in (
            open_review,
            rescan,
            copy_prompt,
            restore_paste,
            restore_paste_manual,
            clear_memory,
        ):
            secondary_row.addWidget(button)
        layout.addLayout(secondary_row)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setObjectName("divider")
        layout.addWidget(divider)

        layout.addWidget(self.paste_box)
        layout.addWidget(self.status_label)
        layout.addWidget(self.log_box)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        self.add_log("程序已启动。请点击“放原文件”，放入客户文件。")

    def closeEvent(self, event: Any) -> None:  # noqa: N802
        self.observer.stop()
        self.observer.join(timeout=2)
        super().closeEvent(event)

    def open_folder(self, path: Path) -> None:
        os.startfile(str(path))

    def set_status(self, message: str) -> None:
        self.status_label.setText(f"状态：{message}")
        self.add_log(message)
        if message.startswith("处理失败") or "暂不支持该文件类型" in message:
            QMessageBox.warning(self, "需要处理", message)
        elif "自动漏扫未通过" in message:
            QMessageBox.warning(self, "暂勿上传", f"{message}\n\n请打开“需要复核”查看处理结果说明。")

    def add_log(self, message: str) -> None:
        self.log_box.append(f"- {message}")

    def rescan_folders(self) -> None:
        self.set_status("正在重新扫描待匿名化和待还原文件夹。")
        thread = threading.Thread(target=lambda: self.observer.handler.scan_existing(force=True), daemon=True)
        thread.start()

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

    def clear_memory(self) -> None:
        count = learning_entry_count(self.workspace.mappings)
        if count == 0:
            QMessageBox.information(self, "本地学习记忆", "当前没有可清空的本地学习记忆。")
            return
        answer = QMessageBox.question(
            self,
            "清空本地学习记忆",
            f"将清空 {count} 条本地学习记忆。\n\n"
            "这不会删除已生成的对照表，也不会影响已经处理过的文件还原。",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        removed = clear_learning_memory(self.workspace.mappings)
        self.set_status(f"已清空 {removed} 条本地学习记忆。")

    def add_memory_rule(self, mode: str) -> None:
        value = self.memory_value.text().strip()
        if not value:
            QMessageBox.warning(self, "无法添加", "请先填写要记住的词。")
            return
        try:
            add_memory_entry(self.workspace.mappings, self.memory_category.currentText(), value, mode)
        except ValueError as exc:
            QMessageBox.warning(self, "无法添加", str(exc))
            return
        self.memory_value.clear()
        if mode == "blacklist":
            self.set_status(f"已加入一定脱敏: {value}。以后再次出现会自动替换。")
        else:
            self.set_status(f"已加入一定不脱敏: {value}。以后再次出现会尽量保留。")

    def _finish_restore(self, result) -> None:
        if result.review_required:
            QMessageBox.warning(self, "需要人工复核", "AI 回复中存在缺失或无法识别的占位符，结果已放入“需要复核”。")
        self.set_status(f"已还原: {result.output_path.name}")


def run_app(root: Path) -> int:
    app = QApplication([])
    window = MainWindow(root)
    window.resize(960, 540)
    window.show()
    return app.exec()
