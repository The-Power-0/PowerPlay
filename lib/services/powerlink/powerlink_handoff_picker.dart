import 'package:flutter/material.dart';
import 'package:material_symbols_icons/symbols.dart';
import 'package:provider/provider.dart';

import '../../profiles/active_profile_provider.dart';
import '../../services/playback_coordinator.dart';
import 'powerlink_app_client.dart';

/// Fire TV D-pad dialog: only queries HA when opened, never in background.
class PowerLinkHandoffPicker extends StatefulWidget {
  const PowerLinkHandoffPicker({super.key});

  static Future<void> show(BuildContext context) => showDialog<void>(
    context: context,
    builder: (_) => const PowerLinkHandoffPicker(),
  );

  @override
  State<PowerLinkHandoffPicker> createState() => _PowerLinkHandoffPickerState();
}

class _PowerLinkHandoffPickerState extends State<PowerLinkHandoffPicker> {
  final _store = PowerLinkAppCredentials();
  final _api = const PowerLinkAppClient();
  PowerLinkAppIdentity? _identity;
  PowerLinkDeviceList? _devices;
  bool _loading = true;
  bool _sending = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  Future<void> _refresh() async {
    if (_sending) return;
    setState(() { _loading = true; _error = null; });
    try {
      final identity = await _store.load();
      if (!mounted) return;
      if (identity == null) {
        setState(() { _identity = null; _devices = null; });
        return;
      }
      final devices = await _api.discover(identity);
      if (!mounted) return;
      setState(() { _identity = identity; _devices = devices; });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _devices = null;
        _error = error is FormatException
            ? error.message.toString()
            : 'Cannot reach PowerLink in Home Assistant.';
      });
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
    setState(() { _sending = true; _error = null; });
    try {
      await _api.initiateHandoff(identity, destination: device.entityId, snapshot: {
        ...snapshot,
        'source_device': identity.sourceDevice,
        'profile_id': linkProfileRef(profile),
      });
      if (!mounted) return;
      Navigator.of(context).pop();
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(SnackBar(
        content: Text('Starting playback on ' + device.name +
            '. This Fire Stick will pause after the handoff is confirmed.'),
      ));
    } catch (err) {
      if (mounted) {
        setState(() => _error = err is FormatException
            ? err.message.toString()
            : 'Handoff failed. Current playback was not stopped.');
      }
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final devices = _devices?.destinations ?? const <PowerLinkDestination>[];
    return AlertDialog(
      title: const Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Symbols.cast_rounded),
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
                    return ListTile(
                      leading: const Icon(Symbols.tv_rounded),
                      title: Text(d.name),
                      subtitle: Text(d.maxHeight >= 2160 ? '4K-capable Fire TV' : 'HD Fire TV'),
                      trailing: d.available
                          ? const Icon(Symbols.arrow_forward_rounded)
                          : const Text('Unavailable'),
                      enabled: !_sending && d.available,
                      onTap: () => _send(d),
                    );
                  },
                ),
              ),
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
        TextButton(
          onPressed: _sending ? null : _refresh,
          child: const Text('Refresh'),
        ),
        TextButton(
          onPressed: _sending ? null : () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
      ],
    );
  }
}
