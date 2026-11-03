"""PowerLink configuration and limits shared by the Home Assistant integration."""

DOMAIN = "powerlink"
CONF_DEVICES = "devices"
CONF_PLEX_SERVERS = "plex_servers"
CONF_DEVICE_ID = "device_id"
CONF_MEDIA_PLAYER = "media_player"
CONF_WAKE_SCRIPT = "wake_script"
CONF_LAUNCH_SCRIPT = "launch_script"
CONF_WAKE_MODE = "wake_mode"
CONF_WARMUP = "warmup_seconds"
CONF_MAX_HEIGHT = "max_height"
CONF_LAUNCH_METHOD = "launch_method"
MAX_SNAPSHOT_BYTES = 512 * 1024
MAX_QUEUE_LENGTH = 5000
MAX_TRANSFER_WINDOW = 50
SESSION_MAX_AGE_SECONDS = 45
TRANSFER_TTL_SECONDS = 3600
APP_PACKAGE = "com.power.powerplay"
