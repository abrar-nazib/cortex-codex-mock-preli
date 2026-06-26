from django.urls import path

from . import views

urlpatterns = [
    path("health", views.HealthView.as_view(), name="health"),
    path("sort-ticket", views.SortTicketView.as_view(), name="sort-ticket"),
]