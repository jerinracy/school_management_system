"""Unit tests for core background tasks."""

from apps.core.tasks import health_check_task


class TestCoreTasks:
    def test_health_check_task_execution(self) -> None:
        result = health_check_task()
        assert result["status"] == "ok"
        assert result["task_name"] == "apps.core.tasks.health_check_task"
        assert "executed_at" in result
