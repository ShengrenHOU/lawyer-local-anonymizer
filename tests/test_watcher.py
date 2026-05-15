from pathlib import Path

from legal_anonymizer.watcher import LegalAnonymizerHandler
from legal_anonymizer.workspace import create_workspace


def test_manual_rescan_force_reprocesses_existing_pending_file(tmp_path):
    workspace = create_workspace(tmp_path)
    source = workspace.pending / "memo.docx"
    source.write_bytes(b"not a real docx")
    messages: list[str] = []
    handler = LegalAnonymizerHandler(workspace, messages.append)
    calls: list[tuple[Path, bool]] = []

    def fake_handle(path: Path, force: bool = False) -> None:
        calls.append((path, force))

    handler.handle_path = fake_handle  # type: ignore[method-assign]

    handler.scan_existing(force=True)

    assert calls == [(source, True)]
