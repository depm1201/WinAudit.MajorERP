from types import SimpleNamespace
from unittest.mock import patch

from app.storage.major_storage_manager import MajorStorageManager


def test_major_storage_manager_creates_expected_tree(tmp_path):
    storage_settings = SimpleNamespace(storage_path=tmp_path)

    with patch("app.storage.major_storage_manager.settings", storage_settings):
        target = MajorStorageManager().ensure_paths("FINANZBURO", "0999999999001", "2026-04")

    assert target == tmp_path / "FINANZBURO" / "clients" / "file" / "0999999999001" / "MAJOR_ERP" / "2026-04"
    assert (target / "raw").is_dir()
    assert (target / "loaded").is_dir()
    assert (target / "rejected").is_dir()
    assert (target / "exports").is_dir()


def test_major_storage_manager_build_export_path_returns_exports_dir(tmp_path):
    storage_settings = SimpleNamespace(storage_path=tmp_path)

    with patch("app.storage.major_storage_manager.settings", storage_settings):
        export_path = MajorStorageManager().build_export_path("EXFIS", "0999999999001", "2026-04")

    assert export_path == tmp_path / "EXFIS" / "clients" / "file" / "0999999999001" / "MAJOR_ERP" / "2026-04" / "exports"
    assert export_path.is_dir()
