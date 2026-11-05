import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../focus/focusable_text_field.dart';
import '../../services/powerlink/powerlink_app_client.dart';
import '../../widgets/focusable_list_tile.dart';
import '../../widgets/settings_page.dart';
import '../../widgets/settings_section.dart';

/// PowerLink setup is performed once per Fire Stick, not per media profile.
/// HA chooses which *registered* media_player is bound to this app through an
/// administrator-generated, short-lived pairing code.
class PowerLinkSettingsScreen extends StatefulWidget {
  const PowerLinkSettingsScreen({super.key});

  @override
  State<PowerLinkSettingsScreen> createState() => _PowerLinkSettingsScreenState();
}

class _PowerLinkSettingsScreenState extends State<PowerLinkSettingsScreen> {
  final _url = TextEditingController();
  final _code = TextEditingController();
  // Fire TV needs a managed native IME session and explicit focus targets.
  final _urlFocus = FocusNode(debugLabel: 'PowerLink URL');
  final _codeFocus = FocusNode(debugLabel: 'PowerLink pairing code');
  final _pairFocus = FocusNode(debugLabel: 'PowerLink pair action');
  final _refreshFocus = FocusNode(debugLabel: 'PowerLink refresh');
  final _disconnectFocus = FocusNode(debugLabel: 'PowerLink disconnect');
  final _urlInput = TvTextInputController();
  final _codeInput = TvTextInputController();

  void _focusCode() => _codeInput.focusInputWithoutOpening();
  void _focusUrl() => _urlInput.focusInputWithoutOpening();
  void _focusPair() => _pairFocus.requestFocus();
  final _credentials = PowerLinkAppCredentials();
  final _api = const PowerLinkAppClient();

  PowerLinkAppIdentity? _identity;
  PowerLinkDeviceList? _devices;
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _restore();
  }

  @override
  void dispose() {
    _url.dispose();
    _code.dispose();
    _urlFocus.dispose();
    _codeFocus.dispose();
    _pairFocus.dispose();
    _refreshFocus.dispose();
    _disconnectFocus.dispose();
    super.dispose();
  }

  Future<void> _restore() async {
    try {
      final identity = await _credentials.load();
      if (!mounted) return;
      setState(() {
        _identity = identity;
        if (identity != null) _url.text = identity.base.toString();
      });
      if (identity != null) await _refresh();
    } catch (_) {
      if (mounted) setState(() => _error = 'Unable to open secure device pairing storage.');
    }
  }

  Future<void> _pair() async {
    if (_busy) return;
    setState(() { _busy = true; _error = null; });
    try {
      final input = _url.text.trim().replaceAll(RegExp(r'/$'), '');
      final url = Uri.tryParse(input);
      if (url == null) throw const FormatException('Enter a valid Home Assistant URL');
      final identity = await _api.pair(url, _code.text.trim());
      await _credentials.save(identity);
      if (!mounted) return;
      _code.clear();
      setState(() { _identity = identity; _devices = null; });
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _refreshFocus.requestFocus();
      });
      await _refresh();
    } catch (err) {
      if (mounted) {
        setState(() => _error = err is FormatException
            ? err.message.toString()
            : 'PowerLink is unreachable. Check your Home Assistant URL and pairing code.');
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _refresh() async {
    final identity = _identity;
    if (identity == null) return;
    try {
      final destinations = await _api.discover(identity);
      if (mounted) setState(() { _devices = destinations; _error = null; });
    } catch (err) {
      if (mounted) {
        setState(() {
          _devices = null;
          _error = err is FormatException
            ? err.message.toString()
            : 'Unable to discover registered PowerLink devices.';
        });
      }
    }
  }

  Future<void> _disconnect() async {
    if (_busy) return;
    setState(() { _busy = true; _error = null; });
    try {
      await _credentials.disconnect();
      if (mounted) {
        setState(() { _identity = null; _devices = null; });
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (mounted) _focusUrl();
        });
      }
    } catch (_) {
      if (mounted) setState(() => _error = 'Could not clear PowerLink credentials.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final identity = _identity;
    return SettingsPage(
      title: const Text('PowerLink'),
      children: [
        SettingsGroup(
          title: 'Home Assistant connection',
          children: [
            const ListTile(
              leading: Icon(Symbols.cast_rounded),
              title: Text('Room-to-room playback'),
              subtitle: Text(
                'PowerLink lists only the devices registered in Home Assistant. '
                'No network scan or background polling runs on this Fire Stick.',
              ),
            ),
            if (identity == null) ...[
              Padding(
                padding: const EdgeInsets.all(16),
                child: FocusableTextField(
                  key: const Key('powerlink_url_field'),
                  controller: _url,
                  focusNode: _urlFocus,
                  tvTextInputController: _urlInput,
                  // Traversal must not re-open the native keyboard.
                  tvTextInputAutoOpenBehavior: TvTextInputAutoOpenBehavior.never,
                  keyboardType: TextInputType.url,
                  onNavigateDown: _focusCode,
                  onSubmitted: (_) => _focusCode(),
                  decoration: const InputDecoration(
                    labelText: 'Home Assistant URL',
                    hintText: 'http://homeassistant.local:8123',
                  ),
                  textInputAction: TextInputAction.next,
                ),
              ),
              Padding(
                padding: const EdgeInsets.all(16),
                child: FocusableTextField(
                  key: const Key('powerlink_code_field'),
                  controller: _code,
                  focusNode: _codeFocus,
                  tvTextInputController: _codeInput,
                  tvTextInputAutoOpenBehavior: TvTextInputAutoOpenBehavior.never,
                  keyboardType: TextInputType.number,
                  inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                  textInputAction: TextInputAction.done,
                  onNavigateUp: _focusUrl,
                  onNavigateDown: _focusPair,
                  onSubmitted: (_) => _focusPair(),
                  maxLength: 9,
                  decoration: const InputDecoration(
                    labelText: 'Nine-digit pairing code',
                  ),
                ),
              ),
              const ListTile(
                title: Text('Get your code in Home Assistant'),
                subtitle: Text(
                  'Settings → Devices & services → PowerLink → Configure → '
                  'Pair PowerPlay player. Choose this Fire Stick, then enter '
                  'the one-time code above within three minutes.',
                ),
              ),
              FocusableListTile(
                key: const Key('powerlink_pair_button'),
                focusNode: _pairFocus,
                leading: const Icon(Symbols.link_rounded),
                title: const Text('Pair this Fire Stick'),
                trailing: _busy ? const CircularProgressIndicator() : null,
                enabled: !_busy,
                onTap: _pair,
              ),
            ] else ...[
              ListTile(
                leading: const Icon(Symbols.check_circle_rounded),
                title: Text('Paired: ${identity.sourceName}'),
                subtitle: Text('${identity.sourceDevice}\n${identity.base}'),
                isThreeLine: true,
              ),
              FocusableListTile(
                focusNode: _refreshFocus,
                leading: const Icon(Symbols.refresh_rounded),
                title: const Text('Refresh PowerLink destinations'),
                enabled: !_busy,
                onTap: _refresh,
              ),
              FocusableListTile(
                focusNode: _disconnectFocus,
                leading: const Icon(Symbols.link_off_rounded),
                title: const Text('Disconnect this Fire Stick'),
                subtitle: const Text('Re-pair to bind a different Home Assistant device.'),
                enabled: !_busy,
                onTap: _disconnect,
              ),
            ],
          ],
        ),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.all(16),
            child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
          ),
        if (identity != null)
          SettingsGroup(
            title: 'Registered destinations',
            children: [
              if (_devices == null)
                const ListTile(title: Text('Use Refresh to check Home Assistant connectivity.'))
              else if (_devices!.destinations.isEmpty)
                const ListTile(title: Text('No other verified PowerLink devices')),
              for (final device in _devices?.destinations ?? const <PowerLinkDestination>[])
                ListTile(
                  leading: const Icon(Symbols.tv_rounded),
                  title: Text(device.name),
                  subtitle: Text(device.entityId),
                  trailing: Text(
                    device.available
                        ? (device.maxHeight >= 2160 ? '4K' : 'HD')
                        : 'Unavailable',
                  ),
                ),
            ],
          ),
        const SizedBox(height: 24),
      ],
    );
  }
}
