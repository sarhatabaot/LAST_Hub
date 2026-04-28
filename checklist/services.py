from hub.models import OperationalChecklistState


CHECKLIST_GROUPS = [
    {
        "key": "safety",
        "title": "Readiness",
        "items": [
            {
                "key": "safety_status_green",
                "label": "Safety status is green",
                "help": "Confirm the safety dashboard shows SAFE and sensors are fresh.",
            },
            {
                "key": "weather_reviewed",
                "label": "Forecast reviewed",
                "help": "Verify conditions remain inside operating limits for the planned window.",
            },
            {
                "key": "systems_reachable",
                "label": "Core systems reachable",
                "help": "Mounts, cameras, enclosure, and network respond normally.",
            },
        ],
    },
    {
        "key": "session",
        "title": "Session Setup",
        "items": [
            {
                "key": "data_path_verified",
                "label": "Data path verified",
                "help": "Storage and transfer paths are writable and monitored.",
            },
            {
                "key": "team_notified",
                "label": "Team notified",
                "help": "Operations channel and on-call engineer have been informed.",
            },
        ],
    },
]


CHECKLIST_ITEMS = [item for group in CHECKLIST_GROUPS for item in group["items"]]


def default_checklist_state():
    return {item["key"]: False for item in CHECKLIST_ITEMS}


def normalize_checklist_state(current_state):
    normalized = dict(current_state or {})
    for item in CHECKLIST_ITEMS:
        normalized.setdefault(item["key"], False)
    return normalized


def build_checklist_groups(current_state):
    normalized = normalize_checklist_state(current_state)
    groups = []
    total_items = len(CHECKLIST_ITEMS)
    completed_items = 0

    for group in CHECKLIST_GROUPS:
        items = []
        complete_count = 0
        for item in group["items"]:
            checked = bool(normalized.get(item["key"]))
            if checked:
                complete_count += 1
                completed_items += 1
            items.append(
                {
                    "key": item["key"],
                    "label": item["label"],
                    "help": item.get("help", ""),
                    "checked": checked,
                }
            )
        groups.append(
            {
                "key": group["key"],
                "title": group["title"],
                "items": items,
                "complete_count": complete_count,
                "total_count": len(items),
            }
        )

    return groups, completed_items, total_items


def get_or_create_state():
    state, created = OperationalChecklistState.objects.get_or_create(
        pk=1,
        defaults={"items": default_checklist_state()},
    )
    if created:
        return state

    normalized = normalize_checklist_state(state.items)
    if normalized != state.items:
        state.items = normalized
        state.save(update_fields=["items", "updated_at"])
    return state


def get_or_create_state_for_update():
    try:
        state = OperationalChecklistState.objects.select_for_update().get(pk=1)
    except OperationalChecklistState.DoesNotExist:
        return OperationalChecklistState.objects.create(pk=1, items=default_checklist_state())

    normalized = normalize_checklist_state(state.items)
    if normalized != state.items:
        state.items = normalized
        state.save(update_fields=["items", "updated_at"])
    return state


def build_page_context():
    state = get_or_create_state()
    groups, completed_items, total_items = build_checklist_groups(state.items)
    return {
        "state": state,
        "state_label": state.state_label(),
        "checklist_groups": groups,
        "completed_items": completed_items,
        "total_items": total_items,
        "all_checked": completed_items == total_items,
    }


def get_dashboard_summary():
    state = get_or_create_state()
    _, completed_items, total_items = build_checklist_groups(state.items)
    return {
        "state": state,
        "completed_items": completed_items,
        "total_items": total_items,
        "all_checked": completed_items == total_items and total_items > 0,
    }
