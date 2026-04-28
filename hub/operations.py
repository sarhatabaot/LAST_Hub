from hub.models import MountConfiguration

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


def get_mount_configurations():
    """Get all mount configurations, creating defaults if they don't exist."""
    from hub.models import MountConfiguration
    import json
    from pathlib import Path
    from django.conf import settings
    
    BASE_DIR = Path(__file__).resolve().parent
    mounts_path = BASE_DIR / "data" / "mounts.json"
    
    # Try to load default configurations from JSON file
    default_configs = []
    if mounts_path.exists():
        try:
            with open(mounts_path, 'r') as f:
                default_configs = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    
    # Ensure all mount configurations exist and are up to date
    for config_data in default_configs:
        mount_config, created = MountConfiguration.objects.get_or_create(
            mount_id=config_data['mount_id'],
            defaults={
                'enabled': config_data['enabled'],
                'reason': config_data['reason']
            }
        )
        
        # If the configuration already exists, update it to match the defaults
        if not created:
            if (mount_config.enabled != config_data['enabled'] or 
                mount_config.reason != config_data['reason']):
                mount_config.enabled = config_data['enabled']
                mount_config.reason = config_data['reason']
                mount_config.save()
    
    # Return all configurations ordered by the order they appear in mounts.json
    mount_order = get_mount_order()
    if mount_order:
        # Create a case-insensitive mapping for ordering
        mount_order_map = {mount_id.upper(): index for index, mount_id in enumerate(mount_order)}
        
        # Get all configurations and sort them according to the JSON order
        all_configs = list(MountConfiguration.objects.all())
        all_configs.sort(key=lambda config: mount_order_map.get(config.mount_id.upper(), 999))
        return all_configs
    else:
        # Fallback to alphabetical ordering if JSON is unavailable
        return MountConfiguration.objects.all().order_by('mount_id')


def get_enabled_mounts():
    """Get list of enabled mounts ordered by mounts.json."""
    mount_order = get_mount_order()
    if mount_order:
        # Create a case-insensitive mapping for ordering
        mount_order_map = {mount_id.upper(): index for index, mount_id in enumerate(mount_order)}
        
        # Get enabled configurations and sort them according to the JSON order
        enabled_configs = list(MountConfiguration.objects.filter(enabled=True))
        enabled_configs.sort(key=lambda config: mount_order_map.get(config.mount_id.upper(), 999))
        return enabled_configs
    else:
        # Fallback to alphabetical ordering if JSON is unavailable
        return MountConfiguration.objects.filter(enabled=True).order_by('mount_id')


def get_disabled_mounts():
    """Get list of disabled mounts with their reasons ordered by mounts.json."""
    mount_order = get_mount_order()
    if mount_order:
        # Create a case-insensitive mapping for ordering
        mount_order_map = {mount_id.upper(): index for index, mount_id in enumerate(mount_order)}
        
        # Get disabled configurations and sort them according to the JSON order
        disabled_configs = list(MountConfiguration.objects.filter(enabled=False))
        disabled_configs.sort(key=lambda config: mount_order_map.get(config.mount_id.upper(), 999))
        return disabled_configs
    else:
        # Fallback to alphabetical ordering if JSON is unavailable
        return MountConfiguration.objects.filter(enabled=False).order_by('mount_id')


def get_mount_order():
    """Get the mount display order from mounts.json file."""
    import json
    from pathlib import Path
    
    BASE_DIR = Path(__file__).resolve().parent
    mounts_path = BASE_DIR / "data" / "mounts.json"
    
    try:
        with open(mounts_path, 'r') as f:
            mounts_data = json.load(f)
            # Extract mount IDs in the order they appear in the JSON file
            return [mount['mount_id'] for mount in mounts_data]
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        # Fallback to even numbers first, then odd numbers if JSON is unavailable
        return ['M02', 'M04', 'M06', 'M08', 'M10', 'M12', 'M01', 'M03', 'M05', 'M07', 'M09', 'M11']
