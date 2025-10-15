#!/usr/bin/env python3
"""
CELCAT Room Availability Checker for Building A29
Checks which rooms and amphitheatres in building A29 are currently available
"""

import requests
from datetime import datetime, timedelta
import sys

# CELCAT API endpoint
API_URL = "https://celcat.u-bordeaux.fr/Calendar/Home/GetCalendarData"

# All A29 rooms and amphitheatres
A29_ROOMS = [
    "A29/ Amphithéâtre A",
    "A29/ Amphithéâtre B",
    "A29/ Amphithéâtre C",
    "A29/ Amphithéâtre D",
    "A29/ Amphithéâtre E",
    "A29/ Amphithéâtre F",
    "A29/ Amphithéâtre G",
    "A29/ Salle 001",
    "A29/ Salle 101",
    "A29/ Salle 102",
    "A29/ Salle 103",
    "A29/ Salle 104",
    "A29/ Salle 105",
    "A29/ Salle 106",
    "A29/ Salle 107",
]


def get_room_schedule(room_name, start_date, end_date):
    """
    Fetch the schedule for a specific room from CELCAT API

    Args:
        room_name: Name of the room (e.g., "A29/ Amphithéâtre A")
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        List of events for the room, or None if request fails
    """
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
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data for {room_name}: {e}", file=sys.stderr)
        return None


def is_room_available_now(events, current_time):
    """
    Check if a room is currently available based on its events

    Args:
        events: List of event dictionaries from API
        current_time: Current datetime object

    Returns:
        True if room is available, False if occupied
    """
    if not events:
        return True

    for event in events:
        start = datetime.fromisoformat(event['start'])
        end = datetime.fromisoformat(event['end'])

        if start <= current_time <= end:
            return False

    return True


def get_next_event(events, current_time):
    """
    Get the next upcoming event for a room (only today)

    Args:
        events: List of event dictionaries from API
        current_time: Current datetime object

    Returns:
        Next event dict or None if no upcoming events today
    """
    if not events:
        return None

    current_date = current_time.date()
    future_events = []

    for event in events:
        start = datetime.fromisoformat(event['start'])
        # Only include events that are today and in the future
        if start > current_time and start.date() == current_date:
            future_events.append(event)

    if not future_events:
        return None

    # Return the soonest event
    return min(future_events, key=lambda e: datetime.fromisoformat(e['start']))


def get_available_duration(events, current_time):
    """
    Calculate how long a room will be available (in minutes)

    Args:
        events: List of event dictionaries from API
        current_time: Current datetime object

    Returns:
        Duration in minutes until next event, or float('inf') if available rest of day
    """
    next_event = get_next_event(events, current_time)
    if next_event:
        next_start = datetime.fromisoformat(next_event['start'])
        duration = (next_start - current_time).total_seconds() / 60
        return duration
    return float('inf')


def get_next_availability(events, current_time):
    """
    Get when an occupied room will next become available today

    Args:
        events: List of event dictionaries from API
        current_time: Current datetime object

    Returns:
        Tuple of (available_time, duration_available) or None if not available today
    """
    current_date = current_time.date()

    # Find current event
    current_event_end = None
    for event in events:
        start = datetime.fromisoformat(event['start'])
        end = datetime.fromisoformat(event['end'])
        if start <= current_time <= end:
            current_event_end = end
            break

    if not current_event_end or current_event_end.date() != current_date:
        return None

    # Find the next event after current one ends (if any)
    next_event_after = None
    for event in events:
        start = datetime.fromisoformat(event['start'])
        if start >= current_event_end and start.date() == current_date:
            if next_event_after is None or start < datetime.fromisoformat(next_event_after['start']):
                next_event_after = event

    # Calculate duration available
    if next_event_after:
        next_start = datetime.fromisoformat(next_event_after['start'])
        duration = (next_start - current_event_end).total_seconds() / 60
    else:
        duration = float('inf')

    return (current_event_end, duration)


def check_all_rooms():
    """
    Check availability of all A29 rooms and display results
    """
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"Checking room availability for {now.strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    available_rooms = []
    occupied_rooms = []

    for room in A29_ROOMS:
        events = get_room_schedule(room, today, tomorrow)

        if events is None:
            print(f"⚠️  {room}: Could not fetch data")
            continue

        is_available = is_room_available_now(events, now)

        if is_available:
            duration = get_available_duration(events, now)
            available_rooms.append((room, events, duration))
        else:
            next_avail = get_next_availability(events, now)
            if next_avail:
                occupied_rooms.append((room, events, next_avail[0], next_avail[1]))

    # Sort available rooms by duration (longest first)
    available_rooms.sort(key=lambda x: (-x[2], x[0]))

    # Display available rooms
    print("\n✅ AVAILABLE ROOMS:")
    print("-" * 70)
    if available_rooms:
        for room, events, duration in available_rooms:
            next_event = get_next_event(events, now)
            if next_event:
                next_start = datetime.fromisoformat(next_event['start'])
                print(f"  {room}")
                print(f"    Available until: {next_start.strftime('%H:%M')}")
            else:
                print(f"  {room}")
                print(f"    Available for the rest of the day")
            print()
    else:
        print("  No rooms currently available")

    # If 2 or fewer available, show next 2 to become available
    if len(available_rooms) <= 2 and occupied_rooms:
        # Sort occupied rooms by: when they become available (soonest first),
        # then by duration (longest first), then alphabetically
        occupied_rooms.sort(key=lambda x: (x[2], -x[3], x[0]))

        print("\n🕒 NEXT ROOMS TO BECOME AVAILABLE:")
        print("-" * 70)
        for i, (room, events, avail_time, duration) in enumerate(occupied_rooms[:2]):
            print(f"  {room}")
            print(f"    Available from: {avail_time.strftime('%H:%M')}")
            if duration == float('inf'):
                print(f"    Available until: End of day")
            else:
                until_time = avail_time + timedelta(minutes=duration)
                print(f"    Available until: {until_time.strftime('%H:%M')}")
            print()

    # Summary
    print("\n" + "=" * 70)
    print(f"Summary: {len(available_rooms)} available, {len(occupied_rooms)} occupied")


if __name__ == "__main__":
    try:
        check_all_rooms()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        sys.exit(1)