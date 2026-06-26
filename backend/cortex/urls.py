"""Project URL routing.

  GET  /health        — service health
  POST /sort-ticket   — classify one ticket
  GET  /docs/          — drf_spectacular swagger UI
  GET  /api/schema/    — OpenAPI schema
"""
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("", include("tickets.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url="/api/schema/"), name="swagger-ui"),
]