import logging
import requests
from livekit.agents import function_tool, RunContext
from dotenv import load_dotenv
import os
import requests

# Google Calendar imports
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pytz



load_dotenv()
@function_tool()
async def get_weather(context: RunContext, city: str) -> str:
    """Fetches the current weather for a given city using wttr.in API."""
    try:
        response = requests.get(f"http://wttr.in/{city}?format=3", timeout=5)
        if response.status_code == 200:
            result = response.text.strip()
            logging.info(f"Weather data fetched for {city}: {result}")
            return result
        else:
            logging.error(f"Failed to fetch weather for {city}: {response.status_code}")
            return f"Could not fetch weather for {city}."
    except Exception as e:
        logging.error(f"Error fetching weather for {city}: {e}")
        return f"An error occurred while fetching weather for {city}."

@function_tool()
async def web_search(context: RunContext, query: str) -> str:
    """Performs a simple web search using DuckDuckGo API."""
    url = "https://api.duckduckgo.com/"
    params = {
        "q": query,
        "format": "json",
        "no_html": 1,
        "skip_disambig": 1
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()

        results = []
        for topic in data.get("RelatedTopics", []):
            if "Text" in topic and "FirstURL" in topic:
                results.append(f"{topic['Text']} ({topic['FirstURL']})")
            elif "Topics" in topic:
                for sub in topic["Topics"]:
                    if "Text" in sub and "FirstURL" in sub:
                        results.append(f"{sub['Text']} ({sub['FirstURL']})")

        if not results:
            return f"No results found for '{query}'."

        return "\n".join(results[:5])  # return top 5 results
    except Exception as e:
        logging.error(f"Error performing web search for '{query}': {e}")
        return f"An error occurred while searching the web for '{query}'."


def get_calendar_events(service, days=1):
    """
    Fetches upcoming events from the user's Google Calendar.

    Parameters:
        service: Google Calendar API service object.
        days: Number of days from today to fetch events for (default: 1).

    Returns:
        List of (summary, start_time) tuples.
    """
    try:
        now = datetime.utcnow().isoformat() + "Z"  # current time in UTC
        end = (datetime.utcnow() + timedelta(days=days)).isoformat() + "Z"

        events_result = service.events().list(
            calendarId="primary",
            timeMin=now,
            timeMax=end,
            singleEvents=True,
            orderBy="startTime"
        ).execute()
        events = events_result.get("items", [])

        if not events:
            print("✅ No upcoming events found.")
            return []

        event_list = []
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            summary = event.get("summary", "No Title")

            # Format time if datetime
            if "T" in start:
                time_obj = datetime.fromisoformat(start.replace("Z", "+00:00"))
                local_time = time_obj.astimezone(pytz.timezone("Asia/Kolkata"))
                formatted_time = local_time.strftime("%I:%M %p %d-%b-%Y")
            else:
                formatted_time = "All Day"

            print(f"📅 {summary} at {formatted_time}")
            event_list.append((summary, formatted_time))

        return event_list

    except Exception as e:
        print(f"❌ Error fetching calendar events: {e}")
        return []
