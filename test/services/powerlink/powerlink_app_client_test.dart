import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:plezy/services/powerlink/powerlink_app_client.dart';

void main() {
  const source = 'media_player.bedroom_fire_tv_stick_lite';
  const destination = 'media_player.living_room_fire_tv_stick_4k_plus';
  final base = Uri.parse('http://192.168.1.20:8123');
  final token = List.filled(43, 'a').join();
  final identity = PowerLinkAppIdentity(
    base: base, sourceDevice: source,
    sourceName: 'Bedroom', token: token,
  );

  test('pairs by a short-lived code without an HA admin token', () async {
    var calls = 0;
    final client = PowerLinkAppClient(client: MockClient((request) async {
      calls++;
      expect(request.url.path, '/api/powerlink/v1/app/pair');
      expect(request.method, 'POST');
      expect(request.headers.containsKey('Authorization'), false);
      expect(jsonDecode(request.body)['code'], '123456789');
      return http.Response(jsonEncode({
        'protocol': 2,
        'source_device': source,
        'source_name': 'Bedroom',
        'token': token,
      }), 200);
    }));
    final paired = await client.pair(base, '123456789');
    expect(paired.sourceDevice, source);
    expect(paired.token, token);
    expect(calls, 1);
  });

  test('discovery returns only named registered targets and keeps token in header', () async {
    var calls = 0;
    final client = PowerLinkAppClient(client: MockClient((request) async {
      calls++;
      expect(request.method, 'GET');
      expect(request.url.path, '/api/powerlink/v1/app/devices');
      expect(request.headers['X-PowerLink-Device'], source);
      expect(request.headers['X-PowerLink-Token'], token);
      expect(request.headers.containsKey('Authorization'), false);
      return http.Response(jsonEncode({
        'protocol': 2, 'source_device': source,
        'destinations': [
          {'entity_id': destination, 'name': 'Living Room',
           'max_height': 2160, 'available': true},
        ],
      }), 200);
    }));
    final result = await client.discover(identity);
    expect(result.destinations.length, 1);
    expect(result.destinations.single.name, 'Living Room');
    expect(result.destinations.single.maxHeight, 2160);
    expect(calls, 1);
  });

  test('handoff posts exact snapshot only on user action and does not stop source', () async {
    var calls = 0;
    final client = PowerLinkAppClient(client: MockClient((request) async {
      calls++;
      expect(request.url.path, '/api/powerlink/v1/app/handoff');
      final data = jsonDecode(request.body) as Map<String, dynamic>;
      expect(data['destination'], destination);
      expect(data['snapshot']['source_device'], source);
      expect(data['snapshot']['queue_source']['play_queue_id'], 555);
      expect(data['snapshot']['position_ms'], 423000);
      expect(data['snapshot']['shuffled'], true);
      expect(request.headers['X-PowerLink-Token'], token);
      return http.Response(jsonEncode({'accepted': true, 'destination': destination}), 200);
    }));
    await client.initiateHandoff(identity, destination: destination, snapshot: {
      'schema': 1, 'source_device': source, 'profile_id': 'plex-home-user',
      'queue_source': {'type': 'plex_play_queue', 'play_queue_id': 555,
                       'selected_item_id': 91, 'server_id': 'plex-main'},
      'position_ms': 423000, 'shuffled': true,
    });
    expect(calls, 1);
  });

  test('never follows an HTTP redirect with a scoped PowerLink token', () async {
    var calls = 0;
    final client = PowerLinkAppClient(client: MockClient((request) async {
      calls++;
      expect(request.followRedirects, isFalse);
      expect(request.headers['X-PowerLink-Token'], token);
      return http.Response('', 302,
          headers: {'location': 'https://another-host.example/capture'});
    }));
    await expectLater(client.discover(identity), throwsFormatException);
    expect(calls, 1);
  });

  test('rejects redirect/insecure public HTTP and invalid code', () async {
    const client = PowerLinkAppClient();
    await expectLater(
      client.pair(Uri.parse('http://example.net'), '123456789'),
      throwsFormatException,
    );
    await expectLater(client.pair(base, '123'), throwsFormatException);
  });

  test('rejects devices list containing the source device itself', () {
    expect(() => PowerLinkDeviceList.fromJson({
      'protocol': 2, 'source_device': source,
      'destinations': [
        {'entity_id': source, 'name': 'Bedroom',
         'max_height': 1080, 'available': true},
      ],
    }), throwsFormatException);
  });

  test('rejects pairing to an unsupported protocol or malformed destinations', () {
    expect(() => PowerLinkDeviceList.fromJson({
      'protocol': 1, 'source_device': source, 'destinations': [],
    }), throwsFormatException);
    expect(() => PowerLinkDestination.fromJson({
      'entity_id': 'bad name', 'name': 'Bedroom',
      'max_height': -1, 'available': true,
    }), throwsFormatException);
  });

  test('handoff refuses the same source or mismatched snapshot without network call', () async {
    const client = PowerLinkAppClient();
    await expectLater(
      client.initiateHandoff(identity, destination: source,
                            snapshot: {'schema': 1, 'source_device': source}),
      throwsFormatException,
    );
    await expectLater(
      client.initiateHandoff(identity, destination: destination,
                            snapshot: {'schema': 1, 'source_device': 'media_player.fake'}),
      throwsFormatException,
    );
  });
}
