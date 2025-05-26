from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('journeys/', views.journey_list, name='journey_list'),
    path('journeys/add/', views.journey_add, name='journey_add'),
    path('vehicles/', views.vehicle_list, name='vehicle_list'),  
    path('vehicles/add/', views.vehicle_add, name='vehicle_add'),
    path('routes/', views.route_list, name='route_list'),
    path('utilities/', views.utility_list, name='utility_list'),
    path('utilities/add/', views.utility_add, name='utility_add'),
    path('route/add/', views.route_add, name='route_add'),
    path('fuel-calculator/', views.fuel_calculator, name='fuel_calculator'),
    path('emission-fuel-charts/', views.emission_fuel_charts, name='emission_fuel_charts'),
    path('journeys/add/', views.journey_add, name='journey_add'),
]
