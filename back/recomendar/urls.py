from django.contrib import admin
from django.urls import path
from recomendar.views import getrecomenders, recommend_by_seen, healthz


urlpatterns = [
    path("admin/", admin.site.urls),
    path("getrecomenders", getrecomenders, name="getrecomenders"),
    path("recommend_by_seen", recommend_by_seen, name="recommend_by_seen"),
    path("healthz", healthz, name="healthz")
]