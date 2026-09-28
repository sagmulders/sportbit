#!/usr/bin/env python3
"""
SportBit API Client - Read-only client to authenticate, retrieve workout schedule, and view event details.
Credentials via environment variables: SPORTBIT_USER, SPORTBIT_PASS
"""

import os
import sys
import json
import argparse
import requests
from urllib.parse import urljoin
from datetime import datetime, timedelta

try:
    from google_drive_uploader import GoogleDriveUploader
    DRIVE_AVAILABLE = True
except ImportError:
    DRIVE_AVAILABLE = False


class SportBitClient:
    """Client for SportBit API with session and XSRF token management."""

    def __init__(self, base_url, email, password):
        self.base_url = base_url
        self.email = email
        self.password = password
        self.session = requests.Session()
        self.xsrf_token = None

    def heartbeat(self):
        """
        Establish session and extract XSRF token.
        GET /cbm/api/data/heartbeat/
        """
        url = urljoin(self.base_url, "/cbm/api/data/heartbeat/")
        params = {"taalIso": "nl"}
        response = self.session.get(url, params=params)
        response.raise_for_status()

        data = response.json()

        # XSRF token is typically in cookies (Angular pattern)
        # Look for common cookie names
        token_cookie_names = ["XSRF-TOKEN", "xsrf-token", "_csrf", "X-XSRF-TOKEN"]
        for cookie_name in token_cookie_names:
            if cookie_name in self.session.cookies:
                self.xsrf_token = self.session.cookies[cookie_name]
                break

        if not self.xsrf_token:
            raise ValueError("Could not extract XSRF token from cookies")

        return data

    def login(self):
        """
        Authenticate with email and password.
        POST /cbm/api/data/inloggen/
        """
        url = urljoin(self.base_url, "/cbm/api/data/inloggen/")
        headers = {"X-XSRF-TOKEN": self.xsrf_token} if self.xsrf_token else {}

        payload = {
            "username": self.email,
            "password": self.password,
            "remember": False,
        }

        response = self.session.post(url, json=payload, headers=headers)
        response.raise_for_status()

        return response.json()

    def get_rooster(self):
        """
        Fetch the schedule (rooster).
        GET /cbm/api/web/rooster/
        """
        url = urljoin(self.base_url, "/cbm/api/web/rooster/")
        response = self.session.get(url)
        response.raise_for_status()

        return response.json()

    def get_events(self, date_str):
        """
        Fetch events for a specific date.
        GET /cbm/api/data/events/?datum=YYYY-MM-DD
        """
        url = urljoin(self.base_url, "/cbm/api/data/events/")
        params = {"datum": date_str}
        response = self.session.get(url, params=params)
        response.raise_for_status()

        return response.json()

    def get_event_details(self, event_id):
        """
        Fetch event details including workout description.
        GET /cbm/api/web/event/{event_id}/
        """
        url = urljoin(self.base_url, f"/cbm/api/web/event/{event_id}/")
        response = self.session.get(url)
        response.raise_for_status()

        return response.json()


def main():
    parser = argparse.ArgumentParser(
        description="SportBit API Client - retrieve schedule and workout descriptions"
    )
    parser.add_argument(
        "--date",
        type=str,
        help="Date to search for events (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--event-id",
        type=int,
        help="Specific event ID to fetch details for",
    )
    parser.add_argument(
        "--save-to-drive",
        action="store_true",
        help="Save workout JSONs to Google Drive (requires --date and GOOGLE_DRIVE_FOLDER_ID env var)",
    )
    args = parser.parse_args()

    email = os.getenv("SPORTBIT_USER")
    password = os.getenv("SPORTBIT_PASS")

    if not email or not password:
        print(
            "Error: SPORTBIT_USER and SPORTBIT_PASS environment variables must be set",
            file=sys.stderr,
        )
        sys.exit(1)

    base_url = "https://duketown.sportbitapp.nl"

    try:
        client = SportBitClient(base_url, email, password)

        print("Establishing session and getting XSRF token...", file=sys.stderr)
        client.heartbeat()

        print("Logging in...", file=sys.stderr)
        client.login()

        if args.event_id:
            print(f"Fetching event {args.event_id} details...", file=sys.stderr)
            event_details = client.get_event_details(args.event_id)
            print("\n" + "=" * 80)
            print(f"EVENT {args.event_id} DETAILS:")
            print("=" * 80)
            print(json.dumps(event_details, indent=2, ensure_ascii=False))

        elif args.date:
            if args.save_to_drive and not DRIVE_AVAILABLE:
                print(
                    "Error: Google Drive dependencies not installed. Run: pip install -r requirements.txt",
                    file=sys.stderr,
                )
                sys.exit(1)

            target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
            date_str = target_date.strftime("%Y-%m-%d")

            print(f"Fetching events for {date_str}...", file=sys.stderr)
            events_response = client.get_events(date_str)

            signed_up_events = []

            for category in ["ochtend", "middag", "avond"]:
                if category in events_response:
                    event_list = events_response[category]
                    if isinstance(event_list, list):
                        for event in event_list:
                            if event.get("aangemeld"):
                                signed_up_events.append(event)

            if not signed_up_events:
                print(
                    f"No signed-up events found on {date_str}",
                    file=sys.stderr,
                )
                sys.exit(0)

            print(
                f"Found {len(signed_up_events)} signed-up event(s)",
                file=sys.stderr,
            )

            for i, event in enumerate(signed_up_events, 1):
                event_id = event.get("id")
                titel = event.get("titel", "Unknown")
                start = event.get("start", "Unknown")

                print(f"[{i}] (ID: {event_id}) {titel} - {start}", file=sys.stderr)

            selected_event = signed_up_events[0]
            event_id = selected_event["id"]
            titel = selected_event["titel"]
            start = selected_event.get("start", "Unknown")
            trainer = selected_event.get("trainer", {}).get("naam", "Unknown")

            print(f"\nFetching details for: {titel}...", file=sys.stderr)
            event_details = client.get_event_details(event_id)

            print("\n" + "=" * 80)
            print(f"EVENT: {titel}")
            print(f"Date: {start}")
            print(f"Trainer: {trainer}")
            print("=" * 80 + "\n")

            if "workouts" in event_details and event_details["workouts"]:
                for workout in event_details["workouts"]:
                    naam = workout.get("naam", "")
                    handelingen = workout.get("handelingen", "")

                    if naam:
                        print(f"## {naam}")
                    if handelingen:
                        print(handelingen)
                    print()
            elif "beschrijving" in event_details:
                print(event_details["beschrijving"])
            elif "description" in event_details:
                print(event_details["description"])
            else:
                print(json.dumps(event_details, indent=2, ensure_ascii=False))

            if args.save_to_drive:
                folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
                if not folder_id:
                    print(
                        "Error: GOOGLE_DRIVE_FOLDER_ID environment variable not set",
                        file=sys.stderr,
                    )
                    sys.exit(1)

                print("\nSaving workouts to Google Drive...", file=sys.stderr)

                try:
                    uploader = GoogleDriveUploader(folder_id)

                    event_date = target_date.strftime("%Y-%m-%d")
                    filename = f"{event_date}-{event_id}.json"

                    if uploader.file_exists(filename):
                        print(f"File already exists, skipping: {filename}", file=sys.stderr)
                    else:
                        workouts = event_details.get("workouts", [])
                        file_id = uploader.upload_workout_json(filename, workouts)
                        print(
                            f"Successfully uploaded: {filename} (ID: {file_id})",
                            file=sys.stderr,
                        )

                except ValueError as e:
                    print(f"Error saving to Drive: {e}", file=sys.stderr)
                    sys.exit(1)

        else:
            print("Fetching schedule (rooster)...", file=sys.stderr)
            schedule = client.get_rooster()

            print("\n" + "=" * 80, file=sys.stderr)
            print("SCHEDULE (ROOSTER):", file=sys.stderr)
            print("=" * 80, file=sys.stderr)
            print(json.dumps(schedule, indent=2, ensure_ascii=False))

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
