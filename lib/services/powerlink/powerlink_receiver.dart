import 'dart:async';
import 'dart:math';

import 'package:flutter/widgets.dart';
import 'package:provider/provider.dart';

import '../../media/ids.dart';
import '../../media/media_item.dart';
import '../../media/media_version.dart';
import '../../providers/multi_server_provider.dart';
import '../../providers/playback_state_provider.dart';
import '../../services/playback_launch_observer.dart';
import '../../services/playback_coordinator.dart';
import '../../utils/app_logger.dart';
import '../../utils/snackbar_helper.dart';
import '../../utils/video_player_navigation.dart';
import '../deep_links/deep_link.dart';
import 'powerlink_transfer.dart';
import 'powerlink_destination_takeover.dart';

/// Receives an exact, already-ordered PowerLink transfer from Home Assistant.
///
/// The original shuffle (or normal queue) is never restarted. The server
/// provides 32-slot windows; the same immutable absolute index is used for
/// identical episodes appearing at different positions in the queue.
class PowerLinkReceiver {
  PowerLinkReceiver._();

  static int _generation = 0;
  // The HA host retains the complete imported queue; a subsequent handoff
  // can reuse that immutable manifest without shipping 5000 entries.
  static String? activeManifestToken;


  static Future<void> launch(BuildContext context, PowerLinkResumeLink link) async {
    final generation = ++_generation;
    final bridge = PowerLinkTransferClient(link.request);
    try {
      // Get queue header (tiny one-item response), then the window centered
      // around the actual playing slot. Never fetch a 5000-entry manifest.
      final header = await bridge.fetch(0, count: 1);
      if (!context.mounted || _generation != generation) return;
      final start = max(0, min(header.currentIndex - 8, max(0, header.total - 32)));
      final initial = await bridge.fetch(start, count: min(32, header.total - start));
      if (!context.mounted || _generation != generation) return;
      if (header.total != initial.total ||
          header.currentIndex != initial.currentIndex ||
          header.shuffled != initial.shuffled ||
          header.positionMs != initial.positionMs ||
          header.profileId != initial.profileId) {
        throw const FormatException('PowerLink transfer changed while loading');
      }

      // The native deep-link profile switch runs first when the link names
      // a profile. Never silently accept an explicitly conflicting identity.
      if (initial.profileId case final profile? when profile.isNotEmpty) {
        if (link.profile != profile) {
          throw const FormatException('PowerLink destination Plex profile mismatch');
        }
      }

      final selected = initial.selected;
      if (selected == null || !selected.isAvailable) {
        throw const FormatException('No playable matching file at current queue index');
      }
      final serverId = selected.serverId!;
      final ratingKey = selected.ratingKey!;
      final plex = context.read<MultiServerProvider>().getClientForServer(ServerId(serverId));
      if (plex == null) throw const FormatException('Destination Plex server is unavailable');
      final resolved = await plex.fetchItem(ratingKey);
      if (!context.mounted || _generation != generation) return;
      if (resolved is! PlexMediaItem || resolved.kind != selected.kind) {
        throw const FormatException('Resolved Plex item does not match handoff media');
      }

      final choice = _pickVersion(resolved, selected);
      final playingItem = resolved.copyWith(
        playQueueItemId: selected.index + 1,
        viewOffsetMs: initial.positionMs,
      );

      // The old player must release its route, media session and native core
      // *before* PowerLink commits its queue. Otherwise the normal navigation
      // guard refuses to launch a second video ('playbackActive'), leaving
      // the original show playing while the transferred queue appears in UI.
      // Awaiting complete retirement also prevents simultaneous Media3 core
      // teardown/startup, a potential source of transient native errors.
      await PowerLinkDestinationTakeover.retire(
        hasVideoSession: () => PlaybackCoordinator.instance.hasVideoSession,
        stopVideoAndExit: () => PlaybackCoordinator.instance.stopVideoAndExit(),
      );
      if (!context.mounted || _generation != generation) return;

      final queue = context.read<PlaybackStateProvider>();
      // Keep only one bounded queue window in memory; the callback loads the
      // neighboring window on demand. An unavailable slot remains an explicit
      // failed navigation rather than being silently skipped/replaced.
      queue.setPlayQueueWindowFetcher((id, {center, window = 50}) async {
        if (id != -2 || _generation != generation) return null;
        final centerIndex = (int.tryParse(center ?? '') ?? 1) - 1;
        if (centerIndex < 0 || centerIndex >= header.total) return null;
        final startIndex = max(0, min(centerIndex - 8, max(0, header.total - 32)));
        final page = await bridge.fetch(startIndex, count: min(32, header.total - startIndex));
        if (page.total != header.total ||
            page.currentIndex != header.currentIndex ||
            page.shuffled != header.shuffled ||
            page.positionMs != header.positionMs) {
          throw const FormatException('PowerLink queue changed after transfer');
        }
        return page.toPlaybackWindow();
      });
      await queue.setPlaybackFromPlayQueue(initial.toPlaybackWindow(), 'powerlink');
      if (!context.mounted || _generation != generation) return;
      activeManifestToken = link.request.token;

      final observer = PlaybackLaunchObserver(isCurrent: () => _generation == generation);
      // Navigation's future completes when the player closes, not after
      // playback starts. Never wait for route close before acknowledging.
      unawaited(navigateToVideoPlayer(
        context,
        metadata: playingItem,
        resolveWatchState: false,
        initialPosition: Duration(milliseconds: initial.positionMs),
        selectedMediaIndex: choice.$1,
        selectedMediaSourceId: choice.$2,
        strictMediaSelection: true,
        launchObserver: observer,
      ).catchError((Object error, StackTrace stack) {
        // Navigation is asynchronous; a failing route commit should never
        // silently leave a swapped queue with no destination playback.
        appLogger.w('PowerLink destination navigation failed',
            error: error, stackTrace: stack);
        observer.mark('failed', failure: 'navigationFailed');
        return null;
      }));
      unawaited(_acknowledgeWhenPlaying(
        bridge, observer, selected, initial.positionMs, generation,
      ));
    } catch (error, stack) {
      // No access credential or capability token is logged.
      appLogger.w('PowerLink could not safely resume the selected queue item',
          error: error, stackTrace: stack);
      if (context.mounted) {
        showMainSnackBar('PowerLink could not resume this queue. Original device was not stopped.');
      }
      unawaited(_safeAck(bridge, 'failed'));
    }
  }

  /// Media IDs take precedence; indices are verified against actual Plex
  /// metadata. An HD destination must not open a UHD-only first file when
  /// two source versions share one Plex rating key.
  static (int, String?) _pickVersion(PlexMediaItem item, PowerLinkQueueSlot slot) {
    final versions = item.mediaVersions ?? const <MediaVersion>[];
    if (versions.isEmpty) {
      throw const FormatException('Plex did not report playable media versions');
    }
    int index = -1;
    if (slot.mediaId case final id? when id.isNotEmpty) {
      index = versions.indexWhere((version) => version.id == id);
      if (index < 0) throw const FormatException('Selected Plex media version no longer exists');
    } else if (slot.mediaIndex != null) {
      index = slot.mediaIndex!;
      if (index >= versions.length) throw const FormatException('Plex media version index is invalid');
    } else if (slot.height case final height?) {
      // Backwards compatibility with early HA preview which sent a height
      // but no Plex Media ID/index.
      for (var i = 0; i < versions.length; i++) {
        if (versions[i].resolutionHeight == height) {
          index = i;
          break;
        }
      }
      if (index < 0) throw const FormatException('No exact matching Plex resolution');
    } else if (versions.length == 1) {
      index = 0;
    } else {
      throw const FormatException('Ambiguous Plex source: missing media version');
    }
    final version = versions[index];
    if (slot.height != null && version.resolutionHeight != slot.height) {
      throw const FormatException('Plex media source resolution differs from Home Assistant');
    }
    return (index, version.id.isEmpty ? null : version.id);
  }

  static Future<void> _safeAck(PowerLinkTransferClient client, String outcome) async {
    try {
      await client.acknowledge(outcome);
    } catch (_) {
      // Network acknowledgment is best effort; local playback is not affected.
    }
  }

  static Future<void> _acknowledgeWhenPlaying(
    PowerLinkTransferClient client,
    PlaybackLaunchObserver observer,
    PowerLinkQueueSlot target,
    int positionMs,
    int generation,
  ) async {
    // Temporary 30-second watcher only for this user-initiated handoff.
    // No persistent app polling, stream listeners or background services.
    for (var attempt = 0; attempt < 150; attempt++) {
      await Future<void>.delayed(const Duration(milliseconds: 200));
      if (generation != _generation || !observer.isCurrent) return;
      final state = observer.snapshot();
      final stage = state['stage'];
      if (stage == 'failed' || stage == 'blocked' || stage == 'stopped' || stage == 'cancelled') {
        await _safeAck(client, 'failed');
        return;
      }
      final item = state['item'];
      final matches = item is Map &&
          item['serverId'] == target.serverId && item['itemId'] == target.ratingKey;
      final offset = state['positionMs'];
      final positionReady = offset is int && (offset - positionMs).abs() <= 6000;
      if (stage == 'playing' && state['ready'] == true && matches && positionReady) {
        await _safeAck(client, 'started');
        return;
      }
    }
    await _safeAck(client, 'failed');
  }
}
