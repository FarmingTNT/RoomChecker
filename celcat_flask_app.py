#!/usr/bin/env python3
"""
Flask web server for A29 Room Availability Checker
Run this on your computer/phone and access via browser
"""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, render_template_string, jsonify, request, send_from_directory
import requests
from datetime import datetime, timedelta

app = Flask(__name__)

API_URL = "https://celcat.u-bordeaux.fr/Calendar/Home/GetCalendarData"
REQUEST_TIMEOUT_SECONDS = float(os.environ.get('ROOMCHECKER_REQUEST_TIMEOUT', '8'))
MAX_FETCH_WORKERS = int(os.environ.get('ROOMCHECKER_MAX_WORKERS', '12'))

A29_ROOMS = [
    "A29/ Amphithéâtre A", "A29/ Amphithéâtre B", "A29/ Amphithéâtre C",
    "A29/ Amphithéâtre D", "A29/ Amphithéâtre E", "A29/ Amphithéâtre F",
    "A29/ Amphithéâtre G", "A29/ Salle 001", "A29/ Salle 101",
    "A29/ Salle 102", "A29/ Salle 103", "A29/ Salle 104",
    "A29/ Salle 105", "A29/ Salle 106", "A29/ Salle 107",
]

A22_ROOMS = [
    "A22/ Salle 96", "A22/ Salle 101", "A22/ Salle 102", "A22/ Salle 103",
    "A22/ Salle 104", "A22/ Salle 105", "A22/ Salle 107", "A22/ Salle 108",
    "A22/ Salle 109", "A22/ Salle 110", "A22/ Salle 111", "A22/ Salle 112",
    "A22/ Salle 113", "A22/ Salle 114", "A22/ Salle 115", "A22/ Salle 117",
    "A22/ Salle 119", "A22/ Salle 201", "A22/ Salle 202", "A22/ Salle 203",
    "A22/ Salle 204", "A22/ Salle 205", "A22/Amphithéâtre Alfred WEGENER",
    "A22/Amphithéâtre Charles DARWIN", "A22/Amphithéâtre Henri POINCARE",
    "A22/Amphithéâtre Rosalind FRANKLIN", "A22/Amphithéâtre Thomas EDISON",
]

A21_ROOMS = [
    "A21/ Salle 150", "A21/ Salle 151", "A21/ Salle 152", "A21/ Salle 153",
    "A21/ Salle 154", "A21/ Salle 155", "A21/ Salle 156", "A21/ Salle 158",
    "A21/ Salle 160", "A21/ Salle 161", "A21/ Salle 162", "A21/ Salle 165",
    "A21/ Salle 251", "A21/ Salle 253", "A21/ Salle 255", "A21/ Salle 256",
    "A21/ Salle 257", "A21/ Salle 261 Bocal lecteurs", "A21/ Salle 263 Bibliothèque",
    "A21/ Salle 301", "A21/ Salle 302", "A21/ Salle 303", "A21/ Salle 304",
    "A21/ Salle 305", "A21/ Salle 306", "A21/ Salle 307", "A21/ Salle 308",
    "A21/ Salle 309", "A21/ Salle 310", "A21/ Salle 311", "A21/ Salle 401",
    "A21/ Salle 402", "A21/ Salle 403", "A21/ Salle 404", "A21/ Salle 405",
    "A21/ Salle 406", "A21/ Salle 455", "A21/ Salle 457", "A21/Salle Informatique A",
    "A21/Salle Informatique B", "A21/Salle Informatique C",
]

ROOMS_BY_BUILDING = {
    "A29": A29_ROOMS,
    "A22": A22_ROOMS,
    "A21": A21_ROOMS,
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RoomChecker</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #F2EAD9;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 800px; margin: 0 auto; }
        .header {
            background: #121417;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 18px;
        }
        .logo {
            width: 64px;
            height: 64px;
            object-fit: contain;
            flex: 0 0 auto;
        }
        .header-text {
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        h1 { color: #F2EAD9; font-size: 28px; margin-bottom: 10px; }
        .subtitle { color: #c5c5c5; font-size: 14px; }
        .controls {
            background: #121417;
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 20px;
        }
        .top-row,
        .bottom-row {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        .bottom-row {
            margin-top: 12px;
        }
        #buildingSelect {
            width: 100%;
            flex: 1;
            padding: 10px 12px;
            border: 2px solid #8a2d2d;
            border-radius: 8px;
            font-size: 15px;
            background: #1f1f1f;
            color: #F2EAD9;
            font-weight: 600;
            outline: none;
            min-height: 43px;
        }
        #buildingSelect:focus {
            border-color: #c43a3a;
            box-shadow: 0 0 0 3px rgba(196,58,58,0.25);
        }
        .time-selector { display: flex; gap: 10px; flex-wrap: nowrap; width: 100%; }
        .time-input-wrapper {
            position: relative;
            flex: 0 0 50%;
            min-width: 0;
        }
        .time-input-wrapper .time-display-input {
            width: 100%;
            display: block;
            padding: 11px 42px 11px 14px;
            border: 2px solid #F2EAD9;
            border-radius: 8px;
            font-size: 16px;
            line-height: 1.2;
            font-weight: 600;
            min-height: 44px;
            min-width: 0;
            background: #F2EAD9;
            color: #1f1f1f;
        }
        .time-input-wrapper .time-display-input::placeholder {
            color: #766a61;
        }
        .time-input-icon {
            position: absolute;
            right: 14px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 17px;
            color: #8a2d2d;
            pointer-events: none;
        }
        button {
            padding: 12px 30px;
            background: #b23232;
            color: #F2EAD9;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }
        button:hover { transform: translateY(-2px); }
        button:disabled { opacity: 0.6; cursor: not-allowed; }
        .btn-now {
            width: 100%;
            margin-bottom: 0;
            padding: 10px 18px;
            font-size: 15px;
            flex: 1;
        }
        #checkBtn {
            flex: 1;
            min-height: 100%;
            padding: 10px 18px;
            font-size: 15px;
        }
        .loading {
            background: #121417;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            text-align: center;
            color: #F2EAD9;
        }
        .spinner {
            border: 4px solid #F2EAD9;
            border-top: 4px solid #b23232;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        .results {
            background: #121417;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .section-title {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 15px;
            color: #F2EAD9;
        }
        .room-card {
            background: #1a1d22;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 12px;
            border-left: 4px solid #b23232;
        }
        .room-name { font-weight: 600; color: #F2EAD9; font-size: 16px; }
        .room-info { color: #c5c5c5; font-size: 14px; margin-top: 5px; }
        .next-available-section {
            margin-top: 25px;
            padding-top: 25px;
            border-top: 2px solid #e0e0e0;
        }
        .next-available-card { border-left-color: #d85858; }
        .summary {
            margin-top: 20px;
            padding: 15px;
            background: #2a1111;
            border-radius: 10px;
            text-align: center;
            font-weight: 600;
            color: #ff8a8a;
        }
        .no-rooms { text-align: center; color: #c5c5c5; padding: 30px; }
        .flatpickr-calendar {
            background: #F2EAD9;
            border: 1px solid #cdb8ac;
            box-shadow: 0 14px 32px rgba(0, 0, 0, 0.28);
        }
        .flatpickr-months .flatpickr-month,
        .flatpickr-current-month .flatpickr-monthDropdown-months,
        .flatpickr-current-month input.cur-year,
        .flatpickr-weekday,
        span.flatpickr-weekday {
            color: #2d1919;
            fill: #2d1919;
        }
        .flatpickr-months .flatpickr-prev-month svg,
        .flatpickr-months .flatpickr-next-month svg {
            fill: #8a2d2d;
        }
        .flatpickr-day {
            color: #2d1919;
            border-radius: 8px;
        }
        .flatpickr-day:hover,
        .flatpickr-day:focus {
            background: #ead8cf;
            border-color: #ead8cf;
        }
        .flatpickr-day.today {
            border-color: #b23232;
        }
        .flatpickr-day.selected,
        .flatpickr-day.startRange,
        .flatpickr-day.endRange,
        .flatpickr-day.selected:hover,
        .flatpickr-day.startRange:hover,
        .flatpickr-day.endRange:hover {
            background: #b23232;
            border-color: #b23232;
            color: #F2EAD9;
        }
        .flatpickr-day.inRange {
            background: #f0cfcf;
            border-color: #f0cfcf;
            box-shadow: -5px 0 0 #f0cfcf, 5px 0 0 #f0cfcf;
        }
        .flatpickr-time input,
        .flatpickr-time .flatpickr-am-pm {
            color: #2d1919;
        }
        .flatpickr-time input:hover,
        .flatpickr-time .flatpickr-am-pm:hover,
        .flatpickr-time input:focus,
        .flatpickr-time .flatpickr-am-pm:focus {
            background: #ead8cf;
        }
        @media (max-width: 600px) {
            .header {
                flex-direction: row;
                text-align: left;
                align-items: center;
                gap: 12px;
                padding: 18px;
            }
            .header-text {
                align-items: flex-start;
            }
            .logo {
                width: 52px;
                height: 52px;
            }
            .top-row, .bottom-row, .time-selector { flex-direction: column; }
            .bottom-row { margin-top: 27px; }
            #buildingSelect { width: 100%; }
            #checkBtn { width: 100%; }
            .time-input-wrapper { width: 100%; flex: 0 0 auto; }
            .time-input-wrapper .time-display-input, button { width: 100%; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <img src="/RC.png" alt="Logo RoomChecker" class="logo" />
            <div class="header-text">
                <h1>RoomChecker</h1>
                <p class="subtitle">Alejandro Díaz - Université de Bordeaux</p>
            </div>
        </div>
        <div class="controls">
            <div class="top-row">
                <div class="time-selector">
                    <div class="time-input-wrapper">
                        <input type="text" id="timeInput" placeholder="Choisissez une date et une heure" />
                        <span class="time-input-icon">📅</span>
                    </div>
                    <button onclick="checkAvailability()" id="checkBtn">Heure choisie</button>
                </div>
            </div>
            <div class="bottom-row">
                <button onclick="checkNow()" class="btn-now">Heure actuelle</button>
                <select id="buildingSelect">
                    <option value="A29" selected>Bâtiment A29</option>
                    <option value="A22">Bâtiment A22</option>
                    <option value="A21">Bâtiment A21</option>
                    <option value="ALL">Tous les bâtiments (A21, A22, A29)</option>
                </select>
            </div>
        </div>
        <div id="loading" class="loading" style="display: none;">
            <div class="spinner"></div>
            <p>Vérification des salles...</p>
        </div>
        <div id="results" style="display: none;"></div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/flatpickr"></script>
    <script src="https://cdn.jsdelivr.net/npm/flatpickr/dist/l10n/fr.js"></script>
    <script>
        let timePicker;

        function initTimePicker() {
            timePicker = flatpickr('#timeInput', {
                enableTime: true,
                time_24hr: true,
                dateFormat: 'Y-m-d\\TH:i',
                altInput: true,
                altInputClass: 'time-display-input',
                altFormat: 'd/m/Y H:i',
                locale: 'fr',
                disableMobile: true,
                defaultDate: new Date(),
            });
        }

        function setDefaultTime() {
            if (timePicker) {
                timePicker.setDate(new Date(), true);
            }
        }
        
        async function checkNow() {
            setDefaultTime();
            await checkAvailability();
        }
        
        async function checkAvailability() {
            const timeInput = document.getElementById('timeInput').value;
            const buildingScope = document.getElementById('buildingSelect').value;
            if (!timeInput) { alert('Sélectionnez une heure'); return; }
            
            document.getElementById('loading').style.display = 'block';
            document.getElementById('results').style.display = 'none';
            document.getElementById('checkBtn').disabled = true;
            
            try {
                const response = await fetch('/api/check', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ time: timeInput, building: buildingScope })
                });
                
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || 'Erreur lors de la vérification des salles');
                }

                const data = await response.json();
                displayResults(data);
            } catch (error) {
                alert(error.message || 'Erreur lors de la vérification des salles');
                console.error(error);
            }
            
            document.getElementById('loading').style.display = 'none';
            document.getElementById('results').style.display = 'block';
            document.getElementById('checkBtn').disabled = false;
        }
        
        function displayResults(data) {
            let html = `<div class="results">
                <p style="text-align: center; color: #666; margin-bottom: 20px;">
                    ${data.check_time}<br>
                    <strong>${data.scope_label}</strong>
                </p>
                ${data.warning ? `<p style="text-align: center; color: #b06a00; margin-bottom: 20px;">${data.warning}</p>` : ''}
                <div class="section-title">Salles disponibles</div>`;
            
            if (data.available.length > 0) {
                data.available.forEach(room => {
                    html += `<div class="room-card">
                        <div class="room-name">${room.name}</div>
                        <div class="room-info">${room.info}</div>
                    </div>`;
                });
            } else {
                html += '<div class="no-rooms">Aucune salle disponible</div>';
            }
            
            if (data.next_available.length > 0) {
                html += '<div class="next-available-section"><div class="section-title">Prochaines disponibilités</div>';
                data.next_available.forEach(room => {
                    html += `<div class="room-card next-available-card">
                        <div class="room-name">${room.name}</div>
                        <div class="room-info">${room.info}</div>
                    </div>`;
                });
                html += '</div>';
            }
            
            html += `<div class="summary">${data.summary}</div></div>`;
            document.getElementById('results').innerHTML = html;
        }
        
        window.onload = () => {
            initTimePicker();
            setDefaultTime();
        };
    </script>
</body>
</html>
"""


def get_room_schedule(room_name, start_date, end_date):
    payload = {
        "start": start_date,
        "end": end_date,
        "resType": "102",
        "calView": "agendaDay",
        "federationIds[]": room_name,
        "colourScheme": "3"
    }
    try:
        response = requests.post(API_URL, data=payload, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        return None


def get_room_schedules_parallel(rooms, start_date, end_date):
    if not rooms:
        return {}

    workers = max(1, min(MAX_FETCH_WORKERS, len(rooms)))
    schedules = {}

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_room = {
            executor.submit(get_room_schedule, room, start_date, end_date): room
            for room in rooms
        }
        for future in as_completed(future_to_room):
            room = future_to_room[future]
            try:
                schedules[room] = future.result()
            except Exception:
                schedules[room] = None

    return schedules


def parse_event_bounds(event):
    start_raw = event.get('start')
    end_raw = event.get('end')
    if not isinstance(start_raw, str) or not isinstance(end_raw, str):
        return None, None
    try:
        return datetime.fromisoformat(start_raw), datetime.fromisoformat(end_raw)
    except ValueError:
        return None, None


def room_display_name(room_name):
    return room_name


def get_rooms_for_scope(scope):
    scope = (scope or 'A29').upper()
    all_codes = ('A21', 'A22', 'A29')

    if scope == 'ALL':
        all_rooms = []
        included = []
        missing = []
        for code in all_codes:
            building_rooms = ROOMS_BY_BUILDING.get(code, [])
            if building_rooms:
                all_rooms.extend(building_rooms)
                included.append(code)
            else:
                missing.append(code)
        return all_rooms, included, missing

    selected_rooms = ROOMS_BY_BUILDING.get(scope, A29_ROOMS)
    if selected_rooms:
        return selected_rooms, [scope], []
    return [], [], [scope]


def get_scope_label(scope):
    labels = {
        'A29': 'Bâtiment : A29',
        'A22': 'Bâtiment : A22',
        'A21': 'Bâtiment : A21',
        'ALL': 'Bâtiments : A21, A22, A29',
    }
    return labels.get(scope, 'Bâtiment : A29')


def get_scope_warning(missing_buildings):
    if not missing_buildings:
        return None
    if len(missing_buildings) == 1:
        return f"La liste des salles pour {missing_buildings[0]} n'est pas encore configurée."
    return f"Les listes des salles ne sont pas encore configurées pour : {', '.join(missing_buildings)}."


def is_room_available(events, check_time):
    if not events:
        return True
    for event in events:
        start, end = parse_event_bounds(event)
        if start is None or end is None:
            continue
        if start <= check_time <= end:
            return False
    return True


def get_next_event_today(events, check_time):
    if not events:
        return None
    check_date = check_time.date()
    future_events = []
    for event in events:
        start, _ = parse_event_bounds(event)
        if start is None:
            continue
        if start > check_time and start.date() == check_date:
            future_events.append((start, event))
    if not future_events:
        return None
    return min(future_events, key=lambda item: item[0])[1]


def get_available_duration(events, check_time):
    next_event = get_next_event_today(events, check_time)
    if not next_event:
        return float('inf')
    return (datetime.fromisoformat(next_event['start']) - check_time).total_seconds() / 60


def get_next_availability(events, check_time):
    if not events:
        return None
    check_date = check_time.date()
    
    current_end = None
    for event in events:
        start, end = parse_event_bounds(event)
        if start is None or end is None:
            continue
        if start <= check_time <= end:
            current_end = end
            break
    
    if not current_end or current_end.date() != check_date:
        return None
    
    future_events = []
    for event in events:
        start, _ = parse_event_bounds(event)
        if start is None:
            continue
        if start >= current_end and start.date() == check_date:
            future_events.append((start, event))
    
    if future_events:
        next_event_start, _ = min(future_events, key=lambda item: item[0])
        duration = (next_event_start - current_end).total_seconds() / 60
    else:
        duration = float('inf')
    
    return {'avail_time': current_end, 'duration': duration}


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/RC.png')
def logo():
    return send_from_directory(os.path.dirname(__file__), 'RC.png')


@app.route('/api/check', methods=['POST'])
def check_availability():
    data = request.json
    check_time = datetime.fromisoformat(data['time'])
    scope = str(data.get('building', 'A29')).upper()
    rooms_to_check, included_buildings, missing_buildings = get_rooms_for_scope(scope)
    if not rooms_to_check:
        return jsonify({
            'error': get_scope_warning(missing_buildings) or "Aucune salle configurée pour la sélection choisie."
        }), 400

    today = check_time.strftime("%Y-%m-%d")
    tomorrow = (check_time + timedelta(days=1)).strftime("%Y-%m-%d")
    room_schedules = get_room_schedules_parallel(rooms_to_check, today, tomorrow)
    
    available_rooms = []
    occupied_rooms = []
    
    for room in rooms_to_check:
        events = room_schedules.get(room)
        if events is None:
            continue
        
        if is_room_available(events, check_time):
            duration = get_available_duration(events, check_time)
            available_rooms.append({'room': room, 'events': events, 'duration': duration})
        else:
            next_avail = get_next_availability(events, check_time)
            if next_avail:
                occupied_rooms.append({
                    'room': room,
                    'avail_time': next_avail['avail_time'],
                    'duration': next_avail['duration']
                })
    
    # Sort
    available_rooms.sort(key=lambda x: (-x['duration'], x['room']))
    occupied_rooms.sort(key=lambda x: (x['avail_time'], -x['duration'], x['room']))
    
    # Format results
    result = {
        'check_time': check_time.strftime('%d/%m/%Y à %H:%M'),
        'scope_label': get_scope_label(scope),
        'warning': get_scope_warning(missing_buildings),
        'available': [],
        'next_available': [],
        'summary': f"{len(available_rooms)} disponibles, {len(occupied_rooms)} occupées ({len(rooms_to_check)} salles vérifiées)"
    }
    
    for item in available_rooms:
        next_event = get_next_event_today(item['events'], check_time)
        info = "Disponible pour le reste de la journée"
        if next_event:
            next_start, _ = parse_event_bounds(next_event)
            if next_start:
                info = f"Disponible jusqu'à {next_start.strftime('%H:%M')}"
        result['available'].append({'name': room_display_name(item['room']), 'info': info})
    
    if len(available_rooms) <= 2:
        for item in occupied_rooms[:2]:
            avail_time = item['avail_time']
            info = f"Disponible à partir de {avail_time.strftime('%H:%M')}"
            if item['duration'] != float('inf'):
                until = avail_time + timedelta(minutes=item['duration'])
                info += f" jusqu'à {until.strftime('%H:%M')}"
            else:
                info += " jusqu'à la fin de la journée"
            result['next_available'].append({'name': room_display_name(item['room']), 'info': info})
    
    return jsonify(result)


if __name__ == '__main__':
    # Get port from environment variable (for Render/Heroku) or use 5000 for local
    port = int(os.environ.get('PORT', 5000))
    
    print("\n" + "="*50)
    print("🏫 A29 RoomChecker Server")
    print("="*50)
    print("\n📱 Access on your phone:")
    print("   1. Connect to same WiFi as this computer")
    print(f"   2. Open: http://YOUR_LOCAL_IP:{port}")
    print("\n💻 Access on this computer:")
    print(f"   Open: http://localhost:{port}")
    print("\n" + "="*50 + "\n")
    
    # Run on all interfaces so it's accessible from phones on same network
    # Debug=False for production deployment
    app.run(host='0.0.0.0', port=port, debug=False)
