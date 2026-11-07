import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/widgets.dart';
import 'package:provider/provider.dart';

import '../../media/media_item.dart';
import '../../media/media_item_types.dart';
import '../../media/play_queue.dart';
import '../../providers/playback_state_provider.dart';
import '../../providers/multi_server_provider.dart';
import '../../media/ids.dart';
import '../powerlink/powerlink_app_client.dart';
import 'powershuffle_event_journal.dart';

/// A single active PowerShuffle player-side session. Only a named
/// PowerShuffle queue context may report events; ordinary Plex Shuffle and
/// manually launched episodes are deliberately invisible to this class.
///
/// The Home Assistant PowerLink integration remains the authoritative store.
class PowerShuffleSession {
  PowerShuffleSession._();
  static final PowerShuffleSession instance = PowerShuffleSession._();

  final PowerLinkAppClient _api = const PowerLinkAppClient();
  final PowerShuffleEventJournal _journal = const PowerShuffleEventJournal();
  PowerLinkAppIdentity? _identity;
  String _sessionId = '';
  String _profileId = '';
  String _showGuid = '';
  String _serverId = '';
  String _currentKey = '';
  String? _awaitingEpisodeKey;
  String? _attachedManifestToken;
  PlexMediaItem? _pendingNavigationTarget;
  List<String> _order = [];
  Map<String, PlexMediaItem> _items = {};
  List<List<int>> _coverage = [];
  int? _lastPosition;
  int? _lastDuration;
  DateTime? _lastSample;
  DateTime? _lastSent;
  bool _started = false;
  bool _completed = false;
  int _completionPercent = 90;
  int _eventCounter = 0;
  Future<void> _inFlight = Future<void>.value();

  String get sessionId => _sessionId;
  String get contextKey => 'powershuffle:$_sessionId';
  bool get active => _identity != null && _sessionId.isNotEmpty;
  bool get completedForCurrent => _completed;
  bool get hasStarted => _started;
  String? get attachedManifestToken => _attachedManifestToken;
  MediaItem? get pendingNavigationTarget => _pendingNavigationTarget;

  static String? keyOf(MediaItem item) {
    if (item is! PlexMediaItem || !item.isEpisode) return null;
    if (item.parentIndex == null || item.index == null) return null;
    return '${item.parentIndex}:${item.index}';
  }

  bool matches(MediaItem item, String? queueContextKey) =>
      active &&
      queueContextKey == contextKey &&
      item.serverId == _serverId &&
      keyOf(item) != null &&
      _items.containsKey(keyOf(item));

  /// Called after HA approves a new queue. The selected episode deliberately
  /// has its normal Plex resume offset removed.
  void begin({
    required PowerLinkAppIdentity identity,
    required String profileId,
    required String showGuid,
    required String serverId,
    required String sessionId,
    required List<String> order,
    required Map<String, PlexMediaItem> items,
    Map<String, dynamic>? settings,
  }) {
    _identity = identity;
    _profileId = profileId;
    _showGuid = showGuid;
    _serverId = serverId;
    _sessionId = sessionId;
    _items = Map.of(items);
    _order = List.of(order);
    final requestedThreshold = settings?['completion_percent'];
    _completionPercent = requestedThreshold is int &&
            requestedThreshold >= 80 && requestedThreshold <= 95
        ? requestedThreshold
        : 90;
    _awaitingEpisodeKey = null;
    _pendingNavigationTarget = null;
    _attachedManifestToken = null;
    _resetEpisode();
  }

  void _resetEpisode() {
    _currentKey = '';
    _coverage = [];
    _lastPosition = null;
    _lastDuration = null;
    _lastSample = null;
    _lastSent = null;
    _started = false;
    _completed = false;
  }

  /// Join an existing session only after PowerLink's first-frame ACK moved
  /// ownership to this device. The queue header carries the session ID, not
  /// a credential. Only a paired recipient can obtain HA's session metadata.
  Future<void> attachFromHandoff(
    BuildContext context, String? transferredContext, MediaItem current, {
    String? manifestToken,
  }) async {
    if (transferredContext == null ||
        !transferredContext.startsWith('powershuffle:')) {
      return;
    }
    final id = transferredContext.substring('powershuffle:'.length);
    if (id.isEmpty || (active && _sessionId == id &&
        _attachedManifestToken == manifestToken)) return;
    final identity = await PowerLinkAppCredentials().load();
    if (identity == null) return;
    Map<String, dynamic>? response;
    for (var attempt = 0; attempt < 8; attempt++) {
      try {
        response = await _api.attachPowerShuffle(identity, id);
        break;
      } catch (_) {
        await Future<void>.delayed(const Duration(seconds: 1));
      }
    }
    if (response == null || !context.mounted) return;
    final profile = response['profile_id'];
    final showGuid = response['show_guid'];
    final serverId = response['server_id'];
    final order = response['queue'];
    if (profile is! String || showGuid is! String ||
        serverId is! String || order is! List) {
      return;
    }

    // The receiving PowerLink window already contains destination-matched
    // HD/4K copies. Prefer those verified entries even if fetching the full
    // show's local Plex inventory later fails or is still incomplete.
    final items = <String, PlexMediaItem>{};
    for (final item in context.read<PlaybackStateProvider>().loadedItems) {
      if (item is! PlexMediaItem || item.serverId != serverId) continue;
      final key = keyOf(item);
      if (key != null && order.contains(key)) {
        items.putIfAbsent(key, () => item);
      }
    }
    // Fetch only on actual receiver handoff, never as a background task.
    if (current is PlexMediaItem && current.grandparentId != null) {
      final plex = context.read<MultiServerProvider>()
          .getPlexClientForServer(ServerId(serverId));
      if (plex != null) {
        try {
          final episodes = await plex.fetchClientSideEpisodeQueue(
            current.grandparentId!,
          );
          if (!context.mounted) return;
          for (final episode in episodes ?? <MediaItem>[]) {
            if (episode is PlexMediaItem && episode.serverId == serverId) {
              final key = keyOf(episode);
              if (key != null && order.contains(key)) {
                items.putIfAbsent(key, () => episode);
              }
            }
          }
        } catch (_) {
          // Plex inventory is supplementary. Never lose the already verified
          // PowerLink destination queue just because a metadata scan failed.
        }
      }
    }
    if (!context.mounted) return;
    final activeKey = keyOf(current);
    if (current is! PlexMediaItem || current.serverId != serverId ||
        activeKey == null || !order.contains(activeKey)) {
      return; // Never attach to unrelated Plex media or another profile.
    }
    // A handoff can be ready before the destination has fetched the rest
    // of the series. Preserve tracking of its verified current episode even
    // if that follow-up inventory request is unavailable.
    items.putIfAbsent(activeKey, () => current);
    begin(
      identity: identity, profileId: profile, showGuid: showGuid,
      serverId: serverId, sessionId: id,
      order: order.whereType<String>().toList(growable: false),
      items: items,
      settings: response['settings'] is Map<String, dynamic>
          ? response['settings'] as Map<String, dynamic> : null,
    );
    // Returning to a previously used Fire Stick may carry the SAME
    // PowerShuffle session ID but a NEW PowerLink transfer manifest.
    // Reattach on each newly acknowledged transfer, never assume stale
    // locally cached queue/coverage still belongs to this device.
    _attachedManifestToken = manifestToken;
    final savedKey = response['coverage_episode'];
    final ranges = response['coverage'];
    if (savedKey is String && savedKey == keyOf(current) && ranges is List) {
      _currentKey = savedKey;
      _coverage = [
        for (final pair in ranges)
          if (pair is List && pair.length == 2 &&
              pair[0] is int && pair[1] is int)
            [pair[0] as int, pair[1] as int],
      ];
      _started = true; // preserve the same viewed-content attempt
    }
  }

  int get viewedMs =>
      _coverage.fold<int>(0, (sum, pair) => sum + pair[1] - pair[0]);

  void _addRange(int start, int end) {
    if (end <= start) return;
    final sorted = <List<int>>[..._coverage, [start, end]]
      ..sort((a, b) => a[0].compareTo(b[0]));
    final merged = <List<int>>[];
    for (final range in sorted) {
      if (merged.isNotEmpty && range[0] <= merged.last[1]) {
        merged.last[1] = math.max(merged.last[1], range[1]);
      } else {
        merged.add(List.of(range));
      }
    }
    _coverage = merged.take(128).toList(growable: false);
  }

  /// Sample only while the native player really advances. Seeking across
  /// unviewed content never fills in the gap or earns a completion.
  void observe({
    required MediaItem item,
    required String? queueContextKey,
    required bool playing,
    required int positionMs,
    required int durationMs,
  }) {
    if (!matches(item, queueContextKey) || durationMs <= 0) return;
    final key = keyOf(item)!;
    // After a confirmed Next, do not resurrect the old episode while its
    // native stream is still retiring and the new item is being loaded.
    if (_awaitingEpisodeKey != null && key != _awaitingEpisodeKey) return;
    if (key == _awaitingEpisodeKey) {
      _awaitingEpisodeKey = null;
      _pendingNavigationTarget = null;
    }
    if (_currentKey != key) {
      _resetEpisode();
      _currentKey = key;
    }
    final now = DateTime.now();
    _lastDuration = durationMs;
    if (!playing || positionMs <= 0) {
      _lastPosition = null;
      _lastSample = null;
      return;
    }
    if (!_started) {
      _started = true;
      unawaited(_record('started', positionMs, durationMs).then<void>((_) {}, onError: (Object _) {}));
    }
    final before = _lastPosition;
    final elapsed = now.difference(_lastSample ?? now).inMilliseconds;
    if (before != null &&
        elapsed > 0 && elapsed <= 5000 &&
        positionMs > before && positionMs - before <= elapsed + 1000) {
      _addRange(before, math.min(positionMs, durationMs));
    }
    _lastPosition = positionMs;
    _lastSample = now;
    if (!_completed && viewedMs * 100 >= durationMs * _completionPercent) {
      _completed = true;
      unawaited(_record('completed', positionMs, durationMs).then<void>((_) {}, onError: (Object _) { _completed = false; }));
    } else if (_lastSent == null || now.difference(_lastSent!).inSeconds >= 12) {
      _lastSent = now;
      unawaited(_record('progress', positionMs, durationMs).then<void>((_) {}, onError: (Object _) {}));
    }
  }

  /// Auto-skipped Plex intro/credits markers represent intentionally
  /// omitted non-story content, not a seek chosen to fake completion.
  /// Manual seeks never use this path.
  void creditAutomaticSkip(int startMs, int endMs, int durationMs) {
    if (!active || !_started || _currentKey.isEmpty ||
        durationMs <= 0 || startMs < 0 || endMs > durationMs ||
        endMs <= startMs) {
      return;
    }
    _addRange(startMs, endMs);
    if (!_completed && viewedMs * 100 >= durationMs * _completionPercent) {
      _completed = true;
      unawaited(_record('completed', endMs, durationMs).then<void>((_) {}, onError: (Object _) { _completed = false; }));
    }
  }

  Future<Map<String, dynamic>> _record(
    String action, int positionMs, int durationMs, {String? requestedKey}
  ) async {
    if (!active || _currentKey.isEmpty) throw StateError('PowerShuffle is inactive');
    final identity = _identity!;
    final payload = <String, dynamic>{
      'profile_id': _profileId,
      'show_guid': _showGuid,
      'server_id': _serverId,
      'session_id': _sessionId,
      'episode_key': _currentKey,
      'event_id': '${DateTime.now().microsecondsSinceEpoch}-${++_eventCounter}',
      'action': action,
      'position_ms': positionMs.clamp(0, 86400000),
      'duration_ms': durationMs.clamp(1, 86400000),
      'viewed_ms': viewedMs,
      'ranges': _coverage,
    };
    if (requestedKey != null) {
      payload['requested_episode_key'] = requestedKey;
    }
    // Keep start -> progress -> complete -> skip/EOF ordered even if the
    // network responds out of order. An explicit skip waits for its ACK.
    final completer = Completer<Map<String, dynamic>>();
    _inFlight = _inFlight.catchError((Object _) {}).then((_) async {
      try {
        completer.complete(await _journal.send(identity, payload));
      } catch (error, stack) {
        completer.completeError(error, stack);
      }
    });
    return completer.future;
  }

  /// Advance the authoritative queue before changing the player. A failed HA
  /// request does NOT silently invent a shuffle order or skip record.
  /// Flush observed viewing ranges before user-requested PowerLink handoff.
  /// The handoff itself still captures the exact live player position from
  /// the native player, and neither changes skip state nor resets the queue.
  Future<void> flushBeforeHandoff() async {
    if (!active || !_started || _currentKey.isEmpty) return;
    await _record('progress', _lastPosition ?? 0, _lastDuration ?? 1);
  }

  Future<MediaItem?> advance(
    BuildContext context, {
    required bool atEnd,
    String? skipChoice,
    MediaItem? requested,
  }) async {
    if (!active || !_started) return null;
    final selected = requested == null ? null : keyOf(requested);
    final action = atEnd || _completed
        ? 'ended'
        : skipChoice == 'five_days'
            ? 'skip_five_days'
            : 'skip_next_cycle';
    final result = await _record(
      action, _lastPosition ?? 0, 1, requestedKey: selected,
    );
    if (!context.mounted) return null;
    final order = result['queue'];
    if (order is! List) return null;
    _order = order.whereType<String>().toList(growable: false);
    if (_order.isEmpty) {
      _resetEpisode();
      return null;
    }
    final next = _items[_order.first];
    if (next == null) {
      _resetEpisode();
      return null;
    }
    // Rebuild the local window only after HA commits the mutation.
    final playable = [
      for (final key in _order)
        if (_items[key] case final PlexMediaItem episode)
          episode.copyWith(viewOffsetMs: 0),
    ];
    if (playable.isEmpty) return null;
    final playbackState = context.read<PlaybackStateProvider>();
    playbackState.setPlaybackFromLocalQueue(
      LocalPlayQueue(items: playable, currentIndex: 0, shuffled: true),
      contextKey: contextKey,
    );
    _resetEpisode();
    _awaitingEpisodeKey = keyOf(playable.first);
    _pendingNavigationTarget = playable.first;
    return playable.first;
  }

  /// Early ordinary exits deliberately do not invoke either skip action.
  Future<void> leave() async {
    if (!active || !_started || _currentKey.isEmpty) return;
    try {
      await _record('exited', _lastPosition ?? 0, 1);
    } catch (_) {
      // The last acknowledged progress still preserves any completed state.
    }
  }

  void deactivate() {
    _identity = null;
    _sessionId = '';
    _attachedManifestToken = null;
    _awaitingEpisodeKey = null;
    _resetEpisode();
    _items = {};
    _order = [];
  }
}
