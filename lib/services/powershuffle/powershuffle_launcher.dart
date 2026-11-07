import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../media/ids.dart';
import '../../media/media_item.dart';
import '../../media/media_item_types.dart';
import '../../media/play_queue.dart';
import '../../profiles/active_profile_provider.dart';
import '../../providers/multi_server_provider.dart';
import '../../providers/playback_state_provider.dart';
import '../../utils/snackbar_helper.dart';
import '../../utils/video_player_navigation.dart';
import '../deep_links/deep_link.dart';
import '../powerlink/powerlink_app_client.dart';
import 'powershuffle_session.dart';

/// Opt-in single-show PowerShuffle launch. Plex's ordinary shuffled and
/// watched/unwatched state remain untouched.
class PowerShuffleLauncher {
  const PowerShuffleLauncher._();

  static bool _launchInFlight = false;

  /// Fire TV Select can repeat; only one queue request/player launch may own
  /// the show detail action at once. Never publish competing HA sessions.
  static Future<void> start(BuildContext context, MediaItem show) async {
    if (_launchInFlight) return;
    _launchInFlight = true;
    try {
      await _launch(context, show);
    } finally {
      _launchInFlight = false;
    }
  }

  static Future<void> _launch(BuildContext context, MediaItem show) async {
    if (show is! PlexMediaItem || !show.isShow ||
        show.serverId == null || show.guid == null || show.guid!.isEmpty) {
      showMainSnackBar('PowerShuffle needs a Plex TV show with a stable GUID.');
      return;
    }
    final profile = context.read<ActiveProfileProvider>().active;
    final identity = await PowerLinkAppCredentials().load();
    if (!context.mounted) return;
    if (profile == null || identity == null) {
      showMainSnackBar('Pair this Fire Stick in Settings → PowerLink first.');
      return;
    }
    final plex = context.read<MultiServerProvider>()
        .getPlexClientForServer(ServerId(show.serverId!));
    if (plex == null) {
      showMainSnackBar('Connect to your Plex server before starting PowerShuffle.');
      return;
    }

    try {
      showMainSnackBar('Preparing PowerShuffle episode rotation…');
      // Fetch the show's real Plex episodes once at launch. There is no
      // continuous library scan or background polling on the Fire Stick.
      final fetched = await plex.fetchClientSideEpisodeQueue(show.id);
      if (!context.mounted) return;
      final items = <String, PlexMediaItem>{};
      final inventory = <Map<String, dynamic>>[];
      for (final row in fetched ?? <MediaItem>[]) {
        if (row is! PlexMediaItem || !row.isEpisode ||
            row.parentIndex == null || row.index == null ||
            row.parentIndex == 0 || row.serverId != show.serverId) continue;
        final key = PowerShuffleSession.keyOf(row)!;
        if (items.containsKey(key)) continue; // HD/4K is one logical episode
        items[key] = row;
        inventory.add({
          'kind': 'episode', 'title': row.title ?? 'Episode ${row.index}',
          'guid': row.guid ?? '', 'server_id': row.serverId,
          'rating_key': row.id, 'show_guid': show.guid,
          'show_title': show.title ?? '', 'season': row.parentIndex,
          'episode': row.index,
          'copies': [
            for (var i = 0; i < (row.mediaVersions?.length ?? 0); i++)
              {
                'server_id': row.serverId, 'rating_key': row.id,
                'guid': row.guid ?? '',
                'height': row.mediaVersions![i].resolutionHeight,
                'bitrate_kbps': row.mediaVersions![i].bitrate ?? 0,
                'media_index': i, 'media_id': row.mediaVersions![i].id,
                'library_title': row.libraryTitle ?? '',
              },
          ],
        });
      }
      if (inventory.isEmpty) {
        showMainSnackBar('No playable regular episodes were found.');
        return;
      }
      final profileId = linkProfileRef(profile);
      final result = await const PowerLinkAppClient().startPowerShuffle(identity, {
        'profile_id': profileId,
        'show_guid': show.guid,
        'server_id': show.serverId,
        'title': show.title ?? 'TV Show',
        'episodes': inventory,
      });
      if (!context.mounted) return;
      if (result['action'] == 'handoff') {
        // HA now owns the safe destination launch. It pauses the source only
        // after the new player acknowledges first-frame playback.
        showMainSnackBar('PowerShuffle is transferring from your other Fire Stick.');
        return;
      }
      if (result['action'] == 'already_playing') {
        showMainSnackBar('PowerShuffle is already playing on this Fire Stick.');
        return;
      }
      final ids = result['queue'];
      final sessionId = result['session_id'];
      if (result['action'] != 'play' || ids is! List || sessionId is! String) {
        showMainSnackBar('No eligible PowerShuffle episodes. Check the five-day skips in Home Assistant.');
        return;
      }
      final ordered = <PlexMediaItem>[
        for (final id in ids)
          if (id is String && items[id] != null)
            items[id]!.copyWith(viewOffsetMs: 0),
      ];
      if (ordered.isEmpty) {
        showMainSnackBar('PowerShuffle could not match the next episode to your Plex library.');
        return;
      }
      PowerShuffleSession.instance.begin(
        identity: identity, profileId: profileId, showGuid: show.guid!,
        serverId: show.serverId!, sessionId: sessionId,
        order: ids.whereType<String>().toList(growable: false), items: items,
      );
      context.read<PlaybackStateProvider>().setPlaybackFromLocalQueue(
        LocalPlayQueue(items: ordered, currentIndex: 0, shuffled: true),
        contextKey: PowerShuffleSession.instance.contextKey,
      );
      await navigateToVideoPlayer(
        context, metadata: ordered.first, resolveWatchState: false,
      );
    } catch (_) {
      if (context.mounted) {
        showMainSnackBar('PowerShuffle could not connect to Home Assistant or Plex.');
      }
    }
  }
}
