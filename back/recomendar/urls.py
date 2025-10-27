from django.urls import path
from .views import healthz, getrecomenders, recommend_by_seen, suggest_titles

urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("getrecomenders", getrecomenders, name="getrecomenders"),
    path("recommend_by_seen", recommend_by_seen, name="recommend_by_seen"),
    path("titles", suggest_titles, name="titles"),
]
