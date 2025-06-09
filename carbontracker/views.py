from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required

def home(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'carbontracker/home.html')

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'carbontracker/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'carbontracker/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')
from .models import Journey, Car, Route, Utility
from django import forms
from django.db.models import Q, Sum, F, FloatField, Value as V, IntegerField
from django.db.models.functions import Coalesce, Cast

def emission_ranking(request):
    # Aggregate emissions by start_state
    state_emissions = Route.objects.values('start_state').annotate(
        total_emission=Coalesce(
            Cast(Sum('journey__total_emission'), FloatField()), 
            V(0, output_field=FloatField())
        )
    ).order_by('-total_emission')

    # Aggregate emissions by start_city
    city_emissions = Route.objects.values('start_state', 'start_city').annotate(
        total_emission=Coalesce(
            Cast(Sum('journey__total_emission'), FloatField()), 
            V(0, output_field=FloatField())
        )
    ).order_by('-total_emission')

    # Aggregate emissions by start_area
    area_emissions = Route.objects.values('start_state', 'start_city', 'start_area').annotate(
        total_emission=Coalesce(
            Cast(Sum('journey__total_emission'), FloatField()), 
            V(0, output_field=FloatField())
        )
    ).order_by('-total_emission')

    context = {
        'state_emissions': state_emissions,
        'city_emissions': city_emissions,
        'area_emissions': area_emissions,
    }
    return render(request, 'carbontracker/emission_ranking.html', context)

class CarForm(forms.ModelForm):
    class Meta:
        model = Car
        fields = ['nickname', 'make', 'model', 'year', 'fuel_type', 'drive', 'transmission', 'v_class', 'disp', 'city_km_per_gallon', 'highway_km_per_gallon', 'icon_id']

class VehicleSearchForm(forms.Form):
    search_query = forms.CharField(label='Search Vehicles', required=False)

def home(request):
    return render(request, 'carbontracker/home.html')

import logging

logger = logging.getLogger(__name__)

def journey_list(request):
    journeys = Journey.objects.select_related('car').filter(car__isnull=False).exclude(car__nickname__exact='')
    logger.debug(f"Filtered journeys count: {journeys.count()}")
    return render(request, 'carbontracker/journey_list.html', {'journeys': journeys})

from django.forms import DateField
from django.forms.widgets import DateInput

class JourneyForm(forms.ModelForm):
    journey_date = DateField(
        input_formats=['%d-%m-%Y', '%Y-%m-%d'],
        widget=DateInput(format='%d-%m-%Y', attrs={'placeholder': 'dd-mm-yyyy'})
    )

    class Meta:
        model = Journey
        fields = ['route', 'car', 'journey_date', 'trans_mode', 'route_save', 'driving_conditions']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter cars to user vehicles only
        self.fields['car'].queryset = Car.objects.filter(is_user_vehicle=True)

def journey_add(request):
    from .models import Route
    if request.method == 'POST':
        form = JourneyForm(request.POST)
        start = request.POST.get('start')
        end = request.POST.get('end')
        city_distance = request.POST.get('city_distance')
        highway_distance = request.POST.get('highway_distance')
        if form.is_valid():
            journey = form.save(commit=False)
            # Create or update Route with distances and coordinates
            route = journey.route
            if not route and start and end:
                # Create new route if not selected and start/end provided
                try:
                    start_lat, start_lng = map(float, start.split(','))
                    end_lat, end_lng = map(float, end.split(','))
                    route_name = f"{start} to {end}"
                    route = Route.objects.create(
                        name=route_name,
                        city_distance=float(city_distance) if city_distance else 0,
                        highway_distance=float(highway_distance) if highway_distance else 0,
                        start_lat=start_lat,
                        start_lng=start_lng,
                        end_lat=end_lat,
                        end_lng=end_lng
                    )
                except (ValueError, TypeError):
                    route = None
            elif route:
                try:
                    route.city_distance = float(city_distance)
                    route.highway_distance = float(highway_distance)
                    if start:
                        lat_lng = start.split(',')
                        if len(lat_lng) == 2:
                            route.start_lat = float(lat_lng[0].strip())
                            route.start_lng = float(lat_lng[1].strip())
                    if end:
                        lat_lng = end.split(',')
                        if len(lat_lng) == 2:
                            route.end_lat = float(lat_lng[0].strip())
                            route.end_lng = float(lat_lng[1].strip())
                    route.save()
                except (ValueError, TypeError):
                    pass
            journey.route = route
            journey.save()
            # Instead of redirecting, re-render form with new route selected
            form = JourneyForm(instance=journey)
            return render(request, 'carbontracker/journey_add.html', {'form': form})
    else:
        form = JourneyForm()
    return render(request, 'carbontracker/journey_add.html', {'form': form})

def vehicle_list(request):
    vehicles = Car.objects.filter(is_user_vehicle=True)
    return render(request, 'carbontracker/vehicle_list.html', {'vehicles': vehicles})

def vehicle_add(request):
    search_form = VehicleSearchForm(request.GET or None)
    vehicles = Car.objects.filter(is_user_vehicle=False)
    if search_form.is_valid():
        query = search_form.cleaned_data.get('search_query')
        if query:
            vehicles = vehicles.filter(
                Q(make__icontains=query) |
                Q(model__icontains=query) |
                Q(year__icontains=query)
            )
    if request.method == 'POST':
        vehicle_id = request.POST.get('vehicle_id')
        nickname = request.POST.get('nickname')
        if vehicle_id:
            try:
                vehicle = Car.objects.get(id=vehicle_id, is_user_vehicle=False)
                vehicle.pk = None  # Create a new instance
                vehicle.nickname = nickname or f"{vehicle.make} {vehicle.model}"
                vehicle.is_user_vehicle = True
                vehicle.save()
                return redirect('vehicle_list')
            except Car.DoesNotExist:
                pass
    return render(request, 'carbontracker/vehicle_add.html', {
        'search_form': search_form,
        'vehicles': vehicles,
    })

class RouteForm(forms.ModelForm):
    class Meta:
        model = Route
        fields = ['name', 'city_distance', 'highway_distance']

def route_list(request):
    routes = Route.objects.all()
    return render(request, 'carbontracker/route_list.html', {'routes': routes})

def route_add(request):
    if request.method == 'POST':
        form = RouteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('route_list')
    else:
        form = RouteForm()
    return render(request, 'carbontracker/route_add.html', {'form': form})

from django import forms

class UtilityForm(forms.ModelForm):
    class Meta:
        model = Utility
        fields = ['bill_type', 'units', 'num_people', 'bill_start_date', 'bill_end_date']

def utility_list(request):
    utilities = Utility.objects.all()
    return render(request, 'carbontracker/utility_list.html', {'utilities': utilities})

def utility_add(request):
    if request.method == 'POST':
        form = UtilityForm(request.POST)
        if form.is_valid():
            utility = form.save()
            return redirect('utility_list')
    else:
        form = UtilityForm()
    return render(request, 'carbontracker/utility_add.html', {'form': form})

class FuelCalculatorForm(forms.Form):
    distance = forms.FloatField(label='Distance (km)', min_value=0)
    vehicle = forms.ModelChoiceField(queryset=Car.objects.all(), label='Vehicle')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['vehicle'].queryset = Car.objects.filter(is_user_vehicle=True)

def fuel_calculator(request):
    import datetime
    result = None
    if request.method == 'POST':
        form = FuelCalculatorForm(request.POST)
        if form.is_valid():
            distance = form.cleaned_data['distance']
            vehicle = form.cleaned_data['vehicle']
            current_year = datetime.datetime.now().year
            try:
                vehicle_year = int(vehicle.year)
            except:
                vehicle_year = current_year
            vehicle_age = current_year - vehicle_year
            degradation_factor = 1 + (0.01 * vehicle_age)
            city_distance = distance * 0.5
            highway_distance = distance * 0.5
            city_fuel_used = city_distance / vehicle.city_km_per_gallon if vehicle.city_km_per_gallon else 0
            highway_fuel_used = highway_distance / vehicle.highway_km_per_gallon if vehicle.highway_km_per_gallon else 0
            total_fuel_used = (city_fuel_used + highway_fuel_used) * degradation_factor
            result = {
                'total_fuel_used': total_fuel_used,
                'distance': distance,
                'vehicle': vehicle,
                'vehicle_age': vehicle_age,
                'degradation_factor': degradation_factor,
            }
    else:
        form = FuelCalculatorForm()
    return render(request, 'carbontracker/fuel_calculator.html', {'form': form, 'result': result})

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

def emission_fuel_charts(request):
    import datetime
    import json
    from collections import defaultdict
    current_year = datetime.datetime.now().year
    # Define degradation factor for driving conditions only (example values)
    driving_conditions_factors = {
        'normal': 0.0,
        'heavy_traffic': 0.05,
        'off_road': 0.1,
    }

    # Get cars used in journeys
    journey_cars = Car.objects.filter(journey__isnull=False).distinct()
    emission_by_make = defaultdict(float)
    fuel_by_make = defaultdict(float)
    count_by_make = defaultdict(int)
    for car in journey_cars:
        try:
            vehicle_year = int(car.year)
        except:
            vehicle_year = current_year
        vehicle_age = current_year - vehicle_year
        # Get driving conditions from journeys of this car
        journeys = car.journey_set.all()
        if journeys.exists():
            # Use the most common driving condition among journeys
            from collections import Counter
            driving_conditions_list = [j.driving_conditions for j in journeys]
            most_common_condition = Counter(driving_conditions_list).most_common(1)[0][0]
            driving_conditions_factor = driving_conditions_factors.get(most_common_condition, 0.0)
        else:
            driving_conditions_factor = 0.0
        degradation_factor = 1 + (0.01 * vehicle_age) + driving_conditions_factor
        avg_km_per_gallon = (car.city_km_per_gallon + car.highway_km_per_gallon) / 2 if car.city_km_per_gallon and car.highway_km_per_gallon else 0
        fuel_used_per_100km = 100 / avg_km_per_gallon if avg_km_per_gallon else 0
        fuel_used_per_100km *= degradation_factor
        emission_per_100km = fuel_used_per_100km * car.kg_per_gallon * degradation_factor
        make_label = car.make
        emission_by_make[make_label] += emission_per_100km
        fuel_by_make[make_label] += fuel_used_per_100km
        count_by_make[make_label] += 1

    # Aggregate utility emissions
    utilities = Utility.objects.all()
    total_utility_emission = 0.0
    total_utility_emission_per_person = 0.0
    utility_count = utilities.count()
    if utility_count > 0:
        total_utility_emission = sum(u.total_emission for u in utilities)
        total_utility_emission_per_person = sum(u.emission_per_person for u in utilities) / utility_count

    emission_data = []
    fuel_data = []
    for make in emission_by_make:
        avg_emission = emission_by_make[make] / count_by_make[make]
        avg_fuel = fuel_by_make[make] / count_by_make[make]
        emission_data.append({
            'label': make,
            'value': avg_emission,
        })
        fuel_data.append({
            'label': make,
            'value': avg_fuel,
        })

    # Add utility emissions as a separate entry
    emission_data.append({
        'label': 'Utilities (Total Emission)',
        'value': total_utility_emission,
    })
    emission_data.append({
        'label': 'Utilities (Emission per Person)',
        'value': total_utility_emission_per_person,
    })

    emission_data_json = json.dumps(emission_data)
    fuel_data_json = json.dumps(fuel_data)
    return render(request, 'carbontracker/emission_fuel_charts.html', {
        'emission_data': emission_data_json,
        'fuel_data': fuel_data_json,
    })

@csrf_exempt
def api_create_route(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('name')
            city_distance = float(data.get('city_distance', 0))
            highway_distance = float(data.get('highway_distance', 0))
            start_lat = float(data.get('start_lat'))
            start_lng = float(data.get('start_lng'))
            end_lat = float(data.get('end_lat'))
            end_lng = float(data.get('end_lng'))
            route = Route.objects.create(
                name=name,
                city_distance=city_distance,
                highway_distance=highway_distance,
                start_lat=start_lat,
                start_lng=start_lng,
                end_lat=end_lat,
                end_lng=end_lng
            )
            return JsonResponse({'success': True, 'route_id': route.id, 'route_name': route.name})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})
