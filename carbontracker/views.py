from django.shortcuts import render, redirect
from .models import Journey, Car, Route, Utility
from django import forms
from django.db.models import Q

class CarForm(forms.ModelForm):
    class Meta:
        model = Car
        fields = ['nickname', 'make', 'model', 'year', 'fuel_type', 'drive', 'transmission', 'v_class', 'disp', 'city_km_per_gallon', 'highway_km_per_gallon', 'icon_id']

class VehicleSearchForm(forms.Form):
    search_query = forms.CharField(label='Search Vehicles', required=False)

def home(request):
    return render(request, 'carbontracker/home.html')

def journey_list(request):
    journeys = Journey.objects.all()
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
        fields = ['route', 'car', 'journey_date', 'trans_mode', 'route_save']

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
            if route:
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
            return redirect('journey_list')
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

def utility_list(request):
    utilities = Utility.objects.all()
    return render(request, 'carbontracker/utility_list.html', {'utilities': utilities})

def utility_add(request):
    # Placeholder for adding utility logic
    return render(request, 'carbontracker/utility_add.html')

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

def emission_fuel_charts(request):
    import datetime
    import json
    current_year = datetime.datetime.now().year
    # Get cars used in journeys
    journey_cars = Car.objects.filter(journey__isnull=False).distinct()
    emission_data = []
    fuel_data = []
    for car in journey_cars:
        try:
            vehicle_year = int(car.year)
        except:
            vehicle_year = current_year
        vehicle_age = current_year - vehicle_year
        degradation_factor = 1 + (0.01 * vehicle_age)
        avg_km_per_gallon = (car.city_km_per_gallon + car.highway_km_per_gallon) / 2 if car.city_km_per_gallon and car.highway_km_per_gallon else 0
        fuel_used_per_100km = 100 / avg_km_per_gallon if avg_km_per_gallon else 0
        fuel_used_per_100km *= degradation_factor
        emission_per_100km = fuel_used_per_100km * car.kg_per_gallon * degradation_factor
        emission_data.append({
            'label': f"{car.make} {car.model} ({car.year})",
            'value': emission_per_100km,
        })
        fuel_data.append({
            'label': f"{car.make} {car.model} ({car.year})",
            'value': fuel_used_per_100km,
        })
    emission_data_json = json.dumps(emission_data)
    fuel_data_json = json.dumps(fuel_data)
    return render(request, 'carbontracker/emission_fuel_charts.html', {
        'emission_data': emission_data_json,
        'fuel_data': fuel_data_json,
    })
