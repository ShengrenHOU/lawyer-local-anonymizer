from legal_anonymizer.workspace import create_workspace, workspace_paths


def test_create_workspace_makes_all_required_folders(tmp_path):
    paths = create_workspace(tmp_path)

    assert paths.pending.exists()
    assert paths.anonymized.exists()
    assert paths.restore_pending.exists()
    assert paths.restored.exists()
    assert paths.mappings.exists()


def test_workspace_paths_are_inside_root(tmp_path):
    paths = workspace_paths(tmp_path)

    assert paths.pending.parent == tmp_path
    assert paths.mappings.name == "99-本地映射表-不要上传"

