import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../media/media_item.dart';
import '../../media/media_kind.dart';
import '../../models/plex/play_queue_response.dart';

/// A one-time PowerLink transfer. It does not store the queue, HA credentials,
/// or a Plex token on the Fire Stick. The capability token grants access only
/// to the transfer manifest and expires on the Home Assistant host.
class PowerLinkRequest {
  const PowerLinkRequest(this.base, this.token);

  final Uri base;
  final String token;

  static final _tokenPattern = RegExp(r'^[a-zA-Z0-9_-]{32,128}$');

  static PowerLinkRequest? parse(String? endpoint, String? capability) {
    if (endpoint == null || capability == null || !_tokenPattern.hasMatch(capability)) {
      return null;
    }
    final base = Uri.tryParse(endpoint);
    if (base == null || !validEndpoint(base)) return null;
    return PowerLinkRequest(base, capability);
  }

  /// Unencrypted HTTP is allowed only on explicitly private home networks.
  /// Routed/public endpoints must use HTTPS. No URL-embedded credentials.
  static bool validEndpoint(Uri base) {
    if (base.userInfo.isNotEmpty || base.host.isEmpty ||
        base.hasQuery || base.hasFragment || (base.path != '' && base.path != '/')) {
      return false;
    }
    if (base.scheme == 'https') return true;
    if (base.scheme != 'http') return false;
    final host = base.host.toLowerCase();
    final parts = host.split('.');
    if (parts.length == 4) {
      final octets = parts.map(int.tryParse).toList(growable: false);
      if (octets.any((n) => n == null || n < 0 || n > 255)) return false;
      final a = octets[0]!;
      final b = octets[1]!;
      return a == 10 || (a == 172 && b >= 16 && b <= 31) ||
          (a == 192 && b == 168) || a == 127;
    }
    return host == 'localhost' || host.endsWith('.local');
  }

  Uri windowUri(int start, int count) => base.replace(
    path: '/api/powerlink/v1/session/$token',
    queryParameters: {'start': '$start', 'count': '$count'},
  );

  Uri ackUri() => base.replace(path: '/api/powerlink/v1/session/$token/ack');
}

/// A slot is an absolute queue position, not a Plex rating key. Repeated
/// episodes must remain distinct and the original shuffle never runs again.
class PowerLinkQueueSlot {
  const PowerLinkQueueSlot({
    required this.index,
    required this.status,
    required this.title,
    required this.kind,
    this.serverId,
    this.ratingKey,
    this.guid,
    this.mediaIndex,
    this.mediaId,
    this.height,
  });

  final int index;
  final String status;
  final String title;
  final MediaKind kind;
  final String? serverId;
  final String? ratingKey;
  final String? guid;
  final int? mediaIndex;
  final String? mediaId;
  final int? height;

  bool get isAvailable => status == 'resolved' && serverId != null && ratingKey != null;

  factory PowerLinkQueueSlot.parse(Object? raw) {
    if (raw is! Map<String, dynamic>) throw const FormatException('Invalid PowerLink slot');
    final index = raw['index'];
    final status = raw['status'];
    final title = raw['title'];
    if (index is! int || index < 0 ||
        (status != 'resolved' && status != 'unavailable') ||
        title is! String || title.isEmpty) {
      throw const FormatException('Invalid PowerLink queue index or slot status');
    }
    final kind = switch (raw['kind']) {
      'movie' => MediaKind.movie,
      'episode' => MediaKind.episode,
      _ => null,
    };
    if (kind == null) throw const FormatException('PowerLink supports movies and episodes');
    final media = raw['media'];
    if (status == 'resolved' && media is! Map<String, dynamic>) {
      throw const FormatException('Resolved item has no Plex media reference');
    }
    final ref = media is Map<String, dynamic> ? media : const <String, dynamic>{};
    String? nonempty(Object? value) => value is String && value.isNotEmpty ? value : null;
    final server = nonempty(ref['server_id']);
    final rating = nonempty(ref['rating_key']);
    if (status == 'resolved' && (server == null || rating == null)) {
      throw const FormatException('PowerLink media identity missing');
    }
    final sourceIndex = ref['media_index'];
    if (sourceIndex != null && (sourceIndex is! int || sourceIndex < 0 || sourceIndex > 50)) {
      throw const FormatException('Invalid media version index');
    }
    final height = ref['height'];
    if (height != null && (height is! int || height <= 0 || height > 8640)) {
      throw const FormatException('Invalid media source resolution');
    }
    return PowerLinkQueueSlot(
      index: index, status: status, title: title, kind: kind,
      serverId: server, ratingKey: rating, guid: nonempty(ref['guid']),
      mediaIndex: sourceIndex as int?, mediaId: nonempty(ref['media_id']),
      height: height as int?,
    );
  }

  MediaItem toQueueItem() {
    // The flag is checked before navigating to a missing entry; never let an
    // unavailable copy silently become a different episode.
    return MediaItem.plex(
      id: ratingKey ?? 'powerlink_unavailable_$index',
      kind: kind,
      title: title,
      guid: guid,
      serverId: serverId,
      playQueueItemId: index + 1,
      raw: isAvailable ? null : {'powerlink_unavailable': true},
    );
  }
}

class PowerLinkQueueWindow {
  const PowerLinkQueueWindow({
    required this.total,
    required this.currentIndex,
    required this.positionMs,
    required this.shuffled,
    required this.start,
    required this.items,
    this.profileId,
  });

  final int total;
  final int currentIndex;
  final int positionMs;
  final bool shuffled;
  final int start;
  final String? profileId;
  final List<PowerLinkQueueSlot> items;

  PowerLinkQueueSlot? get selected {
    for (final item in items) {
      if (item.index == currentIndex) return item;
    }
    return null;
  }

  factory PowerLinkQueueWindow.parse(Object? value) {
    if (value is! Map<String, dynamic>) throw const FormatException('Invalid PowerLink window');
    final total = value['total'];
    final index = value['current_index'];
    final position = value['position_ms'];
    final shuffled = value['shuffled'];
    final start = value['start'];
    final rows = value['items'];
    if (total is! int || total < 1 || total > 5000 ||
        index is! int || index < 0 || index >= total ||
        position is! int || position < 0 || position > 86400000 ||
        shuffled is! bool || start is! int || start < 0 || start >= total ||
        rows is! List || rows.isEmpty || rows.length > 32 ||
        start + rows.length > total) {
      throw const FormatException('Invalid PowerLink queue header');
    }
    final items = <PowerLinkQueueSlot>[];
    for (var i = 0; i < rows.length; i++) {
      final item = PowerLinkQueueSlot.parse(rows[i]);
      if (item.index != start + i) throw const FormatException('PowerLink queue has missing or reordered slots');
      items.add(item);
    }
    final profile = value['profile_id'];
    if (profile != null && profile is! String) throw const FormatException('Invalid PowerLink profile');
    return PowerLinkQueueWindow(
      total: total, currentIndex: index, positionMs: position,
      shuffled: shuffled, start: start, items: List.unmodifiable(items),
      profileId: profile as String?,
    );
  }

  PlayQueueResponse toPlaybackWindow() => PlayQueueResponse(
    // Distinct sentinel: do not accidentally query Plex /playQueues/-2.
    playQueueID: -2,
    playQueueSelectedItemID: currentIndex + 1,
    playQueueShuffled: shuffled,
    playQueueTotalCount: total,
    size: items.length,
    items: items.map((item) => item.toQueueItem()).toList(growable: false),
  );
}

/// All HTTP operations are finite, capped and initiated by a real transfer.
/// No sockets, timers, background polling or huge queue objects remain active.
class PowerLinkTransferClient {
  PowerLinkTransferClient(this.request);

  final PowerLinkRequest request;

  Future<PowerLinkQueueWindow> fetch(int start, {int count = 32}) async {
    if (start < 0 || count < 1 || count > 32) {
      throw const FormatException('Invalid queue window request');
    }
    final bytes = await _request('GET', request.windowUri(start, count));
    return PowerLinkQueueWindow.parse(jsonDecode(utf8.decode(bytes)));
  }

  Future<void> acknowledge(String status) async {
    if (status != 'started' && status != 'failed') {
      throw const FormatException('Invalid transfer acknowledgment');
    }
    await _request('POST', request.ackUri(), body: jsonEncode({'status': status}));
  }

  Future<List<int>> _request(String method, Uri url, {String? body}) async {
    final client = http.Client();
    try {
      return await () async {
        final message = http.Request(method, url);
        message.headers['Accept'] = 'application/json';
        if (body != null) {
          message.headers['Content-Type'] = 'application/json';
          message.body = body;
        }
        final response = await client.send(message);
        if (response.statusCode < 200 || response.statusCode >= 300) {
          throw const FormatException('PowerLink transfer request was rejected');
        }
        final data = <int>[];
        await for (final chunk in response.stream) {
          data.addAll(chunk);
          if (data.length > 192 * 1024) {
            throw const FormatException('PowerLink response exceeded its size limit');
          }
        }
        return data;
      }().timeout(const Duration(seconds: 12));
    } finally {
      client.close();
    }
  }
}
