from django.urls import path

from apps.corporate.views import CorporateInquiryView

app_name = "corporate"

urlpatterns = [
    path("", CorporateInquiryView.as_view(), name="inquiry"),
]

