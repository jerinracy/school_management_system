---
name: django-backend
description: Use for any Django/DRF work: models, services, serializers, viewsets, permissions, Celery tasks, admin, settings. Enforces tenant scoping, service-layer architecture, and performance hygiene.
---

# django-backend

### Patterns
**Model base**
```python
class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta: abstract = True

class TenantOwnedModel(BaseModel):
    institution = models.ForeignKey("institutions.Institution", on_delete=models.PROTECT, related_name="+")
    class Meta: abstract = True
```
**Viewset mixin:** `TenantScopedMixin.get_queryset()` filters by `request.user.institution`; `perform_create` injects institution.

**Service layer:** `services.admit_student(*, application, section, actor) -> Student` — keyword-only args, wrapped in `transaction.atomic`, raises domain exceptions mapped to API errors.

**Selectors:** read-only query functions returning optimized querysets.

### Rules
- `on_delete=PROTECT` for financial/academic history; soft delete for students/staff.
- Unique constraints scoped by tenant: `UniqueConstraint(fields=["institution","roll_no","section","session"])`.
- Use `Meta.indexes` for filter/sort fields; add `CheckConstraint` for invariants (e.g. `paid_amount <= payable_amount`).
- Use `TextChoices` for enums; store Bangla labels via translations, not DB values.
- Serializers: separate read/write serializers when shapes differ; never expose internal IDs/fields unintentionally.
- Use `django-filter`, `SearchFilter`, `OrderingFilter`; cap `page_size`.
- Celery: `acks_late`, `autoretry_for`, exponential backoff, idempotent tasks.
- Settings split; secrets via `django-environ`; `DEBUG=False` in prod; secure cookies/HSTS.
- Admin: register useful models with `list_display`, `search_fields`, `list_filter` (internal tooling only).
- Bangla PDF: WeasyPrint/ReportLab with Noto Sans Bengali embedded; test render.
- Document every endpoint with `@extend_schema`.

### Definition of done (backend task)
Models + migrations + services + serializers + viewsets + permissions + urls + admin + tasks + tests + OpenAPI + docs.

---
