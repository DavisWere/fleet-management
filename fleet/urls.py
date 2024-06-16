from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from fleet.views import (CustomObtainTokenPairView, UserViewSet, ServiceTypeViewSet, CurrentUserViewSet,
                         SubServiceViewSet, VehiclePartViewSet, VehicleServiceViewSet, VehicleViewSet, GeneratePDF)

fleet_router = DefaultRouter()
fleet_router.register(r"user", UserViewSet)
fleet_router.register(r"service-type", ServiceTypeViewSet)
fleet_router.register(r"sub-service", SubServiceViewSet)
fleet_router.register(r"vehicle-part", VehiclePartViewSet)
fleet_router.register(r"vehicle-service", VehicleServiceViewSet)
fleet_router.register(r"vehicle", VehicleViewSet)
fleet_router.register(r"current-user", CurrentUserViewSet,
                      basename='current_user')

url_patterns = fleet_router.urls
url_patterns += [
    path("token/request/", CustomObtainTokenPairView.as_view(), name="token_request"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path('pdf-report/', GeneratePDF.as_view(), name='generate_pdf')

]
