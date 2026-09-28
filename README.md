# SportBit Client

A simple Python CLI client for the SportBit API. Read-only access to view schedules, event details, and workout descriptions.

## Setup

### Requirements
- Python 3.6+
- `requests` library

### Installation

```bash
python3 -m pip install -r requirements.txt
```

Or install directly:
```bash
python3 -m pip install requests
```

### Authentication

Set your credentials as environment variables:

```bash
export SPORTBIT_USER="your-email@example.com"
export SPORTBIT_PASS="your-password"
```

## Usage

### View today's schedule
```bash
python3 sportbit_client.py
```

### Search for signed-up events by date
```bash
python3 sportbit_client.py --date 2026-09-22
```
Shows all events you're signed up for on that date, including event IDs and workout descriptions.

### Get event details
```bash
python3 sportbit_client.py --event-id 84745
```
Displays full event details including workout breakdowns, trainer info, capacity, and location.

### Save workouts to local directory
```bash
python3 sportbit_client.py --date 2026-09-22 --save ./workouts
```
Fetches signed-up events for the date and saves the workout JSONs to a local directory. Files are named `YYYY-MM-DD-{EventID}.json` and contain only the workouts array. Files are not overwritten if they already exist.

## Features

- **Schedule**: View all available classes organized by time of day
- **Event Search**: Find events you've signed up for by date
- **Workout Details**: See complete workout descriptions with exercises, scaling options, and strategy notes
- **Save to File**: Optionally save workout JSONs to a local directory
- **Read-Only**: No modifications to your account or registrations

## API Endpoints Used

- `GET /cbm/api/data/heartbeat/` - Session establishment
- `POST /cbm/api/data/inloggen/` - Authentication
- `GET /cbm/api/web/rooster/` - Schedule
- `GET /cbm/api/data/events/?datum=YYYY-MM-DD` - Events by date
- `GET /cbm/api/web/event/{id}/` - Event details
