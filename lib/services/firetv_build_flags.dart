/// Compile-time flags for the optional, unofficial Home Assistant Fire TV APK.
///
/// Defaults remain OFF to preserve all upstream functionality in any future
/// Windows, Android, or other platform build.
const bool kFireTvPlexOnly =
    bool.fromEnvironment('PLEZY_FIRETV_PLEX_ONLY', defaultValue: false);

/// Home Assistant already owns installation and version checks on these sticks.
const bool kHomeAssistantManagedUpdates =
    bool.fromEnvironment('PLEZY_HA_MANAGED_UPDATES', defaultValue: false);

/// Stage B: Fire TV video uses ExoPlayer regardless of saved backend preference.
/// MPV is STILL packaged for native fallback and music until later stages.
const bool kFireTvForceExoVideo =
    bool.fromEnvironment('PLEZY_FIRETV_FORCE_EXO_VIDEO', defaultValue: false);

/// Single shared choice for the Android video factory, setup and settings.
bool useExoPlayerForAndroidVideo(bool savedPreference) =>
    kFireTvForceExoVideo || savedPreference;

/// Dedicated Plex movies + TV build: do not show music libraries or controls.
const bool kFireTvMoviesTvOnly =
    bool.fromEnvironment('PLEZY_FIRETV_MOVIES_TV_ONLY', defaultValue: false);

/// Disable all external catalog integrations, requests and tracker syncing.
/// Does not affect local Plex library, on-deck, watched-state or HA links.
const bool kFireTvNoExternalServices =
    bool.fromEnvironment('PLEZY_FIRETV_NO_EXTERNAL_SERVICES', defaultValue: false);

/// This appliance excludes room sessions, relays and shared playback.
const bool kFireTvNoWatchTogether =
    bool.fromEnvironment('PLEZY_FIRETV_NO_WATCH_TOGETHER', defaultValue: false);

/// Exclude Plezy Remote host/client/pairing from Fire TV appliance.
/// Physical D-pad, media keys and Home Assistant URIs are unaffected.
const bool kFireTvNoCompanionRemote =
    bool.fromEnvironment('PLEZY_FIRETV_NO_COMPANION_REMOTE', defaultValue: false);
