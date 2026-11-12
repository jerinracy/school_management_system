"""DRF serializers for Events, Clubs, Competitions, Achievements, Certificates & Gallery."""

from rest_framework import serializers

from apps.events.models import (
    Achievement,
    Album,
    Certificate,
    Club,
    ClubMembership,
    Competition,
    CompetitionResult,
    Event,
    EventRSVP,
    GalleryMedia,
    NoticeReadReceipt,
    RSVPStatus,
)


class NoticeReadReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = NoticeReadReceipt
        fields = [
            "id",
            "institution",
            "notice",
            "user",
            "read_at",
        ]
        read_only_fields = ["id", "institution", "user", "read_at"]


class MarkNoticeReadSerializer(serializers.Serializer):
    notice = serializers.UUIDField()


class UnifiedCalendarItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    source_type = serializers.ChoiceField(choices=["event", "holiday", "notice"])
    category = serializers.CharField()
    title_en = serializers.CharField()
    title_bn = serializers.CharField(allow_blank=True)
    description = serializers.CharField(allow_blank=True)
    start = serializers.CharField()
    end = serializers.CharField(allow_null=True)
    is_all_day = serializers.BooleanField()
    venue = serializers.CharField(allow_blank=True)
    is_pinned = serializers.BooleanField()


class ClubSerializer(serializers.ModelSerializer):
    class Meta:
        model = Club
        fields = [
            "id",
            "institution",
            "name_en",
            "name_bn",
            "category",
            "description",
            "advisor",
            "meeting_schedule",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]


class ClubMembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubMembership
        fields = [
            "id",
            "institution",
            "club",
            "student",
            "role",
            "joined_date",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = [
            "id",
            "institution",
            "title_en",
            "title_bn",
            "description_en",
            "description_bn",
            "category",
            "start_datetime",
            "end_datetime",
            "is_all_day",
            "venue",
            "target_audience",
            "target_class_level",
            "target_section",
            "club",
            "organizer",
            "is_published",
            "requires_rsvp",
            "max_participants",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]


class EventRSVPSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventRSVP
        fields = [
            "id",
            "institution",
            "event",
            "user",
            "student",
            "status",
            "note",
            "responded_at",
        ]
        read_only_fields = ["id", "institution", "user", "responded_at"]


class EventRSVPActionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=RSVPStatus.choices, default=RSVPStatus.GOING)
    student = serializers.UUIDField(required=False, allow_null=True)
    note = serializers.CharField(required=False, allow_blank=True, default="")


class CompetitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Competition
        fields = [
            "id",
            "institution",
            "title_en",
            "title_bn",
            "event",
            "club",
            "competition_date",
            "level",
            "category",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]


class CompetitionResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompetitionResult
        fields = [
            "id",
            "institution",
            "competition",
            "student",
            "position",
            "score_or_remark",
            "awarded_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "awarded_at", "created_at", "updated_at"]


class AchievementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Achievement
        fields = [
            "id",
            "institution",
            "student",
            "title_en",
            "title_bn",
            "category",
            "achieved_date",
            "competition_result",
            "description",
            "is_verified",
            "verified_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "verified_by", "created_at", "updated_at"]


class CertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certificate
        fields = [
            "id",
            "institution",
            "student",
            "achievement",
            "competition_result",
            "certificate_number",
            "title_en",
            "title_bn",
            "issued_date",
            "template_code",
            "signatory_name",
            "signatory_title",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]


class AlbumSerializer(serializers.ModelSerializer):
    class Meta:
        model = Album
        fields = [
            "id",
            "institution",
            "title_en",
            "title_bn",
            "description",
            "event",
            "album_date",
            "is_published",
            "is_public_to_guardians",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]


class GalleryMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = GalleryMedia
        fields = [
            "id",
            "institution",
            "album",
            "media_type",
            "file",
            "caption_en",
            "caption_bn",
            "display_order",
            "contains_students",
            "guardian_consent_verified",
            "is_approved",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]
