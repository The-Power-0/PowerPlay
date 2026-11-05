import 'dart:async';
import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

import 'powerlink_transfer.dart';

/// Scoped per-Fire-Stick HA credential stored in Android Keystore encryption.
class PowerLinkAppIdentity {
  const PowerLinkAppIdentity({
    required this.base, required this.sourceDevice,
    required this.sourceName, required this.token,
  });

  final Uri base;
  final String sourceDevice;
  final String sourceName;
  final String token;
}

class PowerLinkAppCredentials {
  PowerLinkAppCredentials({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _storage;
  static const _url = 'powerlink.app.base';
  static const _source = 'powerlink.app.source';
  static const _name = 'powerlink.app.name';
  static const _token = 'powerlink.app.token';

  Future<PowerLinkAppIdentity?> load() async {
    final url = await _storage.read(key: _url);
    final source = await _storage.read(key: _source);
    final name = await _storage.read(key: _name);
    final token = await _storage.read(key: _token);
    if (url == null || source == null || name == null || token == null) return null;
    final base = Uri.tryParse(url);
    if (base == null || !PowerLinkRequest.validEndpoint(base) ||
        source.isEmpty || token.length < 40) {
      return null;
    }
    return PowerLinkAppIdentity(
      base: base, sourceDevice: source, sourceName: name, token: token,
    );
  }

  Future<void> save(PowerLinkAppIdentity identity) async {
    await _storage.write(key: _url, value: identity.base.toString());
    await _storage.write(key: _source, value: identity.sourceDevice);
    await _storage.write(key: _name, value: identity.sourceName);
    await _storage.write(key: _token, value: identity.token);
  }

  Future<void> disconnect() async {
    await _storage.delete(key: _token);
    await _storage.delete(key: _source);
    await _storage.delete(key: _name);
    await _storage.delete(key: _url);
  }
}

class PowerLinkDestination {
  const PowerLinkDestination({
    required this.entityId, required this.name,
    required this.maxHeight, required this.available,
  });

  final String entityId;
  final String name;
  final int maxHeight;
  final bool available;

  factory PowerLinkDestination.fromJson(Object? value) {
    if (value is! Map<String, dynamic>) throw const FormatException('Invalid destination');
    final id = value['entity_id'];
    final name = value['name'];
    final height = value['max_height'];
    final available = value['available'];
    if (id is! String || !(id.startsWith('media_player.') || id.startsWith('remote.')) ||
        name is! String || name.isEmpty || height is! int || height < 1 ||
        available is! bool) {
      throw const FormatException('Invalid destination properties');
    }
    return PowerLinkDestination(
      entityId: id, name: name, maxHeight: height, available: available,
    );
  }
}

class PowerLinkDeviceList {
  const PowerLinkDeviceList({required this.sourceDevice, required this.destinations});
  final String sourceDevice;
  final List<PowerLinkDestination> destinations;

  factory PowerLinkDeviceList.fromJson(Object? json) {
    if (json is! Map<String, dynamic> || json['protocol'] != 2 ||
        json['source_device'] is! String || json['destinations'] is! List) {
      throw const FormatException('Incompatible PowerLink device list');
    }
    final rows = json['destinations'] as List;
    if (rows.length > 100) throw const FormatException('Too many destinations');
    final source = json['source_device'] as String;
    final destinations = rows.map(PowerLinkDestination.fromJson).toList(growable: false);
    if (destinations.any((d) => d.entityId == source)) {
      throw const FormatException('PowerLink cannot target its own source');
    }
    return PowerLinkDeviceList(sourceDevice: source, destinations: destinations);
  }
}

class PowerLinkAppClient {
  const PowerLinkAppClient({http.Client? client}) : _testClient = client;

  // A verified HA wake script can legitimately take up to 600 seconds.
  // Include time for Plex queue preparation and the destination launch;
  // this timeout is not a playback acknowledgment or a cancellation signal.
  static const handoffRequestTimeout = Duration(minutes: 11);

  // Injectable only for tests/authorized transports; production opens a
  // short-lived client per explicit user action and closes it afterwards.
  final http.Client? _testClient;

  static Uri _api(Uri base, String path) => base.replace(path: path);

  Future<PowerLinkAppIdentity> pair(Uri base, String code) async {
    if (!PowerLinkRequest.validEndpoint(base)) {
      throw const FormatException('Use a local HA URL or HTTPS');
    }
    if (!RegExp(r'^[0-9]{9}$').hasMatch(code)) {
      throw const FormatException('Enter the nine-digit PowerLink pairing code');
    }
    final json = await _request(
      _api(base, '/api/powerlink/v1/app/pair'),
      method: 'POST', payload: {'code': code},
    );
    if (json['protocol'] != 2 || json['source_device'] is! String ||
        json['source_name'] is! String || json['token'] is! String ||
        (json['token'] as String).length < 40) {
      throw const FormatException('Unexpected HA pairing response');
    }
    return PowerLinkAppIdentity(
      base: base,
      sourceDevice: json['source_device'] as String,
      sourceName: json['source_name'] as String,
      token: json['token'] as String,
    );
  }

  Future<PowerLinkDeviceList> discover(PowerLinkAppIdentity identity) async {
    final json = await _request(
      _api(identity.base, '/api/powerlink/v1/app/devices'),
      identity: identity,
    );
    final result = PowerLinkDeviceList.fromJson(json);
    if (result.sourceDevice != identity.sourceDevice) {
      throw const FormatException('Device pairing identity changed');
    }
    return result;
  }

  Future<void> initiateHandoff(
    PowerLinkAppIdentity identity, {
    required String destination,
    required Map<String, dynamic> snapshot,
  }) async {
    if (destination == identity.sourceDevice) throw const FormatException('Choose another room');
    if (snapshot['schema'] != 1 || snapshot['source_device'] != identity.sourceDevice) {
      throw const FormatException('Invalid current playback snapshot');
    }
    final result = await _request(
      _api(identity.base, '/api/powerlink/v1/app/handoff'),
      identity: identity, method: 'POST',
      payload: {'destination': destination, 'snapshot': snapshot},
      timeout: handoffRequestTimeout,
    );
    if (result['accepted'] != true || result['destination'] != destination) {
      throw const FormatException('Home Assistant did not accept the handoff');
    }
  }

  Future<Map<String, dynamic>> _request(
    Uri url, {
    PowerLinkAppIdentity? identity,
    String method = 'GET',
    Map<String, dynamic>? payload,
    Duration timeout = const Duration(seconds: 12),
  }) async {
    final client = _testClient ?? http.Client();
    try {
      return await () async {
        final request = http.Request(method, url);
        // Never forward a per-device credential through a reverse-proxy or
        // cross-origin redirect. Configure the final HA URL explicitly.
        request.followRedirects = false;
        request.headers['Accept'] = 'application/json';
        if (identity != null) {
          request.headers['X-PowerLink-Device'] = identity.sourceDevice;
          request.headers['X-PowerLink-Token'] = identity.token;
        }
        if (payload != null) {
          final body = jsonEncode(payload);
          if (utf8.encode(body).length > 2_000_000) {
            throw const FormatException('PowerLink snapshot too large');
          }
          request.headers['Content-Type'] = 'application/json';
          request.body = body;
        }
        final response = await client.send(request);
        if (response.statusCode == 401 || response.statusCode == 403) {
          throw const FormatException('Pair this Fire Stick again in PowerLink settings');
        }
        if (response.statusCode < 200 || response.statusCode >= 300) {
          throw FormatException('PowerLink request failed (HTTP ${response.statusCode})');
        }
        final bytes = <int>[];
        await for (final chunk in response.stream) {
          bytes.addAll(chunk);
          if (bytes.length > 65536) throw const FormatException('PowerLink response too large');
        }
        final decoded = jsonDecode(utf8.decode(bytes));
        if (decoded is! Map<String, dynamic>) {
          throw const FormatException('Invalid PowerLink server response');
        }
        return decoded;
      }().timeout(timeout);
    } finally {
      if (_testClient == null) client.close();
    }
  }
}
