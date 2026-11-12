from django.contrib import admin

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
)

admin.site.register(NoticeReadReceipt)
admin.site.register(Event)
admin.site.register(EventRSVP)
admin.site.register(Club)
admin.site.register(ClubMembership)
admin.site.register(Competition)
admin.site.register(CompetitionResult)
admin.site.register(Achievement)
admin.site.register(Certificate)
admin.site.register(Album)
admin.site.register(GalleryMedia)
