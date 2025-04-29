from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("ayuda", views.ayuda, name="ayuda"),
    path("cargarXml", views.cargarXml, name="cargarXml"),
    path("peticiones", views.peticiones, name="peticiones"),
]