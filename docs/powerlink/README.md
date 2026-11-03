# PowerLink for PowerPlay

**Status: v1.3.0 development preview.** This is a Home Assistant **custom integration for HACS**, not an HA OS add-on. It works with Home Assistant Container, Core, OS, and Supervised because it runs inside the Home Assistant process. The standalone PowerPlay 1.2.4 APK **does not yet support** the required PowerLink capture and resume links; do not treat a successful HACS backend build as a completed end-to-end handoff.

PowerLink centralizes device discovery, configurable TV/Fire Stick wake routines, app launching, exact queue snapshots, and Plex 4K/1080p copy matching. There is no idle Fire TV polling and no background Plex library scan.

## Architecture

| Component | Responsibility |
| --- | --- |
| Home Assistant PowerLink integration | Discover existing HA `media_player` entities, manage device policies and wake scripts, authenticate endpoints, store/replay exact queue snapshots, look up Plex GUID copies, stage destination handoffs |
| PowerPlay Fire TV app (v1.3.0 client, pending) | Respond to one-time `capture` requests with the current ordered queue + exact playback position, fetch 50-item transfer windows, play the selected Plex copy and acknowledge successful playback |
| Plex server | Supply metadata and 1080p/4K equivalents by stable GUID; does not reorder queues |
| Existing HA Android Debug Bridge integration or user script | Send wake commands, activate PowerPlay, deliver `powerplay://powerlink/...` intents |

**A queue transfer is not a new Plex shuffle.** It is an immutable snapshot of the existing queue. Duplicate entries and randomized/sequential order are retained; only each item's physical playback copy may change.

### Default policies for the original three-device installation

These examples are for one installation, **not hard-coded into the integration**:

| Device ID | HA media player | Maximum video height | Launch |
| --- | --- | --- | --- |
| `living_room` | `media_player.living_room_fire_tv_stick_4k_plus` | 2160 (4K) | Android Debug Bridge |
| `bedroom` | `media_player.bedroom_fire_tv_stick_lite` | 1080 | Android Debug Bridge |
| `game_room` | `media_player.game_room_fire_tv_stick_lite` | 1080 | Android Debug Bridge |

A transfer from Living Room to either Stick Lite chooses a compatible 1080p equivalent by **exact Plex GUID** (including the correct movie/episode). Transfers to the Living Room select the highest resolution up to its configured 2160 limit, regardless of the current HDMI UI output mode. If there is no suitable copy, PowerLink fails clearly rather than selecting the wrong show or silently trying to play 4K on an HD-only stick.

A single Plex rating key may contain several `Media` versions. PowerLink checks **each media version**, not only the first file, and sends the selected media ID/index to the destination.

## HACS installation (once the app and integration release are complete)

1. In HACS choose **Custom repositories**, paste `https://github.com/The-Power-0/PowerPlay`, and choose **Integration**.
2. Install **PowerLink for PowerPlay**, restart Home Assistant, then go to **Settings → Devices & services → Add integration → PowerLink**.
3. Open **Configure → Add device** for each endpoint. Use the corresponding HA `media_player` entity, or select script launch for a remote/routed device without a directly reachable Android Debug Bridge entity.
4. Set each endpoint's maximum source resolution (480, 720, 1080, 2160, or 4320), wake mode, optional wake/launch scripts, and warmup delay. Resolution policies must reflect real device capabilities, **not the TV's currently selected resolution**.
5. Add each Plex server under **Configure → Add Plex server**. Its ID must correspond to the Plex server ID known to the PowerPlay app; provide a Home Assistant-reachable base URL and the appropriate Plex token.
6. Run **`powerlink.pair_device`** once per device (administrator only), and securely enter the returned pairing token and your accessible Home Assistant URL in the upcoming PowerPlay 1.3.0 PowerLink settings. The token is displayed only once and only a SHA-256 digest is stored in HA.

**Version caveat:** existing PowerPlay v1.2.4 GitHub tags predate this custom integration. Wait for the v1.3.0 release or deliberately select a development branch in HACS. Do not install this as a production integration while app-side support is pending.

## Supported Home Assistant actions

`powerlink.discover_devices`: list existing HA media players, their integration platforms and whether they are already assigned. No network broadcast, unauthenticated ADB scanning, or polling.

`powerlink.launch`: wake a device if needed and launch `powerplay://open` (or a safe PowerPlay deep link). For Fire TV, the Android Debug Bridge integration executes the `am start` intent against `com.power.powerplay`.

`powerlink.pair_device`: administrator-only action returning a one-time pairing token.

`powerlink.handoff`: ask the **source app** for a fresh, nonce-bound complete queue snapshot; verify the destination's current item has a compatible copy; request the destination app to resume using the resulting transfer ID. Source playback is not stopped before successful playback on the destination.

A handoff cannot work until the PowerPlay 1.3.0 app supports both the `capture` and `resume` intents. Do not use a 1.2.4 app for handoff testing.

### Action example

```yaml
action: powerlink.launch
data:
  device_id: living_room
```

After both devices are paired and upgraded:

```yaml
action: powerlink.handoff
data:
  source_device: living_room
  destination_device: bedroom
response_variable: powerlink_transfer
```

### Configurable power-on routines

For simple devices choose `wake_mode: when_off`, a Fire TV media player, `launch_method: adb`, and a delay of 2–5 seconds.

For a television that needs IR, CEC, an HDMI input change, or a smart plug, create a normal HA script and select it as **Wake script**. The script can perform whatever sequences are appropriate, for example:

```yaml
alias: PowerLink - Living Room Wake
mode: single
sequence:
  - action: media_player.turn_on
    target:
      entity_id: media_player.living_room_fire_tv_stick_4k_plus
  - delay: "00:00:03"
```

For devices on another routed network, select **Launch method: script** and supply a custom HA script. That script receives `powerlink_uri` and `powerlink_device` variables and can forward the launch through an approved bridge, VPN host, remote HA instance, or custom local control mechanism. A VPN or other authorized route is necessary: **PowerLink cannot power a completely unreachable device by itself**.

The Android TV Remote integration does not support Fire TV. Configure **Android Debug Bridge** (`androidtv`) or your own scripts rather than relying on `androidtv_remote`.

## PowerLink v1 wire protocol

On handoff, the source Fire Stick receives `powerplay://powerlink/capture?nonce=<nonce>` and POSTs a **compact queue reference** to `/api/powerlink/v1/sessions`: the current Plex play queue ID, the unique selected queue-item ID, and the exact player position. Home Assistant fetches and reconstructs all queue entries **directly from Plex**, including duplicates, without asking the Fire Stick to serialize its library. If server-side reconstruction is unavailable, the endpoint also accepts a complete bounded `items` manifest as a fallback. In either case, a truncated or changing queue is rejected.

Authentication headers:
```
X-PowerLink-Device: living_room
Authorization: Bearer <per-device pairing token>
Content-Type: application/json
```

The preferred lightweight payload is:

```json
{
  "protocol": 1,
  "source_device": "living_room",
  "capture_nonce": "<received nonce>",
  "server_id": "plex_a",
  "play_queue_id": 9631,
  "selected_play_queue_item_id": 2211762,
  "position_ms": 1237912
}
```

PowerLink queries Plex `GET /playQueues/9631` in overlapping windows, checks the queue version, total size and selected queue-item identity, and builds the complete immutable sequence on Home Assistant. A fallback full manifest has `queue_id`, `shuffled`, `index`, `position_ms`, and ordered `items`, each with `guid`, `kind`, `rating_key`, `server_id`, `title` and optional `season`/`episode`. Server queues are capped at 5000 entries; fallback uploads at 512 KiB. There is no lossy conversion from shuffled to sequential order.

After a match is verified, the destination receives `powerplay://powerlink/resume?id=<opaque-transfer-id>`. It fetches `GET /api/powerlink/v1/transfers/<id>?start=<n>&limit=50` with its **own** device pairing token, preserving every queue index including duplicates and unavailable entries. The transfer ID expires after one hour; snapshots expire within 45 seconds. The destination can POST `.../ready` once it actually begins playback.

Responses include explicit selected Plex media source IDs and source indices; a 4K-only entry on a 1080p device is marked unavailable instead of being silently replaced. The app may show an error for that slot but must not skip or reshuffle the others.

## Security and performance

- Device-specific random bearer tokens; only SHA-256 digests retained in Home Assistant storage. Rotate with `powerlink.pair_device`.
- Use HTTPS (Home Assistant Cloud or a trusted TLS reverse proxy) for **cross-network** session exchange, and restrict ADB access to trusted networks. Never log or put pairing tokens in deep links.
- No persistent websocket, background timer on Fire TV, library sweeps, repeated JSON serialization, or periodic queue transfer calls. The preferred snapshot contains only three queue/position numbers and a server ID; Home Assistant performs queue reconstruction directly from Plex.
- All copy lookups happen on the Home Assistant host, with at most four concurrent lookup operations, twelve-second HTTP deadlines and a five-minute bounded cache.
- The source's queue and playback remain intact if discovery, wake-up, copy resolution, destination launch, or acknowledgement fails.
- Handoff requests capture the source position **once at request time** with a nonce. They do not rely on a minutes-old Plex view offset.
- This backend does not continuously monitor the TV; a future app client should report events only on playback transitions or on explicit handoff requests.
- Home Assistant and HACS are **not yet tested on a live instance** by this branch's CI. Python syntax, metadata, planner and Plex-copy regression tests run in GitHub Actions.

## Development and deployment notes

PowerPlay uses a **single canonical Flutter source tree**. The integration lives in `custom_components/powerlink`, with its own fast tests under `tests/powerlink` and `.github/workflows/powerlink-ha-ci.yml`. It can be packaged by HACS without any HA add-on container or external Python process.

The v1.3.0 project still needs its Fire TV client-side capture/resume implementation, pairing UI, and an end-to-end live-device test before a stable APK or HACS tag should be published.
