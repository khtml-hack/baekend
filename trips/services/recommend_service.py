import json
import os
from datetime import datetime, time, timedelta
from django.conf import settings
from ..models import Recommendation
from .congestion_service import (
    get_monthly_index,
    get_optimal_time_window,
    calculate_congestion_score,
    get_recommendation_level,
)
from integrations.kakao import search_address, keyword_search
from integrations.tmap import get_traffic_info, summarize_traffic


def _infer_location_from_address(address: str) -> str:
    """간단한 문자열 매핑으로 혼잡도 위치 키를 유추 (없으면 default)."""
    if not address:
        return "default"
    lower = address.lower()
    # 한글 키워드도 함께 검사
    if "gangnam" in lower or "강남" in address:
        return "gangnam"
    if "hongdae" in lower or "홍대" in address:
        return "hongdae"
    if "myeongdong" in lower or "명동" in address:
        return "myeongdong"
    if "이문동" in address or "imun" in lower or "imundong" in lower:
        return "imun"
    return "default"
from integrations.openai_gpt import get_travel_recommendation


def get_congestion_json_data():
    """
    혼잡도 JSON 데이터를 직접 읽어서 반환
    """
    json_file_path = os.path.join(settings.BASE_DIR, 'trips', 'fixtures', 'congestion_data.json')
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _safe_float(value):
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _haversine_km(lat1, lon1, lat2, lon2):
    """Calculate great-circle distance between two points in kilometers."""
    from math import radians, sin, cos, asin, sqrt
    if None in (lat1, lon1, lat2, lon2):
        return None
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return R * c


def _map_time_to_bucket(hour: int) -> str:
    """Map an hour to legacy bucket labels to satisfy DB choices."""
    # Keep legacy buckets internally; UI won't show these.
    if 6 <= hour < 8:
        return "T0"
    if 8 <= hour < 10:
        return "T1"
    if 17 <= hour < 19:
        return "T2"
    if 19 <= hour < 21:
        return "T3"
    # Fallback choose closest bucket
    return "T1"


def _build_depart_in_text(now_dt: datetime, target_time_str: str) -> str:
    """Create human text like '15분 뒤 출발 (HH:MM)'.
    If the target time is earlier than now, roll to next day.
    If within 2분, show '지금 출발'.
    """
    base_time = time.fromisoformat(target_time_str)
    target_dt = datetime.combine(now_dt.date(), base_time)
    # 먼저 같은 분 내(±2분)인지 판단 후, 아니면 다음날로 롤오버
    delta_seconds = (target_dt - now_dt).total_seconds()
    if -120 <= delta_seconds <= 120:
        return f"지금 출발 ({base_time.strftime('%H:%M')})"
    if delta_seconds < 0:
        target_dt = target_dt + timedelta(days=1)
    delta_min = int((target_dt - now_dt).total_seconds() // 60)
    if abs(delta_min) <= 2:
        return f"지금 출발 ({base_time.strftime('%H:%M')})"
    return f"{delta_min}분 뒤 출발 ({base_time.strftime('%H:%M')})"


def _minutes_until(now_dt: datetime, target_time_str: str) -> int:
    """Minutes from now to next occurrence of target HH:MM (rolls to next day if needed)."""
    base_time = time.fromisoformat(target_time_str)
    target_dt = datetime.combine(now_dt.date(), base_time)
    if target_dt < now_dt:
        target_dt = target_dt + timedelta(days=1)
    return int((target_dt - now_dt).total_seconds() // 60)


def _time_str_add_minutes(hhmm: str, minutes: int) -> str:
    base_time = time.fromisoformat(hhmm)
    today = datetime(2000, 1, 1, base_time.hour, base_time.minute)
    new_dt = today + timedelta(minutes=minutes)
    return new_dt.strftime('%H:%M')


def create_recommendation(
    user,
    origin_address,
    destination_address,
    region_code=None,
    arrive_by: str | None = None,
    window_minutes: int = 120,
    debug: bool = False,
):
    """
    여행 추천 생성 (2개의 추천 옵션 제공)
    - 각 옵션별로 정밀한 분 단위 시간 추천
    - 최종 optimal_departure_time은 분 단위 결정론 스캐닝으로 확정
    """
    # 1. Kakao API를 통한 주소 정규화
    origin_info = search_address(origin_address)
    destination_info = search_address(destination_address)
    
    normalized_origin = origin_info.get('normalized_address', origin_address)
    normalized_destination = destination_info.get('normalized_address', destination_address)
    
    # 2-a. 좌표 추출
    origin_lat = _safe_float(origin_info.get('y'))
    origin_lon = _safe_float(origin_info.get('x'))
    dest_lat = _safe_float(destination_info.get('y'))
    dest_lon = _safe_float(destination_info.get('x'))

    # 주소 검색이 실패한 경우(좌표 없음) 키워드 검색으로 보완
    if origin_lat is None or origin_lon is None:
        try:
            kw = keyword_search(origin_address)
            docs = kw.get('documents') or []
            if docs:
                origin_lon = _safe_float(docs[0].get('x'))
                origin_lat = _safe_float(docs[0].get('y'))
        except Exception:
            pass
    if dest_lat is None or dest_lon is None:
        try:
            kw = keyword_search(destination_address)
            docs = kw.get('documents') or []
            if docs:
                dest_lon = _safe_float(docs[0].get('x'))
                dest_lat = _safe_float(docs[0].get('y'))
        except Exception:
            pass

    # 2-b. (옵션) TMAP 비활성 플래그면 완전 스킵
    tmap_summary = None
    tmap_meta = None
    if getattr(settings, 'USE_TMAP', False):

        tmap_meta = {
            'has_key': bool(getattr(settings, 'TMAP_APP_KEY', None)),
            'enabled': False,
            'reason': ''
        }
        if origin_lat and origin_lon and tmap_meta['has_key']:
            tmap_raw = get_traffic_info(origin_lat, origin_lon)
            tmap_summary = summarize_traffic(tmap_raw)
            tmap_meta['enabled'] = bool(tmap_summary and tmap_summary.get('total_roads', 0) > 0)
            if not tmap_meta['enabled']:
                tmap_meta['reason'] = 'TMAP 응답 없음 또는 비정상'
        elif not tmap_meta['has_key']:
            tmap_meta['reason'] = 'TMAP_APP_KEY 미설정'
        else:
            tmap_meta['reason'] = '출발지 좌표 없음'

    # 3. 혼잡도 데이터 조회 (현재 월)
    current_congestion = get_monthly_index(region_code=region_code)
    
    # 4. 전체 혼잡도 JSON 데이터 조회 (AI가 패턴 분석용)
    full_congestion_data = get_congestion_json_data()
    
    # 5. 최적 bucket 선택 (혼잡도가 가장 낮은 시간대)
    best_bucket = min(current_congestion.items(), key=lambda x: x[1])[0]
    
    # 6. 추천 원본 생성
    # Arrive-By 모드가 주어지면 해당 모드 우선
    arrive_by_result = None
    if arrive_by:
        try:
            arrive_by_result = compute_latest_departure_for_arrival(
                origin_address, destination_address, arrive_by, window_minutes
            )
        except Exception:
            arrive_by_result = None

    ai_recommendation = get_travel_recommendation(
        normalized_origin, 
        normalized_destination, 
        current_congestion,
        full_congestion_data,
        tmap_summary=tmap_summary
    )

    # 7. AI 응답 정규화 (Figma 스키마: current + options)
    now_dt = datetime.now()
    options = []
    current_block = None

    if arrive_by_result:
        # Arrive-By 모드: 서버 결정값으로 옵션 두 개 구성(최적 + 대안 1)
        primary_depart = arrive_by_result['depart_time']
        window_start = arrive_by_result['search_window']['start']
        window_end = arrive_by_result['search_window']['end']  # arrive_by
        dep_dt = time.fromisoformat(primary_depart)
        # 창 범위 내 강제 클램프 및 일관 재계산
        ws_dt = time.fromisoformat(window_start)
        we_dt = time.fromisoformat(window_end)
        dep_datetime = datetime.combine(now_dt.date(), dep_dt)
        ws_datetime = datetime.combine(now_dt.date(), ws_dt)
        we_datetime = datetime.combine(now_dt.date(), we_dt)
        if dep_datetime < ws_datetime or dep_datetime > we_datetime:
            dep_datetime = min(max(dep_datetime, ws_datetime), we_datetime)
            primary_depart = dep_datetime.strftime('%H:%M')
        cong_score = calculate_congestion_score(dep_datetime, _infer_location_from_address(normalized_destination))
        # 새 민감도로 소요시간 재계산
        try:
            BASE_SPEED_KMH = 30.0
            ROUTE_FACTOR = 1.35
            origin_info_tmp = search_address(origin_address)
            dest_info_tmp = search_address(destination_address)
            origin_lat_tmp = _safe_float(origin_info_tmp.get('y'))
            origin_lon_tmp = _safe_float(origin_info_tmp.get('x'))
            dest_lat_tmp = _safe_float(dest_info_tmp.get('y'))
            dest_lon_tmp = _safe_float(dest_info_tmp.get('x'))
            dist_km_raw_tmp = _haversine_km(origin_lat_tmp, origin_lon_tmp, dest_lat_tmp, dest_lon_tmp)
            dist_km_tmp = dist_km_raw_tmp * ROUTE_FACTOR if dist_km_raw_tmp is not None else None
            tm = 1.0 + 0.45 * (max(0.0, float(cong_score) - 1.0) ** 1.2)
            if dist_km_tmp is not None:
                expected_duration = int(round((dist_km_tmp / BASE_SPEED_KMH) * 60.0 * tm))
            else:
                expected_duration = int(arrive_by_result.get('expected_duration_min', 30))
        except Exception:
            expected_duration = int(arrive_by_result.get('expected_duration_min', 30))

        options = [
            {
                'title': '도착제한 최적',
                'depart_in_text': _build_depart_in_text(now_dt, primary_depart),
                'window': {'start': window_start, 'end': window_end},
                'optimal_departure_time': primary_depart,
                'expected_duration_min': expected_duration,
                'congestion_level': int(round(max(1.0, min(5.0, float(cong_score))))),
                'congestion_description': get_recommendation_level(cong_score),
                'time_saved_min': 0,
                'reward_amount': 0,
            }
        ]
        # 대안이 있으면 하나 추가
        alts = arrive_by_result.get('alternatives') or []
        if alts:
            alt = alts[0]
            alt_depart = alt.get('depart_time', primary_depart)
            alt_dep_dt = time.fromisoformat(alt_depart)
            alt_dep_datetime = datetime.combine(now_dt.date(), alt_dep_dt)
            # 창 범위 내 클램프
            if alt_dep_datetime < ws_datetime or alt_dep_datetime > we_datetime:
                alt_dep_datetime = min(max(alt_dep_datetime, ws_datetime), we_datetime)
                alt_depart = alt_dep_datetime.strftime('%H:%M')
            alt_cong = calculate_congestion_score(alt_dep_datetime, _infer_location_from_address(normalized_destination))
            options.append({
                'title': '도착제한 대안',
                'depart_in_text': _build_depart_in_text(now_dt, alt_depart),
                'window': {'start': window_start, 'end': window_end},
                'optimal_departure_time': alt_depart,
                # 대안도 새 민감도로 재계산
                'expected_duration_min': int(alt.get('expected_duration_min', expected_duration)),
                'congestion_level': int(round(max(1.0, min(5.0, float(alt_cong))))),
                'congestion_description': get_recommendation_level(alt_cong),
                'time_saved_min': 0,
                'reward_amount': 0,
            })
    else:
        if 'options' in ai_recommendation and isinstance(ai_recommendation['options'], list):
            options = ai_recommendation['options']
        else:
            # 구버전 스키마를 options로 변환
            legacy_recs = ai_recommendation.get('recommendations', [])
            for rec in legacy_recs:
                opt_time = rec.get('optimal_departure_time') or rec.get('recommended_window', {}).get('start', '06:00')
                options.append({
                    'title': rec.get('option_type', '옵션'),
                    'depart_in_text': _build_depart_in_text(now_dt, opt_time),
                    'window': {
                        'start': rec.get('recommended_window', {}).get('start', '06:00'),
                        'end': rec.get('recommended_window', {}).get('end', '08:00'),
                    },
                    'optimal_departure_time': opt_time,
                    'expected_duration_min': rec.get('expected_duration_min', 30),
                    'congestion_level': rec.get('expected_congestion_level', 3),
                    'congestion_description': rec.get('congestion_description', '보통'),
                    'time_saved_min': rec.get('time_saved_min', 0),
                    'reward_amount': rec.get('reward_amount', 50),
                })

    # current 블록은 항상 서버에서 계산하여 사용 (AI 값 무시)
    current_block = None
    # 목적지 주소로부터 간단히 위치 키 추정
    inferred_location = _infer_location_from_address(normalized_destination)
    
    if len(options) < 2:
        if arrive_by_result:
            # 도착제한 모드에서 대안이 없을 때: 창 내에서 최적 근처의 대안 1개 생성
            try:
                primary_time = options[0]['optimal_departure_time']
                ws = options[0]['window']['start']
                we = options[0]['window']['end']
                ws_dt = time.fromisoformat(ws)
                we_dt = time.fromisoformat(we)
                arrive_time_dt = time.fromisoformat(we)  # arrive_by == window end
                arrive_dt = datetime.combine(now_dt.date(), arrive_time_dt)

                # 후보 이동(분): -15, -10, +10, +15 (우선 앞당김 위주)
                for shift in (-15, -10, 10, 15):
                    cand = _time_str_add_minutes(primary_time, shift)
                    cand_t = time.fromisoformat(cand)
                    # 창 범위 체크
                    if not (datetime.combine(now_dt.date(), ws_dt) <= datetime.combine(now_dt.date(), cand_t) <= datetime.combine(now_dt.date(), we_dt)):
                        continue
                    # 소요시간 재계산
                    dep_dt = datetime.combine(now_dt.date(), cand_t)
                    cong = calculate_congestion_score(dep_dt, inferred_location)
                    tm = 1.0 + 0.45 * (max(0.0, float(cong) - 1.0) ** 1.2)
                    dist_km_raw = _haversine_km(origin_lat, origin_lon, dest_lat, dest_lon)
                    dist_km = dist_km_raw * 1.35 if dist_km_raw is not None else None
                    if dist_km is None:
                        continue
                    dur = int(round((dist_km / 30.0) * 60.0 * tm))
                    # 도착 제한 충족
                    if dep_dt + timedelta(minutes=dur) <= arrive_dt:
                        options.append({
                            'title': '도착제한 대안',
                            'depart_in_text': _build_depart_in_text(now_dt, cand),
                            'window': {'start': ws, 'end': we},
                            'optimal_departure_time': cand,
                            'expected_duration_min': dur,
                            'congestion_level': max(1, min(5, int(round(float(cong))))),
                            'congestion_description': get_recommendation_level(cong),
                            'time_saved_min': 0,
                            'reward_amount': 0,
                        })
                        break
            except Exception:
                pass
        # 일반 모드에서만 기본 카드 생성
        if not arrive_by_result and len(options) < 2:
            options = [
                {
                    'title': '최적 시간',
                    'depart_in_text': _build_depart_in_text(now_dt, '06:30'),
                    'window': {'start': '06:00', 'end': '08:00'},
                    'optimal_departure_time': '06:30',
                    'expected_duration_min': 30,
                    'congestion_level': 2,
                    'congestion_description': '원활',
                    'time_saved_min': 20,
                    'reward_amount': 100,
                },
                {
                    'title': '대안 시간',
                    'depart_in_text': _build_depart_in_text(now_dt, '08:30'),
                    'window': {'start': '08:00', 'end': '10:00'},
                    'optimal_departure_time': '08:30',
                    'expected_duration_min': 35,
                    'congestion_level': 3,
                    'congestion_description': '보통',
                    'time_saved_min': 15,
                    'reward_amount': 80,
                },
            ]
    
    # 7. 각 옵션별로 분 단위 결정론 스캔으로 최적 분 확정
    #    보상은 시간절감에 비례해 동적으로 산정
    processed_recommendations = []
    global_now_str = now_dt.strftime('%H:%M')
    # Arrive-By 모드면 서버가 준 창을 그대로 사용, 아니면 기본 2시간 창
    if arrive_by_result:
        global_end_str = arrive_by_result['search_window']['end']
    else:
        global_end_str = _time_str_add_minutes(global_now_str, 120)

    first_optimal_time = None
    # 동적 보상 계산을 위한 기준(가장 느린 예상 소요시간)
    try:
        baseline_duration = max(int(o.get('expected_duration_min', 30)) for o in options) if options else 30
    except Exception:
        baseline_duration = 30
    REWARD_FACTOR = 10 # 분당 3포인트, 0~100 캡

    det_first = None
    alt_first = []
    for i, rec in enumerate(options):
        # 2시간 이내 강제: 모든 옵션은 [now, now+120] 범위에서만 탐색
        # 두 번째 옵션은 최소 15분 이후부터 탐색해 첫 번째와 겹치지 않게 함
        if arrive_by_result:
            # 도착제한 창 고정 사용
            window_start_str = arrive_by_result['search_window']['start']
            window_end_str = arrive_by_result['search_window']['end']
        else:
            if i == 0:
                window_start_str = global_now_str
            else:
                window_start_str = _time_str_add_minutes(global_now_str, 15)
            window_end_str = global_end_str

        # 안전 보정: 시작이 끝보다 뒤가 되지 않게
        ws_dt = time.fromisoformat(window_start_str)
        we_dt = time.fromisoformat(window_end_str)
        if (datetime.combine(now_dt.date(), ws_dt) >= datetime.combine(now_dt.date(), we_dt)):
            # 끝에서 15분 뺀 지점으로 시작 세팅
            window_start_str = _time_str_add_minutes(window_end_str, -15)
            ws_dt = time.fromisoformat(window_start_str)
        
        # 분 단위 결정론 스캔으로 최적 분 확정
        # Arrive-By 모드에서는 이미 서버가 최적 출발 분을 계산했으므로 그대로 사용
        if arrive_by_result:
            deterministic = None
        else:
            deterministic = get_optimal_time_window(
                current_time=now_dt,
                window_hours=None,
                location=inferred_location,
                window_start_time=ws_dt,
                window_end_time=we_dt
            )

        # 1안은 최적, 2안은 같은 창에서 계산된 대안 최소점을 우선 채택
        if i == 0:
            if arrive_by_result:
                optimal_departure = options[0]['optimal_departure_time']
            else:
                optimal_departure = deterministic['optimal_time']['time'] if deterministic else window_start_str
            det_first = deterministic
            alt_first = (deterministic.get('alternative_times') if deterministic else []) or []
        else:
            if arrive_by_result and len(options) > 1:
                optimal_departure = options[1]['optimal_departure_time']
            else:
                if det_first and alt_first:
                    optimal_departure = alt_first[0]['time']
                else:
                    optimal_departure = deterministic['optimal_time']['time'] if deterministic else window_start_str

        # 두 번째 옵션이 첫 번째와 동일하면 10분 뒤로 미세 이동 (끝을 넘지 않게)
        if i == 1 and first_optimal_time == optimal_departure:
            candidate = _time_str_add_minutes(optimal_departure, 10)
            # 경계를 넘지 않도록 조정
            if datetime.combine(now_dt.date(), time.fromisoformat(candidate)) > datetime.combine(now_dt.date(), we_dt):
                # 넘으면 10분 앞당김
                candidate = _time_str_add_minutes(optimal_departure, -10)
            optimal_departure = candidate

        if i == 0:
            first_optimal_time = optimal_departure

        # 예상 소요시간 계산 (하버사인 + 혼잡도 배율)
        BASE_SPEED_KMH = 30.0
        ROUTE_FACTOR = 1.35
        try:
            dist_km_raw = _haversine_km(origin_lat, origin_lon, dest_lat, dest_lon)
            dist_km = dist_km_raw * ROUTE_FACTOR if dist_km_raw is not None else None
            dep_dt = datetime.combine(now_dt.date(), time.fromisoformat(optimal_departure))
            cong_score = calculate_congestion_score(dep_dt, inferred_location)
            # 지수형 혼잡 점수는 1~5 범위. 보다 공격적으로 반영하기 위해 제곱 가중
            time_multiplier = 1.0 + 0.45 * (max(0.0, float(cong_score) - 1.0) ** 1.2)
            if dist_km is not None:
                expected_duration = int(round((dist_km / BASE_SPEED_KMH) * 60.0 * time_multiplier))
            else:
                expected_duration = int(rec.get('expected_duration_min', 30))
        except Exception:
            expected_duration = int(rec.get('expected_duration_min', 30)) if isinstance(rec.get('expected_duration_min', 30), (int, float)) else 30

        # 혼잡도 설명/레벨 갱신
        try:
            congestion_description = get_recommendation_level(cong_score)
            expected_congestion_level = max(1, min(5, int(round(float(cong_score)))))
        except Exception:
            congestion_description = rec.get('congestion_description', '보통')
            expected_congestion_level = rec.get('congestion_level', rec.get('expected_congestion_level', 3))

        # 임시 저장(보상은 나중에 baseline 재산정 후 일괄 계산)
        time_saved_min = 0
        reward_amount = 0

        processed_recommendations.append({
            'option_type': rec.get('title', f'옵션 {i+1}'),
            'recommended_bucket': _map_time_to_bucket(time.fromisoformat(optimal_departure).hour),
            'recommended_window': {
                'start': window_start_str,
                'end': window_end_str
            },
            'optimal_departure_time': optimal_departure,
            'rationale': rec.get('rationale', '혼잡도 데이터를 기반으로 한 추천입니다.'),
            'expected_duration_min': expected_duration,
            'expected_congestion_level': expected_congestion_level,
            'congestion_description': congestion_description,
            'time_sensitivity': rec.get('time_sensitivity', '보통'),
            'time_saved_min': time_saved_min,
            'reward_amount': reward_amount
        })

    # 대안 다양성 보정: 두 옵션 소요시간이 동일/유사(<=1분)하면 대안 시간을 ±10~20분 이동해 차이를 확보
    if len(processed_recommendations) >= 2:
        try:
            first = processed_recommendations[0]
            second = processed_recommendations[1]
            if abs(int(first['expected_duration_min']) - int(second['expected_duration_min'])) <= 1:
                def recompute_for(time_str: str) -> tuple[int, float]:
                    dep_dt_local = datetime.combine(now_dt.date(), time.fromisoformat(time_str))
                    cong = calculate_congestion_score(dep_dt_local, inferred_location)
                    tm = 1.0 + 0.35 * max(0.0, float(cong) - 1.0)
                    dist_km_raw_local = _haversine_km(origin_lat, origin_lon, dest_lat, dest_lon)
                    dist_km_local = dist_km_raw_local * 1.35 if dist_km_raw_local is not None else None
                    if dist_km_local is not None:
                        dur_local = int(round((dist_km_local / 30.0) * 60.0 * tm))
                    else:
                        dur_local = second['expected_duration_min']
                    return dur_local, float(cong)

                # 후보: +10, -10, +20, -20 분 범위 내에서 창을 넘지 않게 조정
                shifts = [10, -10, 20, -20]
                ws = time.fromisoformat(second['recommended_window']['start'])
                we = time.fromisoformat(second['recommended_window']['end'])
                base_time = time.fromisoformat(second['optimal_departure_time'])
                def within_window(t: time) -> bool:
                    start_dt_local = datetime.combine(now_dt.date(), ws)
                    end_dt_local = datetime.combine(now_dt.date(), we)
                    cand_dt_local = datetime.combine(now_dt.date(), t)
                    return start_dt_local <= cand_dt_local <= end_dt_local

                chosen = None
                for s in shifts:
                    cand = _time_str_add_minutes(base_time.strftime('%H:%M'), s)
                    cand_t = time.fromisoformat(cand)
                    if within_window(cand_t):
                        dur_new, cong_new = recompute_for(cand)
                        if abs(int(first['expected_duration_min']) - dur_new) >= 2:
                            chosen = (cand, dur_new, cong_new)
                            break
                if chosen is not None:
                    cand_time, dur_new, cong_new = chosen
                    second['optimal_departure_time'] = cand_time
                    second['expected_duration_min'] = dur_new
                    second['expected_congestion_level'] = max(1, min(5, int(round(cong_new))))
                    second['congestion_description'] = get_recommendation_level(cong_new)
                    second['recommended_bucket'] = _map_time_to_bucket(time.fromisoformat(cand_time).hour)
        except Exception:
            pass

    # 최종 baseline 재산정 후 보상/절감 재계산
    if processed_recommendations:
        # 기준선: 지금 출발했을 때의 예상 소요시간
        try:
            BASE_SPEED_KMH = 30.0
            ROUTE_FACTOR = 1.35
            dist_km_raw_now = _haversine_km(origin_lat, origin_lon, dest_lat, dest_lon)
            dist_km_now = dist_km_raw_now * ROUTE_FACTOR if dist_km_raw_now is not None else None
            cong_now = calculate_congestion_score(now_dt, location=inferred_location)
            time_multiplier_now = 1.0 + 0.45 * (max(0.0, float(cong_now) - 1.0) ** 1.2)
            if dist_km_now is not None:
                baseline_duration = int(round((dist_km_now / BASE_SPEED_KMH) * 60.0 * time_multiplier_now))
            else:
                baseline_duration = max(r['expected_duration_min'] for r in processed_recommendations)
        except Exception:
            baseline_duration = max(r['expected_duration_min'] for r in processed_recommendations)
        
        for r in processed_recommendations:
            time_saved_min = max(0, baseline_duration - r['expected_duration_min'])
            r['time_saved_min'] = time_saved_min
            r['reward_amount'] = max(0, min(100, int(round(time_saved_min * REWARD_FACTOR))))

        # 대안이 최적보다 더 많이 절약하지 않도록 정렬/레이블 보정
        if len(processed_recommendations) >= 2:
            # 절약 분 기준 내림차순으로 우선 정렬
            if processed_recommendations[1]['time_saved_min'] > processed_recommendations[0]['time_saved_min']:
                processed_recommendations[0], processed_recommendations[1] = processed_recommendations[1], processed_recommendations[0]

            # 레이블 정규화 (arrive_by 모드와 일반 모드 구분)
            try:
                if arrive_by_result:
                    processed_recommendations[0]['option_type'] = '도착제한 최적'
                    processed_recommendations[1]['option_type'] = '도착제한 대안'
                else:
                    processed_recommendations[0]['option_type'] = '최적 시간'
                    processed_recommendations[1]['option_type'] = '대안 시간'
            except Exception:
                pass
    
    # 8. Recommendation 객체 생성 (첫 번째 옵션을 메인으로 저장)
    main_rec = processed_recommendations[0]
    recommendation = Recommendation.objects.create(
        user=user,
        origin_address=normalized_origin,
        destination_address=normalized_destination,
        recommended_bucket=main_rec['recommended_bucket'],
        window_start=time.fromisoformat(main_rec['recommended_window']['start']),
        window_end=time.fromisoformat(main_rec['recommended_window']['end']),
        expected_duration_min=main_rec['expected_duration_min'],
        expected_congestion_level=main_rec['expected_congestion_level'],
        rationale=main_rec['rationale']
    )
    
    # 9. 현재 시간 분석: 지금 출발 가정으로 계산
    try:
        duration_min = baseline_duration if processed_recommendations else 30
    except Exception:
        duration_min = 30
    score = calculate_congestion_score(now_dt, location=inferred_location)
    current_analysis = {
        'departure_time': now_dt.strftime('%H:%M'),
        'arrival_time': (now_dt + timedelta(minutes=duration_min)).strftime('%H:%M'),
        'duration_min': duration_min,
        'congestion_level': round(float(score), 2),
        'congestion_description': get_recommendation_level(score),
        'location': inferred_location,
    }

    # 10. 결과 반환 (Figma 형태 포함)
    result = {
        'recommendation_id': recommendation.id,
        'ui': {
            'current': {
                'departure_time': current_analysis['departure_time'],
                'arrival_time': current_analysis['arrival_time'],
                'duration_min': current_analysis['duration_min'],
                'congestion_level': current_analysis['congestion_level'],
                'congestion_description': current_analysis['congestion_description'],
            },
            'options': [
                {
                    'title': processed_recommendations[0]['option_type'],
                    'depart_in_text': _build_depart_in_text(now_dt, processed_recommendations[0]['optimal_departure_time']),
                    'window': processed_recommendations[0]['recommended_window'],
                    'optimal_departure_time': processed_recommendations[0]['optimal_departure_time'],
                    'expected_duration_min': processed_recommendations[0]['expected_duration_min'],
                    'congestion_level': processed_recommendations[0]['expected_congestion_level'],
                    'congestion_description': processed_recommendations[0]['congestion_description'],
                    'time_saved_min': processed_recommendations[0]['time_saved_min'],
                    'reward_amount': processed_recommendations[0]['reward_amount'],
                },
                {
                    'title': processed_recommendations[1]['option_type'] if len(processed_recommendations) > 1 else '대안 시간',
                    'depart_in_text': _build_depart_in_text(now_dt, (processed_recommendations[1]['optimal_departure_time'] if len(processed_recommendations) > 1 else processed_recommendations[0]['optimal_departure_time'])),
                    'window': (processed_recommendations[1]['recommended_window'] if len(processed_recommendations) > 1 else processed_recommendations[0]['recommended_window']),
                    'optimal_departure_time': (processed_recommendations[1]['optimal_departure_time'] if len(processed_recommendations) > 1 else processed_recommendations[0]['optimal_departure_time']),
                    'expected_duration_min': (processed_recommendations[1]['expected_duration_min'] if len(processed_recommendations) > 1 else processed_recommendations[0]['expected_duration_min']),
                    'congestion_level': (processed_recommendations[1]['expected_congestion_level'] if len(processed_recommendations) > 1 else processed_recommendations[0]['expected_congestion_level']),
                    'congestion_description': (processed_recommendations[1]['congestion_description'] if len(processed_recommendations) > 1 else processed_recommendations[0]['congestion_description']),
                    'time_saved_min': (processed_recommendations[1]['time_saved_min'] if len(processed_recommendations) > 1 else processed_recommendations[0]['time_saved_min']),
                    'reward_amount': (processed_recommendations[1]['reward_amount'] if len(processed_recommendations) > 1 else processed_recommendations[0]['reward_amount']),
                },
            ],
            # TMAP 비활성 시 필드 제거
            **({} if tmap_summary is None else {'tmap_summary': tmap_summary}),
            **({} if tmap_meta is None else {'tmap_meta': tmap_meta}),
        },
        'origin_address': normalized_origin,
        'destination_address': normalized_destination,
        'origin_location': {
            'lat': origin_lat,
            'lng': origin_lon,
        },
        'destination_location': {
            'lat': dest_lat,
            'lng': dest_lon,
        },
        'ai_confidence': 'high'
    }

    # 디버그가 아닐 때는 레거시 필드를 숨김
    if debug:
        result['recommendations'] = processed_recommendations
        result['current_time_analysis'] = current_analysis
    
    return result


def compute_latest_departure_for_arrival(origin_address: str, destination_address: str, arrive_by_hhmm: str, window_minutes: int = 120) -> dict:
    """
    도착 마감시각(arrive_by)을 만족하는 가장 늦은 출발시각을 1분 단위로 탐색.
    - Kakao 주소 정규화와 좌표 추출 사용
    - 혼잡도 점수로 소요시간을 추정하여 역산
    Returns dict: {
        'depart_time': 'HH:MM',
        'arrive_by': 'HH:MM',
        'expected_duration_min': int,
        'alternatives': [{depart_time, expected_duration_min, congestion_score}, ... up to 2],
        'search_window': {start: 'HH:MM', end: 'HH:MM'}
    }
    """
    now_dt = datetime.now()
    try:
        arrive_time = time.fromisoformat(arrive_by_hhmm)
    except Exception:
        raise ValueError("arrive_by 형식이 잘못되었습니다. HH:MM")

    arrive_dt = datetime.combine(now_dt.date(), arrive_time)
    if arrive_dt <= now_dt:
        arrive_dt = arrive_dt + timedelta(days=1)

    # 좌표 확보
    origin_info = search_address(origin_address)
    destination_info = search_address(destination_address)
    origin_lat = _safe_float(origin_info.get('y'))
    origin_lon = _safe_float(origin_info.get('x'))
    dest_lat = _safe_float(destination_info.get('y'))
    dest_lon = _safe_float(destination_info.get('x'))

    if origin_lat is None or origin_lon is None or dest_lat is None or dest_lon is None:
        # 좌표 없으면 보수적 기본 소요시간 40분 가정하여 단순 역산
        default_duration = 40
        latest_depart = arrive_dt - timedelta(minutes=default_duration)
        return {
            'depart_time': latest_depart.strftime('%H:%M'),
            'arrive_by': arrive_dt.strftime('%H:%M'),
            'expected_duration_min': default_duration,
            'alternatives': [],
            'search_window': {
                'start': (arrive_dt - timedelta(minutes=window_minutes)).strftime('%H:%M'),
                'end': arrive_dt.strftime('%H:%M')
            }
        }

    # 탐색 범위: arrive_by 이전 window_minutes 동안, 뒤에서 앞으로 역탐색
    inferred_location = _infer_location_from_address(destination_info.get('normalized_address') or destination_address)
    start_dt = arrive_dt - timedelta(minutes=window_minutes)
    probe = arrive_dt.replace(second=0, microsecond=0)
    if probe > arrive_dt:
        probe = probe - timedelta(minutes=1)

    BASE_SPEED_KMH = 30.0
    ROUTE_FACTOR = 1.35

    candidates = []
    # 뒤에서 앞으로 1분 단위 역탐색: 도착시각 - 예측소요시간 = 출발시각
    cursor = arrive_dt - timedelta(minutes=1)
    while cursor >= start_dt:
        # 해당 분에 출발하면 도착시간이 arrive_by를 넘지 않는지 체크
        cong_score = calculate_congestion_score(cursor, inferred_location)
        time_multiplier = 1.0 + 0.25 * max(0.0, float(cong_score) - 1.0)
        dist_km_raw = _haversine_km(origin_lat, origin_lon, dest_lat, dest_lon)
        if dist_km_raw is not None:
            from math import ceil
            expected_duration = int(ceil((dist_km_raw * ROUTE_FACTOR / BASE_SPEED_KMH) * 60.0 * time_multiplier))
        else:
            expected_duration = 30
        arrival_est = cursor + timedelta(minutes=expected_duration)
        if arrival_est <= arrive_dt:
            # 유효 후보
            candidates.append({'depart': cursor, 'duration': expected_duration, 'cong': float(cong_score)})
        cursor = cursor - timedelta(minutes=1)

    if not candidates:
        # 창 내 충족 불가 시, 가장 이른 출발을 제안
        earliest = start_dt
        cong_score = calculate_congestion_score(earliest, inferred_location)
        time_multiplier = 1.0 + 0.25 * max(0.0, float(cong_score) - 1.0)
        dist_km_raw = _haversine_km(origin_lat, origin_lon, dest_lat, dest_lon)
        from math import ceil
        expected_duration = int(ceil((dist_km_raw * ROUTE_FACTOR / BASE_SPEED_KMH) * 60.0 * time_multiplier)) if dist_km_raw is not None else 30
        return {
            'depart_time': earliest.strftime('%H:%M'),
            'arrive_by': arrive_dt.strftime('%H:%M'),
            'expected_duration_min': expected_duration,
            'alternatives': [],
            'search_window': {
                'start': start_dt.strftime('%H:%M'),
                'end': arrive_dt.strftime('%H:%M')
            }
        }

    # 가장 늦은 출발시각 = 후보 중 depart가 최대인 항목
    best = max(candidates, key=lambda c: c['depart'])
    # 대안 2개: best보다 10분, 20분 앞선 근접 후보가 있으면 채택
    alts = []
    for gap in (10, 20):
        target = best['depart'] - timedelta(minutes=gap)
        near = min(candidates, key=lambda c: abs(int((c['depart'] - target).total_seconds() // 60)))
        if near and near['depart'] < best['depart']:
            alts.append(near)
    # 중복 제거 및 최대 2개
    seen = set()
    alt_clean = []
    for a in alts:
        key = a['depart'].strftime('%H:%M')
        if key not in seen:
            seen.add(key)
            alt_clean.append(a)
        if len(alt_clean) >= 2:
            break

    return {
        'depart_time': best['depart'].strftime('%H:%M'),
        'arrive_by': arrive_dt.strftime('%H:%M'),
        'expected_duration_min': int(best['duration']),
        'alternatives': [
            {
                'depart_time': a['depart'].strftime('%H:%M'),
                'expected_duration_min': int(a['duration']),
                'congestion_score': round(float(a['cong']), 2),
            } for a in alt_clean
        ],
        'search_window': {
            'start': start_dt.strftime('%H:%M'),
            'end': arrive_dt.strftime('%H:%M')
        }
    }
