from django.contrib import admin
from django.urls import path
from recomendar.views import (
    healthz, recommender_status, list_titles,
    getrecomenders, recommend_by_seen
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz", healthz),
    path("recommender/status", recommender_status),
    path("anime/titles", list_titles),
    path("getrecomenders", getrecomenders),
    path("recommend_by_seen", recommend_by_seen),
]
