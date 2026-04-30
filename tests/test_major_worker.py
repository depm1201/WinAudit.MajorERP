from unittest.mock import patch

from app.workers import major_worker


def test_configure_worker_logging_uses_project_log_level():
    with patch("app.workers.major_worker.setup_logging") as mock_setup_logging:
        major_worker.configure_worker_logging()

    mock_setup_logging.assert_called_once_with(service="worker", level=major_worker.settings.LOG_LEVEL)
