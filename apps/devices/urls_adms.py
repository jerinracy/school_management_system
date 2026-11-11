"""Direct root-level URLs for ZKTeco ADMS terminal firmware."""

from django.urls import path

from apps.devices.views import (
    ZKTecoCdataView,
    ZKTecoDeviceCmdView,
    ZKTecoGetRequestView,
)

urlpatterns = [
    path("cdata", ZKTecoCdataView.as_view(), name="root_iclock_cdata"),
    path("getrequest", ZKTecoGetRequestView.as_view(), name="root_iclock_getrequest"),
    path("devicecmd", ZKTecoDeviceCmdView.as_view(), name="root_iclock_devicecmd"),
]
