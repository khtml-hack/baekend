import json
import os
from django.core.management.base import BaseCommand, CommandError
from trips.models import CongestionIndex


class Command(BaseCommand):
    help = 'Import congestion data from JSON file into CongestionIndex model'

    def add_arguments(self, parser):
        parser.add_argument(
            'json_file',
            type=str,
            help='Path to JSON file containing congestion data'
        )
        parser.add_argument(
            '--region',
            type=str,
            default=None,
            help='Region code (default: None)'
        )
        parser.add_argument(
            '--version',
            type=str,
            default='v1',
            help='Data version (default: v1)'
        )

    def handle(self, *args, **options):
        json_file_path = options['json_file']
        region_code = options['region']
        version = options['version']

        # Check if file exists
        if not os.path.exists(json_file_path):
            raise CommandError(f'JSON file does not exist: {json_file_path}')

        # Load JSON data
        try:
            with open(json_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
        except json.JSONDecodeError as e:
            raise CommandError(f'Invalid JSON format: {e}')
        except Exception as e:
            raise CommandError(f'Error reading file: {e}')

        created_count = 0
        updated_count = 0

        # Process each month's data
        for month, congestion_values in data.items():
            # Validate required fields
            required_fields = ['T0', 'T1', 'T2', 'T3']
            missing_fields = [field for field in required_fields if field not in congestion_values]
            
            if missing_fields:
                self.stdout.write(
                    self.style.WARNING(
                        f'Skipping {month}: missing fields {missing_fields}'
                    )
                )
                continue

            # Update or create congestion index
            congestion_index, created = CongestionIndex.objects.update_or_create(
                month=month,
                region_code=region_code,
                version=version,
                defaults={
                    'T0': congestion_values['T0'],
                    'T1': congestion_values['T1'],
                    'T2': congestion_values['T2'],
                    'T3': congestion_values['T3'],
                }
            )

            if created:
                created_count += 1
                self.stdout.write(
                    f'Created: {month} - T0:{congestion_values["T0"]}, T1:{congestion_values["T1"]}, T2:{congestion_values["T2"]}, T3:{congestion_values["T3"]}'
                )
            else:
                updated_count += 1
                self.stdout.write(
                    f'Updated: {month} - T0:{congestion_values["T0"]}, T1:{congestion_values["T1"]}, T2:{congestion_values["T2"]}, T3:{congestion_values["T3"]}'
                )

        # Print summary
        self.stdout.write(
            self.style.SUCCESS(
                f'Import completed! Created: {created_count}, Updated: {updated_count}'
            )
        )
