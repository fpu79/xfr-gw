from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("", views.transfer_list, name="transfer-list"),
    path("downloads/<int:transfer_id>/", views.download, name="download"),
]
