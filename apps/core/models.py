"""Core abstract models, managers, and mixins."""

import uuid
from typing import Any

from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet supporting soft delete operations."""

    def delete(self) -> tuple[int, dict[str, int]]:
        """Soft delete all records in this queryset."""
        count = self.update(is_deleted=True, deleted_at=timezone.now())
        return count, {self.model._meta.label: count}

    def hard_delete(self) -> tuple[int, dict[str, int]]:
        """Permanently delete records from the database."""
        return super().delete()

    def alive(self) -> "SoftDeleteQuerySet":
        """Filter for non-deleted records."""
        return self.filter(is_deleted=False)

    def dead(self) -> "SoftDeleteQuerySet":
        """Filter for soft-deleted records."""
        return self.filter(is_deleted=True)


class SoftDeleteManager(models.Manager):
    """Manager that excludes soft-deleted records by default."""

    def get_queryset(self) -> SoftDeleteQuerySet:
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)


class AllObjectsManager(models.Manager):
    """Manager providing access to all objects, including soft-deleted ones."""

    def get_queryset(self) -> SoftDeleteQuerySet:
        return SoftDeleteQuerySet(self.model, using=self._db)


class SoftDeleteMixin(models.Model):
    """Mixin adding soft delete functionality to a model."""

    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def delete(self, using: Any = None, keep_parents: bool = False) -> tuple[int, dict[str, int]]:
        """Soft delete the instance."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])
        return 1, {self._meta.label: 1}

    def hard_delete(
        self, using: Any = None, keep_parents: bool = False
    ) -> tuple[int, dict[str, int]]:
        """Permanently delete the instance from the database."""
        return super().delete(using=using, keep_parents=keep_parents)

    def restore(self) -> None:
        """Restore a soft-deleted instance."""
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at"])


class BaseModel(models.Model):
    """Abstract base model with UUID primary key and timestamp audit fields."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class TenantOwnedModel(BaseModel):
    """Abstract base model for all tenant-scoped data.

    Enforces mandatory institution scoping. Uses a string reference to
    'institutions.Institution' so apps.core remains independent of concrete apps.
    """

    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.PROTECT,
        related_name="+",
        db_index=True,
    )

    class Meta:
        abstract = True
