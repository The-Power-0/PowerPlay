# PowerLink

**A Home Assistant-side companion for PowerPlay 1.3.0**, staged in a separate branch of [The-Power-0/PowerPlay](https://github.com/The-Power-0/PowerPlay) before moving to its own **The-Power-0/PowerLink** repository.

> **Development preview.** This is *not* yet a published HACS integration. Current stable PowerPlay 1.2.4 does **not** implement the PowerLink v1 receiver, so complete queue transfers cannot work until the PowerPlay 1.3.0 app-side implementation is tested. Handoff launching is disabled for unverified clients by default. The \`open_device\` action, discovery and policy planner can be tested independently.

## What PowerLink does

- **No LAN scans or competing ADB sessions.** It discovers existing Home Assistant Android Debug Bridge \`media_player\` entities and lets an administrator register them. It delegates ADB to Home Assistant's existing Android Debug Bridge integration.
- **Device policies, not room names.** Configurable \`max_height\`, preference for highest quality, launch method (HA Android TV ADB or custom HA script), and per-device wake-up sequences.
- **Exact queue continuity.** PowerPlay will export an ordered snapshot of the current **Plex** queue, its shuffled flag, cursor and exact playback offset. PowerLink retains every entry and duplicate in order. It does **not** reshuffle or rebuild a guessed queue.
- **1080p and 4K matching.** For every requested queue window, PowerLink selects a copy whose verified resolution fits the destination. 4K-capable targets can choose a true 2160p copy; Full HD targets never receive a known UHD-only copy. Media identity is checked by Plex GUID or other high-confidence identifiers, not title alone.
- **Server-side, lazy matching.** Queue windows of up to 32 entries are resolved **only on demand** with a maximum of 3 Plex queries in flight and a bounded 10-minute catalog cache. No idle traffic, full-library indexing or large payloads sent to the Fire Stick.
- **Different homes/networks.** The Home Assistant controller's API URL can be a reachable private LAN URL or a TLS-protected external/VPN URL. Device wake/app launch can use the local ADB integration or a custom Home Assistant script/bridge on a different network. This is *routed connectivity*, not automatic internet tunneling.
- **Safe handoff.** The current source is never stopped merely because the destination woke or accepted an Android intent. A receiver must acknowledge successful playback. A short-lived 256-bit secret grants access only to one handoff manifest, not HA/Plex credentials.

## Installation (after separate repository and first supported PowerPlay release)

Copy \`custom_components/powerlink\` into the Home Assistant \`/config/custom_components/\` directory or install the future PowerLink repository as a HACS **Integration**. This is compatible with Home Assistant Container; it does not require Supervisor or an add-on store. Restart Home Assistant, then add **PowerLink** under Settings > Devices & Services.

In setup, provide a **Home Assistant base URL reachable by the Fire Sticks** (e.g. \`http://10.0.0.10:8123\` on your LAN or \`https://home.example.net\` across networks). Optional Plex URL/token enable Home Assistant-side targeted equivalent lookup, which is the preferred way to map your distinct \`Movies [4K]\` and \`TV Shows [4K]\` libraries.

### Example device policies (your three Fire Sticks)

This is an example only. The integration **does not** hard-code names, addresses, model-to-room mappings or an assumed local subnet.

| Existing Home Assistant entity | Preferred max | Launch | Quality policy |
| --- | ---: | --- | --- |
| \`media_player.living_room_fire_tv_stick_4k_plus\` | 2160p | ADB or custom script | Prefer highest available 4K copy |
| \`media_player.bedroom_fire_tv_stick_lite\` | 1080p | ADB or custom script | Match HD version |
| \`media_player.game_room_fire_tv_stick_lite\` | 1080p | ADB or custom script | Match HD version |

Discover candidates with \`powerlink.discover_devices\`. Register one device at a time using \`powerlink.register_device\`:

~~~yaml
action: powerlink.register_device
data:
  entity_id: media_player.living_room_fire_tv_stick_4k_plus
  name: Living Room
  max_height: 2160
  prefer_highest_quality: true
  launch_method: adb
  # Initially false. Set only after PowerPlay 1.3.0 receiver is verified.
  supports_protocol_v1: false
  wake_steps:
    - kind: service
      domain: media_player
      service: turn_on
      entity_id: media_player.living_room_fire_tv_stick_4k_plus
      when_not_states: [playing, paused, idle]
      continue_on_error: true
    - kind: wait_state
      entity_id: media_player.living_room_fire_tv_stick_4k_plus
      states: [idle, playing, paused, on]
      timeout: 20
~~~

Each device's wake steps are optional. For displays requiring CEC, smart plugs, input switching, delays, or other routines, use additional HA service/wait/delay steps. Every step has a bounded timeout and only executes when launching. **Never toggle a smart plug that powers a running device unexpectedly**; configure your own sequence.

For a remote/second network, choose \`launch_method: script\` and \`launch_script: script.my_fire_tv_handoff\`. The script receives \`powerlink_uri\` as a variable and can forward it through an existing secure VPN, broker, remote HA instance or service. That transport must be configured by the user; it isn't bundled.

The existing 1.2.4 app can be opened with:

~~~yaml
action: powerlink.open_device
data:
  entity_id: media_player.living_room_fire_tv_stick_4k_plus
~~~

## Handoff protocol for the PowerPlay receiver

### Preferred lightweight export: Plex queue reference

For Plex server-managed queues (shuffled **or** sequential), the PowerPlay 1.3.0 sender should **not** fetch thousands of episodes on the Fire Stick. Instead it sends just its existing Plex queue ID, selected \`playQueueItemID\`, queue version, current offset and profile:

~~~json
{
  "schema": 1,
  "source_device": "media_player.game_room_fire_tv_stick_lite",
  "profile_id": "plex-home-main",
  "context_key": "shuffle",
  "position_ms": 253400,
  "shuffled": true,
  "queue_source": {
    "type": "plex_play_queue",
    "server_id": "plex-main",
    "play_queue_id": 701,
    "selected_item_id": 3002,
    "version": 5
  }
}
~~~

Home Assistant uses the configured Plex token **for the same Plex account/profile** to GET \`/playQueues/701\` with a centered window big enough for the whole queue. It validates the queue version, total item count, selected item ID and ordered \`playQueueItemID\` list (including duplicates) before allowing a handoff. A partial window, a changed queue, or a wrong Plex identity aborts without waking or stopping the source. The resulting frozen manifest is served in small indexed windows for destination playback.

This means the Fire Stick's handoff CPU/network cost is approximately constant rather than proportional to the queue length. The full \`items\` snapshot described below is retained as a fallback for local/non-Plex queues, but the preferred 1.3.0 Plex path is the lightweight queue reference.

A PowerPlay 1.3.0 source will provide a **complete ordered queue snapshot** to Home Assistant. Example:

~~~json
{
  "schema": 1,
  "source_device": "media_player.living_room_fire_tv_stick_4k_plus",
  "profile_id": "plex-home-main",
  "context_key": "my-favorites-shuffle",
  "current_index": 1,
  "position_ms": 253400,
  "shuffled": true,
  "items": [
    {
      "kind": "episode", "title": "Episode 3", "guid": "plex://episode/example3",
      "server_id": "plex-main", "rating_key": "456",
      "show_guid": "plex://show/example", "show_title": "My Series",
      "season": 1, "episode": 3,
      "copies": [
        {"server_id": "plex-main", "rating_key": "456",
         "guid": "plex://episode/example3", "height": 2160,
         "bitrate_kbps": 25000, "library_title": "TV Shows [4K]"}
      ]
    },
    {
      "kind": "episode", "title": "Episode 8", "guid": "plex://episode/example8",
      "server_id": "plex-main", "rating_key": "789",
      "show_guid": "plex://show/example", "show_title": "My Series",
      "season": 1, "episode": 8,
      "copies": [
        {"server_id": "plex-main", "rating_key": "789",
         "guid": "plex://episode/example8", "height": 1080,
         "bitrate_kbps": 8000, "library_title": "TV Shows"}
      ]
    }
  ]
}
~~~

The controller accepts the snapshot through \`powerlink.prepare_handoff\` (returns an opaque handoff link without waking a device) or, **once a verified 1.3.0 receiver exists**, \`powerlink.handoff\` (wakes the destination and launches the prepared link).

The receiver will handle a \`powerplay://powerlink?v=1&base=<url>&token=<secret>\` intent and GET:

\`<base>/api/powerlink/v1/session/<token>?start=<index>&count=<1..32>\`

The response preserves the original \`current_index\`, \`position_ms\`, \`shuffled\`, \`total\` and indexed \`items\`. The receiver must build an **external, server-provided local queue**, not ask Plex to reshuffle or recreate a new queue. It should fetch more indexed windows as playback advances. Unavailable items are retained with \`status: unavailable\` and must show a recoverable playback error rather than silently jumping to another episode.

After opening and seeking successfully, the receiver POSTs \`{"status":"started"}\` to \`.../session/<token>/ack\`. If it cannot play, POST \`{"status":"failed"}\`. HA emits \`powerlink_handoff_acknowledged\` with the source, destination and outcome. The source should stop **only after a verified playback-start acknowledgment**, via a separately configured automation/policy.

### Security and performance boundaries

- Snapshot capped at 2 MB and 5,000 entries; on-demand windows capped at 32 and Plex lookup concurrency capped at 3.
- Transfer capability tokens are cryptographically random and held in RAM for up to 12 hours; they expire on Home Assistant restart. Anyone who has the token can fetch that **one** queue. Use HTTPS for public/cross-network access, keep tokens out of dashboards, logs and publicly exposed scripts, and do not share raw action responses.
- Plex tokens are used only by Home Assistant's Plex resolver, sent in request headers, and never included in deep links, app messages or transfer responses.
- The \`handoff\` action refuses to launch on clients not marked \`supports_protocol_v1\`. Do not mark a device ready until a v1.3.0+ receiver has actually been deployed and tested.
- The optional Plex resolver is a conservative *targeted* \`/library/all\` lookup; it will never match unrelated media on title alone. Server-specific Plex naming/metadata differences may require later refinements and additional fixture tests.

## Development / separate repository

When ready to publish the independent project, copy the contents of **this \`powerlink/\` directory** into the root of the new \`The-Power-0/PowerLink\` GitHub repository, not the enclosing folder. Keep PowerPlay and PowerLink independently versioned, with their own tests, issues and releases. The accompanying GitHub workflow already has the correct root-relative paths for the new repository.

The PowerPlay 1.3.0 work is a separate PR adding the app-side snapshot exporter, full-queue pagination, position capture, external queue provider, secure relay fetch, dynamic media copy selection and playback acknowledgment. Until then, HACS installation is a **development preview, not a finished cross-room playback feature**.
