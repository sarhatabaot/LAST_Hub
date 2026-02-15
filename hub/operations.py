CHECKLIST_ITEMS = [
    {
        "key": "safety_status_green",
        "label": "Safety status is green",
        "help": "Confirm the safety dashboard shows SAFE and all sensors are fresh.",
    },
    {
        "key": "weather_reviewed",
        "label": "Weather and forecast reviewed",
        "help": "Verify conditions are within operational limits for the session window.",
    },
    {
        "key": "systems_reachable",
        "label": "Core systems reachable",
        "help": "Confirm mounts, cameras, dome, and networking are responsive.",
    },
    {
        "key": "data_path_verified",
        "label": "Data path verified",
        "help": "Confirm storage and transfer paths are writable and monitored.",
    },
    {
        "key": "team_notified",
        "label": "Team notified",
        "help": "Operations channel and on-call engineer have been informed.",
    },
]


def default_checklist_state():
    return {item["key"]: False for item in CHECKLIST_ITEMS}


def normalize_checklist_state(current_state):
    normalized = dict(current_state or {})
    for item in CHECKLIST_ITEMS:
        normalized.setdefault(item["key"], False)
    return normalized


def build_checklist_items(current_state):
    normalized = normalize_checklist_state(current_state)
    items = []
    for item in CHECKLIST_ITEMS:
        items.append(
            {
                "key": item["key"],
                "label": item["label"],
                "help": item.get("help", ""),
                "checked": bool(normalized.get(item["key"])),
            }
        )
    return items, normalized
