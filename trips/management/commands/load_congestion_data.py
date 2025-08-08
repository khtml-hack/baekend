import json
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from trips.models import CongestionIndex


class Command(BaseCommand):
    help = '혼잡도 데이터를 JSON 파일에서 데이터베이스로 로드합니다.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help='JSON 파일 경로 (기본값: trips/fixtures/congestion_data.json)',
        )
        parser.add_argument(
            '--region',
            type=str,
            default=None,
            help='지역 코드 (기본값: None)',
        )
        parser.add_argument(
            '--data-version',
            type=str,
            default='v1',
            help='데이터 버전 (기본값: v1)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='기존 데이터를 삭제하고 새로 로드',
        )

    def handle(self, *args, **options):
        # JSON 파일 경로 설정
        if options['file']:
            json_file_path = options['file']
        else:
            json_file_path = os.path.join(
                settings.BASE_DIR, 
                'trips', 
                'fixtures', 
                'congestion_data.json'
            )

        # 파일 존재 확인
        if not os.path.exists(json_file_path):
            self.stdout.write(
                self.style.ERROR(f'JSON 파일을 찾을 수 없습니다: {json_file_path}')
            )
            return

        # 기존 데이터 삭제 (--clear 옵션)
        if options['clear']:
            deleted_count = CongestionIndex.objects.filter(
                region_code=options['region'],
                version=options['data_version']
            ).count()
            CongestionIndex.objects.filter(
                region_code=options['region'],
                version=options['data_version']
            ).delete()
            self.stdout.write(
                self.style.SUCCESS(f'기존 데이터 {deleted_count}개를 삭제했습니다.')
            )

        # JSON 파일 로드
        try:
            with open(json_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'JSON 파일 로드 실패: {e}')
            )
            return

        # 데이터 저장
        created_count = 0
        updated_count = 0

        for month, congestion_values in data.items():
            # 기존 데이터 확인
            congestion_index, created = CongestionIndex.objects.update_or_create(
                month=month,
                region_code=options['region'],
                version=options['data_version'],
                defaults={
                    'T0': congestion_values['T0'],
                    'T1': congestion_values['T1'],
                    'T2': congestion_values['T2'],
                    'T3': congestion_values['T3'],
                }
            )

            if created:
                created_count += 1
                self.stdout.write(f'생성: {month} - {congestion_values}')
            else:
                updated_count += 1
                self.stdout.write(f'업데이트: {month} - {congestion_values}')

        # 결과 출력
        self.stdout.write(
            self.style.SUCCESS(
                f'혼잡도 데이터 로드 완료! '
                f'생성: {created_count}개, 업데이트: {updated_count}개'
            )
        )
