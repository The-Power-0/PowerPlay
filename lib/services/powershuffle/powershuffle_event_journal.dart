import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../powerlink/powerlink_app_client.dart';

/// Small device-local outbox for unacknowledged PowerShuffle events.
///
/// This stores no Home Assistant credential or Plex token. Each record carries
/// an idempotency key, so retrying after a Fire TV sleep/app restart cannot
/// double count a completed episode. HA is the final authority: no local
/// event may invent or advance a queue without an HA acknowledgment.
class PowerShuffleEventJournal {
  const PowerShuffleEventJournal({PowerLinkAppClient client = const PowerLinkAppClient()})
      : _client = client; // ignore: prefer_initializing_formals — public injected name stays stable

  final PowerLinkAppClient _client;
  static const _prefix = 'powershuffle.pending.v1.';

  Future<List<Map<String, dynamic>>> _read(SharedPreferences prefs, String name) async {
    final raw = prefs.getString(_prefix + name);
    if (raw == null) return <Map<String, dynamic>>[];
    try {
      final parsed = jsonDecode(raw);
      if (parsed is! List || parsed.length > 200) {
        throw const FormatException('PowerShuffle journal exceeds safe bound');
      }
      return [
        for (final item in parsed)
          if (item is Map<String, dynamic>) item,
      ];
    } on FormatException {
      // Prefer a visible error to silently losing the only copy of a queued
      // completion or skip. The app's event caller can present its failure UI.
      rethrow;
    } catch (_) {
      throw const FormatException('PowerShuffle event journal is invalid');
    }
  }

  Future<void> _write(
    SharedPreferences prefs, String name, List<Map<String, dynamic>> events,
  ) async {
    if (!await prefs.setString(_prefix + name, jsonEncode(events))) {
      throw const FormatException('Could not save PowerShuffle pending event');
    }
  }

  Future<Map<String, dynamic>?> flush(PowerLinkAppIdentity identity, {String? requiredEventId}) async {
    final prefs = await SharedPreferences.getInstance();
    final name = identity.sourceDevice;
    final pending = await _read(prefs, name);
    Map<String, dynamic>? latest;
    while (pending.isNotEmpty) {
      try {
        latest = await _client.powerShuffleEvent(identity, pending.first);
      } on FormatException catch (e) {
        if (e.message.toString().contains('HTTP 409') &&
            pending.first['event_id'] == requiredEventId) {
          pending.removeAt(0);
          await _write(prefs, name, pending);
          rethrow; // The current explicit Next must not falsely succeed.
        }
        // The source can cease to own a session after an acknowledged
        // PowerLink handoff. Those stale events must not block future ones.
        // Only definitive HA conflicts are discarded; transport errors
        // remain on disk for the next retry.
        if (!e.message.toString().contains('HTTP 409')) rethrow;
      }
      pending.removeAt(0);
      await _write(prefs, name, pending);
    }
    return latest;
  }

  Future<Map<String, dynamic>> send(
    PowerLinkAppIdentity identity, Map<String, dynamic> event,
  ) async {
    final prefs = await SharedPreferences.getInstance();
    final name = identity.sourceDevice;
    final pending = await _read(prefs, name);
    // Progress contains complete cumulative viewed ranges. A long offline
    // interval therefore needs only its latest unsent progress event per
    // current episode, not hundreds of duplicate heartbeat records.
    final last = pending.isEmpty ? null : pending.last;
    if (event['action'] == 'progress' && last?['action'] == 'progress' &&
        last?['session_id'] == event['session_id'] &&
        last?['episode_key'] == event['episode_key']) {
      pending[pending.length - 1] = Map<String, dynamic>.of(event);
    } else {
      if (pending.length >= 200) {
        throw const FormatException('PowerShuffle pending event journal is full');
      }
      pending.add(Map<String, dynamic>.of(event));
    }
    await _write(prefs, name, pending);
    final reply = await flush(identity, requiredEventId: event['event_id'] as String?);
    if (reply == null || reply['accepted'] != true) {
      throw const FormatException('PowerShuffle event was not acknowledged');
    }
    return reply;
  }
}
