import 'dart:async';

import 'package:flutter/material.dart';
import 'package:material_symbols_icons/symbols.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:provider/provider.dart';

import '../../focus/focusable_button.dart';
import '../../focus/focusable_wrapper.dart';
import '../../profiles/active_profile_provider.dart';
import '../deep_links/deep_link.dart';
import '../../services/playback_coordinator.dart';
import 'powerlink_app_client.dart';
import '../powershuffle/powershuffle_session.dart';

/// Fire TV D-pad dialog: only queries HA when opened, never in background.
class PowerLinkHandoffPicker extends StatefulWidget {
  const PowerLinkHandoffPicker({super.key, this.credentials, this.client});

  /// Optional dependencies allow the Fire TV focus flow to be tested with a
  /// deterministic, authenticated Home Assistant destination list.
  final PowerLinkAppCredentials? credentials;
  final PowerLinkAppClient? client;

  static Future<void> show(BuildContext context) => showDialog<void>(
    context: context,
    builder: (_) => const PowerLinkHandoffPicker(),
  );

  @override
  State<PowerLinkHandoffPicker> createState() => _PowerLinkHandoffPickerState();
}

class _PowerLinkHandoffPickerState extends State<PowerLinkHandoffPicker> {
  late final PowerLinkAppCredentials _store = widget.credentials ?? PowerLinkAppCredentials();
  late final PowerLinkAppClient _api = widget.client ?? const PowerLinkAppClient();
  final _destinationFocusNodes = <String, FocusNode>{};
  final _refreshFocus = FocusNode(debugLabel: 'PowerLink Refresh');
  final _cancelFocus = FocusNode(debugLabel: 'PowerLink Cancel');
  PowerLinkAppIdentity? _identity;
  PowerLinkDeviceList? _devices;
  bool _loading = true;
  bool _sending = false;
  String? _sendingDestination;
  String? _error;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  @override
  void dispose() {
    for (final node in _destinationFocusNodes.values) {
      node.dispose();
    }
    _refreshFocus.dispose();
    _cancelFocus.dispose();
    super.dispose();
  }

  FocusNode _nodeFor(PowerLinkDestination device) =>
      _destinationFocusNodes.putIfAbsent(
        device.entityId,
        () => FocusNode(debugLabel: 'PowerLink ${device.name}'),
      );

  void _focusAfterDiscovery(PowerLinkDeviceList? list) {
    final firstAvailable = list?.destinations.where((device) => device.available).firstOrNull;
    // The devices are inserted *after* the HTTP call, not when the dialog
    // opens. A post-frame focus request places D-pad focus inside the modal
    // route instead of leaving it on the underlying video player.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || _sending) return;
      if (firstAvailable != null) {
        _nodeFor(firstAvailable).requestFocus();
      } else {
        _refreshFocus.requestFocus();
      }
    });
  }

  Future<void> _refresh() async {
    if (_sending) return;
    setState(() { _loading = true; _error = null; });
    try {
      final identity = await _store.load();
      if (!mounted) return;
      if (identity == null) {
        setState(() { _identity = null; _devices = null; });
        _focusAfterDiscovery(null);
        return;
      }
      final devices = await _api.discover(identity);
      if (!mounted) return;
      for (final device in devices.destinations) {
        if (device.available) _nodeFor(device);
      }
      setState(() { _identity = identity; _devices = devices; });
      _focusAfterDiscovery(devices);
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _devices = null;
        _error = error is FormatException
            ? error.message.toString()
            : 'Cannot reach PowerLink in Home Assistant.';
      });
      _focusAfterDiscovery(null);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _send(PowerLinkDestination device) async {
    if (_sending || !device.available) return;
    final identity = _identity;
    if (identity == null) return;
    // Take a fresh playhead at the moment of clicking the destination, not
    // when the picker was opened. The player continues until the new device
    // has actually begun playing and HA acknowledges it.
    final snapshot = PlaybackCoordinator.instance.capturePowerLinkQueue();
    if (snapshot == null) {
      setState(() => _error = 'Start a movie or TV queue before transferring playback.');
      return;
    }
    final profile = context.read<ActiveProfileProvider>().active;
    if (profile == null) {
      setState(() => _error = 'Select a Plex Home profile first.');
      return;
    }
    setState(() {
      _sending = true;
      _sendingDestination = device.name;
      _error = null;
    });
    try {
      // The native capture above carries the exact playhead. Flush the
      // separate PowerShuffle coverage ledger before ownership changes.
      // This is a no-op for ordinary Plex or normal Shuffle handoffs.
      await PowerShuffleSession.instance.flushBeforeHandoff();
      await _api.initiateHandoff(identity, destination: device.entityId, snapshot: {
        ...snapshot,
        'source_device': identity.sourceDevice,
        'profile_id': linkProfileRef(profile),
      });
      if (!mounted) return;
      final messenger = ScaffoldMessenger.maybeOf(context);
      Navigator.of(context).pop();
      messenger?.showSnackBar(SnackBar(
        content: Text('Starting playback on ${device.name}. This Fire Stick will pause after the handoff is confirmed.'),
      ));
    } catch (err) {
      if (mounted) {
        setState(() => _error = err is TimeoutException
            ? 'Home Assistant may still be waking this TV. Check the destination before retrying; the source only pauses after verified playback.'
            : err is FormatException
                ? err.message.toString()
                : 'Handoff failed or could not be confirmed. Check the destination before retrying.');
      }
    } finally {
      if (mounted) {
        setState(() {
          _sending = false;
          _sendingDestination = null;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final devices = _devices?.destinations ?? const <PowerLinkDestination>[];
    final available = devices.where((device) => device.available).toList(growable: false);
    final lastAvailableFocus = available.isEmpty ? _refreshFocus : _nodeFor(available.last);
    return AlertDialog(
      title: const Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          SvgPicture.asset('assets/brand/powerlink-mark.svg', width: 24, height: 24, colorFilter: ColorFilter.mode(Theme.of(context).colorScheme.primary, BlendMode.srcIn)),
          SizedBox(width: 12),
          Text('PowerLink · Move playback'),
        ],
      ),
      content: SizedBox(
        width: 520,
        height: 330,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Choose a Home Assistant room. The exact queue, shuffle order '
              'and playback position will transfer. This TV pauses only after '
              'the destination confirms playback.',
            ),
            const SizedBox(height: 12),
            if (_loading)
              const Expanded(child: Center(child: CircularProgressIndicator()))
            else if (_identity == null)
              const Expanded(child: Center(
                child: Text('Pair this Fire Stick under Settings → PowerLink first.'),
              ))
            else if (devices.isEmpty)
              const Expanded(child: Center(
                child: Text('No other PowerLink destinations are registered and verified.'),
              ))
            else
              Expanded(
                child: ListView.builder(
                  itemCount: devices.length,
                  itemBuilder: (context, index) {
                    final d = devices[index];
                    final availableIndex = available.indexWhere((device) => device.entityId == d.entityId);
                    return FocusableWrapper(
                      key: ValueKey('powerlink_destination_${d.entityId}'),
                      focusNode: d.available ? _nodeFor(d) : null,
                      canRequestFocus: !_sending && d.available,
                      descendantsAreFocusable: false,
                      disableScale: true,
                      useBackgroundFocus: true,
                      borderRadius: 12,
                      semanticLabel: 'Move playback to ${d.name}',
                      onSelect: d.available && !_sending ? () => _send(d) : null,
                      onNavigateUp: d.available && availableIndex > 0
                          ? () => _nodeFor(available[availableIndex - 1]).requestFocus()
                          : null,
                      onNavigateDown: d.available && !_sending
                          ? () => availableIndex + 1 < available.length
                              ? _nodeFor(available[availableIndex + 1]).requestFocus()
                              : _refreshFocus.requestFocus()
                          : null,
                      onNavigateRight: d.available && !_sending
                          ? _refreshFocus.requestFocus
                          : null,
                      child: ListTile(
                        leading: const Icon(Symbols.tv_rounded),
                        title: Text(d.name),
                        subtitle: Text(d.maxHeight >= 2160 ? '4K-capable Fire TV' : 'HD Fire TV'),
                        trailing: d.available
                            ? const Icon(Symbols.arrow_forward_rounded)
                            : const Text('Unavailable'),
                        enabled: d.available,
                      ),
                    );
                  },
                ),
              ),
            if (_sending) ...[
              const SizedBox(height: 12),
              Text('Home Assistant is preparing and waking ${_sendingDestination ?? 'the destination'}. Playback continues here until confirmed.'),
              const SizedBox(height: 8),
              const LinearProgressIndicator(),
            ],
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  _error!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ),
          ],
        ),
      ),
      actions: [
        FocusableButton(
          focusNode: _refreshFocus,
          onPressed: _sending ? null : _refresh,
          onNavigateUp: () => lastAvailableFocus.requestFocus(),
          onNavigateRight: _cancelFocus.requestFocus,
          child: TextButton(
            onPressed: _sending ? null : _refresh,
            child: const Text('Refresh'),
          ),
        ),
        FocusableButton(
          focusNode: _cancelFocus,
          onPressed: _sending ? null : () => Navigator.of(context).pop(),
          onNavigateUp: () => lastAvailableFocus.requestFocus(),
          onNavigateLeft: _refreshFocus.requestFocus,
          child: TextButton(
            onPressed: _sending ? null : () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
        ),
      ],
    );
  }
}
