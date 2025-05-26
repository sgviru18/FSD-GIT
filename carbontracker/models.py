from django.db import models

class VehicleSpec(models.Model):
    city = models.FloatField()
    highway = models.FloatField()
    # Add other fields as needed

    def __str__(self):
        return f"City: {self.city}, Highway: {self.highway}"

class Car(models.Model):
    nickname = models.CharField(max_length=100)
    make = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.CharField(max_length=4)
    fuel_type = models.CharField(max_length=50)
    drive = models.CharField(max_length=50)
    transmission = models.CharField(max_length=50)
    v_class = models.CharField(max_length=50)
    disp = models.CharField(max_length=50)
    city_km_per_gallon = models.FloatField()
    highway_km_per_gallon = models.FloatField()
    kg_per_gallon = models.FloatField()
    icon_id = models.IntegerField(null=True, blank=True)
    car_spec = models.ForeignKey(VehicleSpec, on_delete=models.SET_NULL, null=True, blank=True)
    is_user_vehicle = models.BooleanField(default=False)

    def calculate_kg_per_gallon(self):
        if self.fuel_type == "Electricity fuel":
            self.kg_per_gallon = 0.0
        elif self.fuel_type == "Diesel fuel":
            self.kg_per_gallon = 10.16
        else:
            self.kg_per_gallon = 8.89

    def save(self, *args, **kwargs):
        self.calculate_kg_per_gallon()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nickname} ({self.make} {self.model} {self.year})"

class Route(models.Model):
    name = models.CharField(max_length=200)
    city_distance = models.FloatField()
    highway_distance = models.FloatField()
    total_distance = models.FloatField()
    start_lat = models.FloatField(null=True, blank=True)
    start_lng = models.FloatField(null=True, blank=True)
    end_lat = models.FloatField(null=True, blank=True)
    end_lng = models.FloatField(null=True, blank=True)

    def save(self, *args, **kwargs):
        self.total_distance = self.city_distance + self.highway_distance
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.total_distance} km"

class Journey(models.Model):
    TRANSPORT_MODES = [
        ('car', 'Car'),
    ]

    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    car = models.ForeignKey(Car, on_delete=models.CASCADE, null=True, blank=True)
    total_emission = models.FloatField()
    journey_date = models.DateField()
    trans_mode = models.CharField(max_length=20, choices=TRANSPORT_MODES, default='car')
    route_save = models.BooleanField(default=False)

    def calculate_total_emission(self):
        if self.car:
            # Convert distances from km to miles for calculation consistency
            city_miles = self.route.city_distance / 1.609
            highway_miles = self.route.highway_distance / 1.609
            total_fuel_usage = (city_miles / self.car.city_km_per_gallon) + (highway_miles / self.car.highway_km_per_gallon)
            self.total_emission = total_fuel_usage * self.car.kg_per_gallon
        else:
            self.total_emission = 0.0

    def save(self, *args, **kwargs):
        self.calculate_total_emission()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Journey on {self.journey_date} by {self.trans_mode}"

class Utility(models.Model):
    bill_type = models.CharField(max_length=50)
    bill_amount = models.FloatField()
    total_emission = models.FloatField()
    num_people = models.IntegerField()
    emission_per_person = models.FloatField()
    bill_start_date = models.DateField()
    bill_end_date = models.DateField()
    days = models.IntegerField()

    def determine_unit(self):
        if self.bill_type == "Electricity":
            return 0.009
        else:
            return 56.1

    def calculate_emissions(self):
        emission_unit = self.determine_unit()
        self.total_emission = self.bill_amount * emission_unit
        self.emission_per_person = (self.total_emission / self.num_people) / self.days

    def save(self, *args, **kwargs):
        self.calculate_emissions()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.bill_type} bill from {self.bill_start_date} to {self.bill_end_date}"
