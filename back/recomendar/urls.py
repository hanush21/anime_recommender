from django.contrib import admin
from django.urls import path
from .views import getrecomenders, recommend_by_seen, healthz, recommender_status


urlpatterns = [
    path("admin/", admin.site.urls),
    path("getrecomenders", getrecomenders),
    path("recommend_by_seen", recommend_by_seen),
    path("healthz", healthz),
    path("recommender/status", recommender_status),
]