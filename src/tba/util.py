from typing import Any
import requests
import datetime
from json import loads
from hashlib import sha256
import hmac
from django.conf import settings
from django.db import IntegrityError
from django.db.models import Q
import pytz
from django.utils import timezone

from scouting.models import (
    CompetitionLevel,
    Event,
    EventTeamInfo,
    Season,
    Team,
    Match,
)
import scouting.util
from tba.models import Message

tba_url = "https://www.thebluealliance.com/api/v3"


def get_events_for_team(
    team: Team, season: Season, event_cds_to_ignore: list[str] | None = None
) -> list[dict[str, Any]]:
    """
    Get all events for a team in a specific season from The Blue Alliance API.
    
    Args:
        team: The Team object to get events for
        season: The Season object to get events for
        event_cds_to_ignore: Optional list of event codes to skip
        
    Returns:
        List of dictionaries containing event data
    """

    request = requests.get(
        f"{tba_url}/team/frc{team.team_no}/events/{season.season}",
        headers={"X-TBA-Auth-Key": settings.TBA_KEY},
    )
    request = loads(request.text)

    parsed = []

    for event_requested in request:
        if (
            event_cds_to_ignore is None
            or event_requested["key"] not in event_cds_to_ignore
        ):
            data = get_tba_event(event_requested["key"])
            parsed.append(data)
        else:
            parsed.append({"event_cd": event_requested["key"]})

    return parsed


def get_matches_for_team_event(team_key: str, event_key: str) -> list[dict[str, Any]]:
    """
    Get all matches for a team at a specific event from The Blue Alliance API.
    
    Args:
        team_key: The team number (without 'frc' prefix)
        event_key: The event code
        
    Returns:
        List of match data dictionaries from TBA
    """
    request = requests.get(
        f"{tba_url}/team/frc{team_key}/event/{event_key}/matches",
        headers={"X-TBA-Auth-Key": settings.TBA_KEY},
    )
    matches = loads(request.text)
    # for match in matches:
    # print(match)

    return matches


def sync_season(season_id: int) -> str:
    """
    Synchronize all events for team 3492 in a specific season from The Blue Alliance.
    
    Args:
        season_id: The ID of the Season to synchronize
        
    Returns:
        Message string with sync results for each event
    """
    season = Season.objects.get(id=season_id)

    request = requests.get(
        f"{tba_url}/team/frc3492/events/{season.season}",
        headers={"X-TBA-Auth-Key": settings.TBA_KEY},
    )
    request = loads(request.text)

    messages = ""
    for event in request:
        messages += sync_event(season, event["key"])
        messages += "------------------------------------------------\n"

    return messages


def get_tba_event(event_cd: str) -> dict[str, Any]:
    """
    Fetch event details from The Blue Alliance API.
    
    Args:
        event_cd: The event code (e.g., '2024pahat')
        
    Returns:
        Dictionary containing parsed event data (event_nm, date_st, date_end, event_cd, time_zone)
        
    Raises:
        Exception: If TBA returns an error
    """
    request = requests.get(
        f"{tba_url}/event/{event_cd}",
        headers={"X-TBA-Auth-Key": settings.TBA_KEY},
    )
    tba_event = loads(request.text)

    if tba_event.get("Error", None) is not None:
        raise Exception(tba_event["Error"])

    time_zone = (
        tba_event.get("timezone")
        if tba_event.get("timezone", None) is not None
        else "America/New_York"
    )

    return {
        "event_nm": tba_event["name"],
        "date_st": datetime.datetime.strptime(
            tba_event["start_date"], "%Y-%m-%d"
        ).astimezone(pytz.timezone(time_zone)),
        "date_end": datetime.datetime.strptime(
            tba_event["end_date"], "%Y-%m-%d"
        ).astimezone(pytz.timezone(time_zone)),
        "event_cd": tba_event["key"],
        "event_url": tba_event.get("event_url", None),
        "gmaps_url": tba_event.get("gmaps_url", None),
        "address": tba_event.get("address", None),
        "city": tba_event.get("city", None),
        "state_prov": tba_event.get("state_prov", None),
        "postal_code": tba_event.get("postal_code", None),
        "location_name": tba_event.get("location_name", None),
        "timezone": tba_event.get("timezone", "America/New_York"),
        "webcast_url": (
            tba_event["webcasts"][0]["channel"]
            if len(tba_event["webcasts"]) > 0
            else ""
        ),
    }


def get_tba_event_teams(event_cd: str) -> list[dict[str, Any]]:
    """
    Get list of teams at an event from The Blue Alliance API.
    
    Args:
        event_cd: The event code (e.g., '2024pahat')
        
    Returns:
        List of dictionaries with team_no and team_nm fields
    """
    request = requests.get(
        f"{tba_url}/event/{event_cd}/teams",
        headers={"X-TBA-Auth-Key": settings.TBA_KEY},
    )
    tba_teams = loads(request.text)

    parsed = []

    for team in tba_teams:
        parsed.append({"team_no": team["team_number"], "team_nm": team["nickname"]})

    return parsed


def sync_event(season: Season, event_cd: str) -> str:
    """
    Synchronize an event and its teams from The Blue Alliance.
    
    Creates or updates the event and team records, linking teams to the event.
    Removes teams that are no longer at the event.
    
    Args:
        season: The Season object the event belongs to
        event_cd: The event code from TBA
        
    Returns:
        Message string detailing what was added, updated, or removed
    """
    data = get_tba_event(event_cd)
    data["teams"] = get_tba_event_teams(event_cd)

    messages = ""
    try:
        event = Event.objects.get(event_cd=data["event_cd"])
        event.void_ind = "n"
        event.date_st = data["date_st"]
        event.date_end = data["date_end"]

        messages += "(NO ADD) Already have event: " + data["event_cd"] + "\n"
    except Event.DoesNotExist:
        event = Event(
            season=season,
            event_cd=data["event_cd"],
            date_st=data["date_st"],
            date_end=data["date_end"],
            current="n",
            competition_page_active="n",
            void_ind="n",
        )

        event.save(force_insert=True)
        messages += "(ADD) Added event: " + data["event_cd"] + "\n"

    event.event_nm = data["event_nm"]
    event.event_url = data["event_url"]
    event.address = data["address"]
    event.city = data["city"]
    event.state_prov = data["state_prov"]
    event.postal_code = data["postal_code"]
    event.location_name = data["location_name"]
    event.gmaps_url = data["gmaps_url"]
    event.webcast_url = data["webcast_url"]
    event.timezone = data["timezone"]
    event.save()

    # remove teams that have been removed from an event
    teams = Team.objects.filter(
        ~Q(team_no__in=set(team["team_no"] for team in data["teams"])) & Q(event=event)
    )
    for team in teams:
        team.event_set.remove(event)
        messages += f"(REMOVE) Removed team: {team.team_no} {team.team_nm} from event: {data['event_cd']}\n"

    for team_ in data["teams"]:
        try:
            team = Team(
                team_no=team_["team_no"], team_nm=team_["team_nm"], void_ind="n"
            )
            team.save(force_insert=True)
            messages += f"(ADD) Added team: {team_['team_no']} {team_['team_nm']}\n"
        except IntegrityError:
            team = Team.objects.get(team_no=team_["team_no"])
            messages += (
                f"(NO ADD) Already have team: {team_['team_no']} {team_['team_nm']}\n"
            )

        try:  # TODO it doesn't throw an error, but re-linking many to many only keeps one entry in the table for the link
            team.event_set.add(event)
            messages += f"(LINK) Added team: {team_['team_no']} {team_['team_nm']} to event: {data['event_cd']}\n"
        except IntegrityError:
            messages += f"(NO LINK) Team: {team_['team_no']} {team_['team_nm']} already at event: {data['event_cd']}\n"

    return messages


def sync_matches(event: Event) -> str:
    """
    Synchronize all matches for an event from The Blue Alliance.
    
    Args:
        event: The Event object to sync matches for
        
    Returns:
        Message string detailing sync results
    """
    messages = ""
    request = requests.get(
        f"{tba_url}/event/{event.event_cd}/matches",
        headers={"X-TBA-Auth-Key": settings.TBA_KEY},
    )
    matches = loads(request.text)
    match_number = ""
    try:
        for match in matches:
            match_number = match.get("match_number", 0)
            messages += save_tba_match(match)
    except Exception as e:
        messages += f"(ERROR) {event.event_nm} {match_number} {e}\n"
    return messages


def get_tba_event_team_info(event_cd: str) -> list[dict[str, Any]]:
    """
    Get team ranking and performance info from The Blue Alliance.
    
    Args:
        event_cd: The event code to get rankings for
        
    Returns:
        List of dictionaries containing team stats including:
            - matches_played, qual_average, wins, losses, ties, rank, dq, team_id
    """
    request = requests.get(
        f"{tba_url}/event/{event_cd}/rankings",
        headers={"X-TBA-Auth-Key": settings.TBA_KEY},
    )
    rankings = loads(request.text)

    ret = []
    for info in rankings.get("rankings", []):
        ret.append(
            {
                "matches_played": info.get("matches_played", 0),
                "qual_average": info.get("qual_average", 0),
                "losses": (
                    info["record"].get("losses", 0)
                    if info.get("record", 0) is not None
                    else 0
                ),
                "wins": (
                    info["record"].get("wins", 0)
                    if info.get("record", 0) is not None
                    else 0
                ),
                "ties": (
                    info["record"].get("ties", 0)
                    if info.get("record", 0) is not None
                    else 0
                ),
                "rank": info.get("rank", 0),
                "dq": info.get("dq", 0),
                "team_id": replace_frc_in_str(info["team_key"]),
            }
        )

    return ret


def sync_event_team_info(force: int) -> str:
    """
    Synchronize team performance info for the current event.
    
    Only syncs if the event is currently active (between start and end dates)
    or if force is set to 1.
    
    Args:
        force: 1 to force sync regardless of event dates, 0 to only sync if event is active
        
    Returns:
        Message string describing what was synced
    """
    messages = ""
    event = Event.objects.get(current="y")

    sync_event(event.season, event.event_cd)

    now = datetime.datetime.combine(timezone.now(), datetime.time.min)
    date_st = datetime.datetime.combine(event.date_st, datetime.time.min)
    date_end = datetime.datetime.combine(event.date_end, datetime.time.min)

    # Only sync information if the event is active or forcing an update
    if force == 1 or date_st <= now <= date_end:
        for info in get_tba_event_team_info(event.event_cd):
            try:
                eti = EventTeamInfo.objects.get(
                    Q(event=event) & Q(team_id=info["team_id"]) & Q(void_ind="n")
                )
                messages += f"(UPDATE) {event.event_nm} {eti.team.team_no}\n"
            except EventTeamInfo.DoesNotExist:
                eti = EventTeamInfo(
                    event=event,
                    team_id=info["team_id"],
                )
                messages += f"(ADD) {event.event_nm} {eti.team.team_no}\n"

            eti.matches_played = info["matches_played"]
            eti.qual_average = info["qual_average"]
            eti.losses = info["losses"]
            eti.wins = info["wins"]
            eti.ties = info["ties"]
            eti.rank = info["rank"]
            eti.dq = info["dq"]

            eti.save()
    else:
        messages = "No active event"
    return messages


def save_tba_match(tba_match: dict[str, Any]) -> str:
    """
    Save or update a match from The Blue Alliance data.
    
    Args:
        tba_match: Dictionary of match data from TBA API containing:
                   - event_key, match_number, match_key, comp_level, time
                   - alliances with red/blue team_keys and scores
                   
    Returns:
        Message string indicating if match was added or updated
    """
    event = Event.objects.get(event_cd=tba_match["event_key"])
    messages = ""
    match_number = tba_match.get("match_number", 0)
    red_one = Team.objects.get(
        Q(team_no=replace_frc_in_str(tba_match["alliances"]["red"]["team_keys"][0]))
        & Q(void_ind="n")
    )
    red_two = Team.objects.get(
        Q(team_no=replace_frc_in_str(tba_match["alliances"]["red"]["team_keys"][1]))
        & Q(void_ind="n")
    )
    red_three = Team.objects.get(
        Q(team_no=replace_frc_in_str(tba_match["alliances"]["red"]["team_keys"][2]))
        & Q(void_ind="n")
    )
    blue_one = Team.objects.get(
        Q(team_no=replace_frc_in_str(tba_match["alliances"]["blue"]["team_keys"][0]))
        & Q(void_ind="n")
    )
    blue_two = Team.objects.get(
        Q(team_no=replace_frc_in_str(tba_match["alliances"]["blue"]["team_keys"][1]))
        & Q(void_ind="n")
    )
    blue_three = Team.objects.get(
        Q(team_no=replace_frc_in_str(tba_match["alliances"]["blue"]["team_keys"][2]))
        & Q(void_ind="n")
    )
    red_score = tba_match["alliances"]["red"].get("score", None)
    blue_score = tba_match["alliances"]["blue"].get("score", None)
    comp_level = CompetitionLevel.objects.get(
        Q(comp_lvl_typ=tba_match.get("comp_level", " ")) & Q(void_ind="n")
    )
    time = (
        datetime.datetime.fromtimestamp(
            tba_match["time"], pytz.timezone("America/New_York")
        )
        if tba_match["time"]
        else None
    )
    match_key = tba_match["key"]

    try:
        match = Match.objects.get(Q(match_key=match_key))

        match.red_one = red_one
        match.red_two = red_two
        match.red_three = red_three
        match.blue_one = blue_one
        match.blue_two = blue_two
        match.blue_three = blue_three
        match.red_score = red_score
        match.blue_score = blue_score
        match.comp_level = comp_level
        match.time = time
        match.void_ind = "n"

        match.save()
        messages += f"(UPDATE) {event.event_nm} {comp_level.comp_lvl_typ_nm} {match_number} {match_key}\n"
    except Match.DoesNotExist:
        match = Match(
            match_key=match_key,
            match_number=match_number,
            event=event,
            red_one=red_one,
            red_two=red_two,
            red_three=red_three,
            blue_one=blue_one,
            blue_two=blue_two,
            blue_three=blue_three,
            red_score=red_score,
            blue_score=blue_score,
            comp_level=comp_level,
            time=time,
            void_ind="n",
        )
        match.save()
        messages += f"(ADD) {event.event_nm} {comp_level.comp_lvl_typ_nm} {match_number} {match_key}\n"

    return messages


def save_message(message: dict[str, Any]) -> Message:
    """
    Save a TBA webhook message to the database.
    
    Args:
        message: Dictionary containing message_type and message_data
        
    Returns:
        The created Message object
    """
    msg = Message(
        message_type=message["message_type"],
        message_data=str(message["message_data"])[:4000],
    )
    msg.save()
    return msg


def verify_tba_webhook_call(request: Any) -> bool:
    """
    Verify that a webhook call is legitimately from The Blue Alliance.
    
    Uses HMAC-SHA256 to verify the request signature against the configured secret.
    
    Args:
        request: The HTTP request object with data and META attributes
        
    Returns:
        True if the webhook signature is valid, False otherwise
    """
    import json
    json_str = json.dumps(request.data, ensure_ascii=True)
    hmac_hex = hmac.new(
        settings.TBA_WEBHOOK_SECRET.encode("utf-8"), json_str.encode("utf-8"), sha256
    ).hexdigest()
    return hmac_hex == request.META.get("HTTP_X_TBA_HMAC", None)


def replace_frc_in_str(s: str) -> str:
    """
    Remove 'frc' prefix from team keys.
    
    Args:
        s: String that may contain 'frc' prefix (e.g., 'frc3492')
        
    Returns:
        String with 'frc' removed (e.g., '3492')
    """
    return s.replace("frc", "")
