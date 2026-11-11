"""Biometric device, punch intake, enrollment, and hardware integration models."""

from typing import ClassVar

from django.db import models

from apps.core.models import SoftDeleteMixin, TenantOwnedModel


class DeviceType(models.TextChoices):
    FINGERPRINT = "fingerprint", "Fingerprint (আঙুলের ছাপ)"
    FACE = "face", "Facial Recognition (মুখাবয়ব)"
    IRIS = "iris", "Iris Recognition (আইরিশ)"
    PALM = "palm", "Palm Vein (হাতের তালু)"
    RFID = "rfid", "RFID Card (স্মার্ট কার্ড)"
    NFC = "nfc", "NFC Badge (এনএফসি)"
    QR = "qr", "QR Code (কিউআর কোড)"
    PIN = "pin", "PIN / Password (পিন কোড)"
    MOBILE = "mobile", "Mobile App GPS (মোবাইল অ্যাপ)"


class DeviceProtocol(models.TextChoices):
    PUSH_ADMS = "push_adms", "Push (ZKTeco ADMS/iClock)"
    GENERIC_HTTP = "generic_http", "Generic HTTP Webhook (HMAC)"
    MQTT = "mqtt", "MQTT Broker"
    PULL_SDK = "pull_sdk", "Pull via SDK / Network Socket"
    SIMULATOR = "simulator", "Virtual Simulator"


class DeviceStatus(models.TextChoices):
    ONLINE = "online", "Online"
    OFFLINE = "offline", "Offline"
    MAINTENANCE = "maintenance", "Maintenance"


class CommandStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    SENT = "sent", "Sent to Device"
    ACKNOWLEDGED = "acknowledged", "Acknowledged"
    FAILED = "failed", "Failed"


class RawPunchStatus(models.TextChoices):
    UNPROCESSED = "unprocessed", "Unprocessed"
    PROCESSED = "processed", "Processed into Attendance"
    DUPLICATE = "duplicate", "Duplicate In Window"
    UNMAPPED = "unmapped", "Unmapped User (Review Queue)"


class Device(TenantOwnedModel, SoftDeleteMixin):
    """Master hardware device registry for biometric and attendance terminals."""

    name = models.CharField(
        max_length=100,
        help_text="Descriptive title, e.g. 'Main Gate Terminal 1' or 'Staff Room Face Scanner'",
    )
    device_type = models.CharField(
        max_length=30,
        choices=DeviceType.choices,
        default=DeviceType.FINGERPRINT,
    )
    vendor = models.CharField(
        max_length=50,
        default="ZKTeco",
        help_text="Hardware manufacturer, e.g. ZKTeco, Hikvision, Suprema, eSSL",
    )
    model = models.CharField(max_length=50, blank=True, help_text="Model name, e.g. SpeedFace-V5L")
    serial_no = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Unique hardware serial number (SN)",
    )
    protocol = models.CharField(
        max_length=30,
        choices=DeviceProtocol.choices,
        default=DeviceProtocol.PUSH_ADMS,
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    port = models.PositiveIntegerField(null=True, blank=True, default=80)
    auth_secret = models.CharField(
        max_length=255,
        blank=True,
        help_text="Shared HMAC secret or device encryption key",
    )
    api_token = models.CharField(
        max_length=128,
        db_index=True,
        blank=True,
        help_text="Secret authentication token for HTTP webhook or ADMS push ingestion",
    )
    branch = models.ForeignKey(
        "institutions.Branch",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="devices",
    )
    location = models.CharField(
        max_length=100,
        blank=True,
        help_text="Physical placement, e.g. Main Gate, Library, Staff Lounge",
    )
    timezone_offset_minutes = models.IntegerField(
        default=360,
        help_text="Timezone offset in minutes (+360 for Asia/Dhaka UTC+6)",
    )
    status = models.CharField(
        max_length=20,
        choices=DeviceStatus.choices,
        default=DeviceStatus.OFFLINE,
    )
    last_seen = models.DateTimeField(null=True, blank=True)
    firmware_version = models.CharField(max_length=50, blank=True)
    user_capacity = models.PositiveIntegerField(default=1000)
    punch_capacity = models.PositiveIntegerField(default=100000)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Device"
        verbose_name_plural = "Devices"
        ordering = ["name"]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["institution", "serial_no"],
                condition=models.Q(is_deleted=False),
                name="unique_active_device_serial_per_institution",
            )
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["serial_no", "institution"]),
            models.Index(fields=["api_token"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.vendor} - {self.serial_no})"


class DeviceGroup(TenantOwnedModel, SoftDeleteMixin):
    """Logical grouping of hardware terminals by audience or physical perimeter."""

    name = models.CharField(max_length=100, help_text="e.g. 'Main Gate - Students', 'Staff Room'")
    description = models.TextField(blank=True)
    target_audience = models.CharField(
        max_length=20,
        choices=[
            ("all", "All"),
            ("students", "Students"),
            ("staff", "Staff"),
            ("drivers", "Drivers"),
        ],
        default="all",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class DeviceGroupMember(TenantOwnedModel):
    """Membership of terminal in a device group."""

    group = models.ForeignKey(DeviceGroup, on_delete=models.CASCADE, related_name="members")
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="group_memberships")

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(fields=["group", "device"], name="unique_device_in_group")
        ]

    def __str__(self) -> str:
        return f"{self.device.name} in {self.group.name}"


class DeviceUserMap(TenantOwnedModel):
    """Binds device-side numerical identifiers to school students or staff."""

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="user_mappings")
    device_user_id = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Hardware user PIN/ID as registered on terminal, e.g. '1001'",
    )
    user_type = models.CharField(
        max_length=20,
        choices=[("student", "Student"), ("staff", "Staff")],
        default="student",
    )
    student = models.ForeignKey(
        "students.Student",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="device_mappings",
    )
    staff = models.ForeignKey(
        "staff.Staff",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="device_mappings",
    )
    rfid_card = models.CharField(max_length=50, blank=True)

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["device", "device_user_id"],
                name="unique_device_user_id_per_device",
            )
        ]

    def __str__(self) -> str:
        target = (
            self.student.name_en
            if self.student
            else (self.staff.full_name_en if self.staff else "Unassigned")
        )
        return f"Device {self.device.name}: PIN {self.device_user_id} -> {target}"


class BiometricConsent(TenantOwnedModel, SoftDeleteMixin):
    """Guardian and employee consent tracking for biometric enrollment."""

    subject_type = models.CharField(
        max_length=20,
        choices=[("student", "Student"), ("staff", "Staff")],
        default="student",
    )
    student = models.ForeignKey(
        "students.Student",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="biometric_consents",
    )
    staff = models.ForeignKey(
        "staff.Staff",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="biometric_consents",
    )
    guardian = models.ForeignKey(
        "guardians.Guardian",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="given_biometric_consents",
        help_text="Mandatory for minor students",
    )
    consent_version = models.CharField(max_length=20, default="v1.0")
    granted_at = models.DateTimeField(auto_now_add=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    @property
    def is_active(self) -> bool:
        return self.withdrawn_at is None

    def __str__(self) -> str:
        target = (
            self.student.name_en
            if self.student
            else (self.staff.full_name_en if self.staff else "Unknown")
        )
        status = "Active" if self.is_active else "Withdrawn"
        return f"Consent ({status}) for {target} [{self.consent_version}]"


class BiometricEnrollment(TenantOwnedModel, SoftDeleteMixin):
    """Metadata tracking user enrollment on terminals. HARD RULE: No raw templates stored."""

    subject_type = models.CharField(
        max_length=20,
        choices=[("student", "Student"), ("staff", "Staff")],
        default="student",
    )
    student = models.ForeignKey(
        "students.Student",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="biometric_enrollments",
    )
    staff = models.ForeignKey(
        "staff.Staff",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="biometric_enrollments",
    )
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="enrollments")
    method = models.CharField(max_length=30, choices=DeviceType.choices)
    device_user_id = models.CharField(max_length=50)
    consent = models.ForeignKey(
        BiometricConsent,
        on_delete=models.PROTECT,
        related_name="enrollments",
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        target = (
            self.student.name_en
            if self.student
            else (self.staff.full_name_en if self.staff else "Unknown")
        )
        return f"{self.method} on {self.device.name} for {target}"


class DeviceCommand(TenantOwnedModel):
    """Asynchronous command queue for hardware orchestration."""

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="commands")
    command_type = models.CharField(
        max_length=50,
        choices=[
            ("enroll_user", "Enroll User"),
            ("delete_user", "Delete User"),
            ("sync_time", "Sync Time"),
            ("reboot", "Reboot Device"),
            ("clear_log", "Clear Log"),
        ],
    )
    payload = models.TextField(blank=True, help_text="Formatted device instruction or JSON")
    status = models.CharField(
        max_length=20,
        choices=CommandStatus.choices,
        default=CommandStatus.QUEUED,
        db_index=True,
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    response_message = models.TextField(blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.command_type} on {self.device.name} ({self.status})"


class DeviceHealthLog(TenantOwnedModel):
    """Periodic diagnostics and connectivity telemetry."""

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="health_logs")
    device_time = models.DateTimeField()
    server_time = models.DateTimeField(auto_now_add=True)
    clock_drift_seconds = models.IntegerField(default=0)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_count = models.PositiveIntegerField(default=0)
    punch_count = models.PositiveIntegerField(default=0)
    status_ok = models.BooleanField(default=True)
    raw_data = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return (
            f"{self.device.name} Health @ {self.server_time} (Drift: {self.clock_drift_seconds}s)"
        )


class RawPunch(TenantOwnedModel):
    """Immutable, append-only raw punch log received from attendance hardware."""

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="raw_punches")
    serial_no = models.CharField(max_length=100, db_index=True)
    raw_user_id = models.CharField(max_length=50, db_index=True)
    device_time = models.DateTimeField(db_index=True)
    received_at = models.DateTimeField(auto_now_add=True, db_index=True)
    clock_drift_seconds = models.IntegerField(default=0)
    verify_type = models.CharField(
        max_length=30,
        choices=DeviceType.choices,
        default=DeviceType.FINGERPRINT,
    )
    punch_state = models.CharField(max_length=20, default="0", help_text="0=In, 1=Out, etc.")
    work_code = models.CharField(max_length=20, blank=True)
    payload_hash = models.CharField(max_length=64, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=RawPunchStatus.choices,
        default=RawPunchStatus.UNPROCESSED,
        db_index=True,
    )
    resolved_student = models.ForeignKey(
        "students.Student",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="raw_punches",
    )
    resolved_staff = models.ForeignKey(
        "staff.Staff",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="raw_punches",
    )
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-device_time"]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["device", "raw_user_id", "device_time"],
                name="unique_raw_punch_device_user_time",
            )
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["device", "received_at"]),
            models.Index(fields=["status", "institution"]),
        ]

    def __str__(self) -> str:
        return f"Punch PIN {self.raw_user_id} @ {self.device_time} on {self.device.name} ({self.status})"
