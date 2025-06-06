from django.core.management.base import BaseCommand
from carbontracker.models import Route

class Command(BaseCommand):
    help = 'Backfill start and end location fields for existing Route records using reverse geocoding'

    def handle(self, *args, **options):
        routes = Route.objects.all()
        total = routes.count()
        self.stdout.write(f"Backfilling location fields for {total} routes...")
        updated_count = 0
        for route in routes:
            updated = False
            if route.start_lat and route.start_lng and (not route.start_state or not route.start_city or not route.start_area):
                state, city, area = route.reverse_geocode(route.start_lat, route.start_lng)
                route.start_state = state
                route.start_city = city
                route.start_area = area
                updated = True
            if route.end_lat and route.end_lng and (not route.end_state or not route.end_city or not route.end_area):
                state, city, area = route.reverse_geocode(route.end_lat, route.end_lng)
                route.end_state = state
                route.end_city = city
                route.end_area = area
                updated = True
            if updated:
                route.save()
                updated_count += 1
                self.stdout.write(f"Updated route {route.id}: {route.name}")
        self.stdout.write(f"Backfill complete. Updated {updated_count} routes.")
