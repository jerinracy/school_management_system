"""Management command to create timestamped DB backups and prune expired archives."""

import sqlite3
import subprocess
from datetime import timedelta
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


class Command(BaseCommand):
    help = "Create a timestamped database backup and prune backups older than retention days."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--backup-dir",
            type=str,
            default="",
            help="Override BACKUP_DIR setting.",
        )
        parser.add_argument(
            "--retention-days",
            type=int,
            default=int(getattr(settings, "BACKUP_RETENTION_DAYS", 30)),
            help="Delete backups older than N days.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        raw_dir = options["backup_dir"] or str(
            getattr(settings, "BACKUP_DIR", Path(settings.BASE_DIR) / "backups")
        )
        backup_dir = Path(raw_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)

        db_cfg = settings.DATABASES["default"]
        engine = db_cfg["ENGINE"]
        stamp = timezone.now().strftime("%Y%m%d_%H%M%S")

        if "sqlite3" in engine:
            db_name = str(db_cfg["NAME"])
            target = backup_dir / f"db_backup_{stamp}.sqlite3"
            if db_name == ":memory:":
                target.write_bytes(b"")
            else:
                src_conn = sqlite3.connect(db_name)
                dst_conn = sqlite3.connect(str(target))
                try:
                    src_conn.backup(dst_conn)
                finally:
                    dst_conn.close()
                    src_conn.close()
        elif "postgresql" in engine:
            target = backup_dir / f"db_backup_{stamp}.dump"
            cmd = [
                "pg_dump",
                "-Fc",
                "-h",
                str(db_cfg.get("HOST") or "localhost"),
                "-p",
                str(db_cfg.get("PORT") or "5432"),
                "-U",
                str(db_cfg.get("USER") or "postgres"),
                "-f",
                str(target),
                str(db_cfg["NAME"]),
            ]
            result = subprocess.run(cmd, check=False, capture_output=True, text=True)
            if result.returncode != 0:
                raise CommandError(f"pg_dump failed: {result.stderr}")
        else:
            raise CommandError(f"Unsupported database engine for backup: {engine}")

        cutoff = (
            timezone.now().timestamp() - timedelta(days=options["retention_days"]).total_seconds()
        )
        pruned = 0
        for item in backup_dir.glob("db_backup_*"):
            if item.is_file() and item != target and item.stat().st_mtime < cutoff:
                item.unlink()
                pruned += 1

        self.stdout.write(
            self.style.SUCCESS(f"Backup created: {target} (pruned {pruned} old backup(s))")
        )
