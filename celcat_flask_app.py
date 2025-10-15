#!/usr/bin/env python3
"""
Flask web server for A29 Room Availability Checker
Run this on your computer/phone and access via browser
"""

from flask import Flask, render_template_string, jsonify, request
import requests
from datetime import datetime, timedelta

app = Flask(__name__)

API_URL = "https://celcat.u-bordeaux.fr/Calendar/Home/GetCalendarData"

A29_ROOMS = [
    "A29/ Amphithéâtre A", "A29/ Amphithéâtre B", "A29/ Amphithéâtre C",
    "A29/ Amphithéâtre D", "A29/ Amphithéâtre E", "A29/ Amphithéâtre F",
    "A29/ Amphithéâtre G", "A29/ Salle 001", "A29/ Salle 101",
    "A29/ Salle 102", "A29/ Salle 103", "A29/ Salle 104",
    "A29/ Salle 105", "A29/ Salle 106", "A29/ Salle 107",
]

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>A29 Room Checker</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 800px; margin: 0 auto; }
        .header {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 20px;
            text-align: center;
        }
        h1 { color: #333; font-size: 28px; margin-bottom: 10px; }
        .subtitle { color: #666; font-size: 14px; }
        .controls {
            background: white;
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 20px;
        }
        .time-selector { display: flex; gap: 10px; margin-bottom: 15px; flex-wrap: wrap; }
        input[type="datetime-local"] {
            flex: 1;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 16px;
            min-width: 200px;
        }
        button {
            padding: 12px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }
        button:hover { transform: translateY(-2px); }
        button:disabled { opacity: 0.6; cursor: not-allowed; }
        .loading {
            background: white;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            text-align: center;
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        .results {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .section-title {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 15px;
            color: #333;
        }
        .room-card {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 12px;
            border-left: 4px solid #667eea;
        }
        .room-name { font-weight: 600; color: #333; font-size: 16px; }
        .room-info { color: #666; font-size: 14px; margin-top: 5px; }
        .next-available-section {
            margin-top: 25px;
            padding-top: 25px;
            border-top: 2px solid #e0e0e0;
        }
        .next-available-card { border-left-color: #ffa726; }
        .summary {
            margin-top: 20px;
            padding: 15px;
            background: #f0f4ff;
            border-radius: 10px;
            text-align: center;
            font-weight: 600;
            color: #667eea;
        }
        .no-rooms { text-align: center; color: #999; padding: 30px; }
        @media (max-width: 600px) {
            .time-selector { flex-direction: column; }
            input[type="datetime-local"], button { width: 100%; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏫 A29 Room Availability</h1>
            <p class="subtitle">Université de Bordeaux - Building A29</p>
        </div>
        <div class="controls">
            <div class="time-selector">
                <input type="datetime-local" id="timeInput" />
                <button onclick="checkAvailability()" id="checkBtn">Check</button>
            </div>
            <button onclick="checkNow()" style="width: 100%; margin-top: 10px;">Check Now</button>
        </div>
        <div id="loading" class="loading" style="display: none;">
            <div class="spinner"></div>
            <p>Checking rooms...</p>
        </div>
        <div id="results" style="display: none;"></div>
    </div>
    <script>
        function setDefaultTime() {
            const now = new Date();
            now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
            document.getElementById('timeInput').value = now.toISOString().slice(0, 16);
        }
        
        async function checkNow() {
            setDefaultTime();
            await checkAvailability();
        }
        
        async function checkAvailability() {
            const timeInput = document.getElementById('timeInput').value;
            if (!timeInput) { alert('Select a time'); return; }
            
            document.getElementById('loading').style.display = 'block';
            document.getElementById('results').style.display = 'none';
            document.getElementById('checkBtn').disabled = true;
            
            try {
                const response = await fetch('/api/check', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ time: timeInput })
                });
                
                const data = await response.json();
                displayResults(data);
            } catch (error) {
                alert('Error checking availability');
                console.error(error);
            }
            
            document.getElementById('loading').style.display = 'none';
            document.getElementById('results').style.display = 'block';
            document.getElementById('checkBtn').disabled = false;
        }
        
        function displayResults(data) {
            let html = `<div class="results">
                <p style="text-align: center; color: #666; margin-bottom: 20px;">
                    ${data.check_time}
                </p>
                <div class="section-title">✅ Available Rooms</div>`;
            
            if (data.available.length > 0) {
                data.available.forEach(room => {
                    html += `<div class="room-card">
                        <div class="room-name">${room.name}</div>
                        <div class="room-info">${room.info}</div>
                    </div>`;
                });
            } else {
                html += '<div class="no-rooms">No rooms available</div>';
            }
            
            if (data.next_available.length > 0) {
                html += '<div class="next-available-section"><div class="section-title">🕒 Next Available</div>';
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
        
        window.onload = setDefaultTime;
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
        response = requests.post(API_URL, data=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except:
        return None


def is_room_available(events, check_time):
    if not events:
        return True
    for event in events:
        start = datetime.fromisoformat(event['start'])
        end = datetime.fromisoformat(event['end'])
        if start <= check_time <= end:
            return False
    return True


def get_next_event_today(events, check_time):
    if not events:
        return None
    check_date = check_time.date()
    future = [e for e in events if datetime.fromisoformat(e['start']) > check_time 
              and datetime.fromisoformat(e['start']).date() == check_date]
    return min(future, key=lambda e: datetime.fromisoformat(e['start'])) if future else None


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
        start = datetime.fromisoformat(event['start'])
        end = datetime.fromisoformat(event['end'])
        if start <= check_time <= end:
            current_end = end
            break
    
    if not current_end or current_end.date() != check_date:
        return None
    
    future = [e for e in events if datetime.fromisoformat(e['start']) >= current_end 
              and datetime.fromisoformat(e['start']).date() == check_date]
    
    if future:
        next_event = min(future, key=lambda e: datetime.fromisoformat(e['start']))
        duration = (datetime.fromisoformat(next_event['start']) - current_end).total_seconds() / 60
    else:
        duration = float('inf')
    
    return {'avail_time': current_end, 'duration': duration}


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/check', methods=['POST'])
def check_availability():
    data = request.json
    check_time = datetime.fromisoformat(data['time'])
    today = check_time.strftime("%Y-%m-%d")
    tomorrow = (check_time + timedelta(days=1)).strftime("%Y-%m-%d")
    
    available_rooms = []
    occupied_rooms = []
    
    for room in A29_ROOMS:
        events = get_room_schedule(room, today, tomorrow)
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
        'check_time': check_time.strftime('%A, %B %d, %Y at %H:%M'),
        'available': [],
        'next_available': [],
        'summary': f"{len(available_rooms)} available, {len(occupied_rooms)} occupied"
    }
    
    for item in available_rooms:
        next_event = get_next_event_today(item['events'], check_time)
        info = "Available for rest of day"
        if next_event:
            next_start = datetime.fromisoformat(next_event['start'])
            info = f"Available until {next_start.strftime('%H:%M')}"
        result['available'].append({'name': item['room'], 'info': info})
    
    if len(available_rooms) <= 2:
        for item in occupied_rooms[:2]:
            avail_time = item['avail_time']
            info = f"Available from {avail_time.strftime('%H:%M')}"
            if item['duration'] != float('inf'):
                until = avail_time + timedelta(minutes=item['duration'])
                info += f" until {until.strftime('%H:%M')}"
            else:
                info += " until end of day"
            result['next_available'].append({'name': item['room'], 'info': info})
    
    return jsonify(result)


if __name__ == '__main__':
    print("\n" + "="*50)
    print("🏫 A29 Room Checker Server")
    print("="*50)
    print("\n📱 Access on your phone:")
    print("   1. Connect to same WiFi as this computer")
    print("   2. Open: http://YOUR_LOCAL_IP:5000")
    print("\n💻 Access on this computer:")
    print("   Open: http://localhost:5000")
    print("\n" + "="*50 + "\n")
    
    # Run on all interfaces so it's accessible from phones on same network
    app.run(host='0.0.0.0', port=5000, debug=True)
