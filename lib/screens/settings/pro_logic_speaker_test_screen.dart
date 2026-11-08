import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../widgets/focusable_list_tile.dart';
import '../../widgets/settings_page.dart';
import '../../widgets/settings_section.dart';

/// Manual verification of the *physical* Fire TV -> TV optical PCM -> DAC -> AVR
/// route. Exercises the same native Pro Logic matrix used during media playback.
/// Tests work even when the playback preference is switched off.
class ProLogicSpeakerTestScreen extends StatefulWidget {
  const ProLogicSpeakerTestScreen({super.key});

  @override
  State<ProLogicSpeakerTestScreen> createState() => _ProLogicSpeakerTestScreenState();
}

class _ProLogicSpeakerTestScreenState extends State<ProLogicSpeakerTestScreen> {
  static const _channel = MethodChannel('com.plezy/exo_player');
  String? _lastChannel;
  String? _error;
  bool _busy = false;

  Future<void> _play(String speaker) async {
    if (_busy) return;
    setState(() { _busy = true; _error = null; });
    try {
      final ok = await _channel.invokeMethod<bool>('startProLogicSpeakerTest', {'speaker': speaker});
      if (!mounted) return;
      setState(() {
        _lastChannel = ok == true ? speaker : null;
        if (ok != true) _error = 'Could not start PCM speaker test. Verify the audio output is available.';
      });
    } on PlatformException catch (e) {
      if (!mounted) return;
      setState(() { _error = 'Audio test failed: ${e.message ?? e.code}'; });
    } finally {
      if (mounted) setState(() { _busy = false; });
    }
  }

  Future<void> _stop() async {
    try {
      await _channel.invokeMethod<void>('stopProLogicSpeakerTest');
    } on PlatformException {
      // Leaving this screen also requests a stop.
    }
    if (mounted) setState(() { _lastChannel = null; });
  }

  @override
  void dispose() {
    // Fire-and-forget: native playback owns the worker and releases AudioTrack.
    _channel.invokeMethod<void>('stopProLogicSpeakerTest').catchError((Object _) {});
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SettingsPage(
      title: const Text('Pro Logic speaker test'),
      children: [
        const Padding(
          padding: EdgeInsets.all(16),
          child: Text(
            'Set the Fire TV and TV digital output to stereo PCM, turn off TV '
            'audio enhancements, and select Dolby Pro Logic on your receiver. '
            'Start at a modest volume. Each test plays a short tone through the '
            'same matrix encoder used for movies. The feature toggle can stay off.',
          ),
        ),
        SettingsGroup(
          title: 'Check each speaker',
          children: [
            _speakerTile('left', 'Front left', 'Tone should come primarily from the front-left speaker.', Symbols.volume_up_rounded),
            _speakerTile('center', 'Center', 'Tone should be steered primarily into the center speaker.', Symbols.speaker_rounded),
            _speakerTile('right', 'Front right', 'Tone should come primarily from the front-right speaker.', Symbols.volume_up_rounded),
            _speakerTile('surround', 'Rear surround (mono)', 'Both rear speakers should play the same tone. Some front leakage is normal.', Symbols.surround_sound_rounded),
            FocusableListTile(
              leading: const Icon(Symbols.stop_circle_rounded),
              title: const Text('Stop test tone'),
              onTap: _stop,
            ),
          ],
        ),
        if (_lastChannel != null)
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
            child: Text('Last test: ${_lastChannel!}. Select another channel to compare.',
                style: Theme.of(context).textTheme.bodySmall),
          ),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.all(16),
            child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
          ),
        const Padding(
          padding: EdgeInsets.all(16),
          child: Text(
            'This tests channel steering, not a discrete 5.1 decoder. Original '
            'Pro Logic uses a single mono rear channel and has no dedicated LFE '
            'channel. TV processing or an incorrect PCM setting can spoil rear '
            'steering. A test tone starting successfully does not prove the '
            'physical audio route is correct.',
          ),
        ),
      ],
    );
  }

  Widget _speakerTile(String id, String title, String subtitle, IconData icon) {
    return FocusableListTile(
      leading: Icon(icon),
      title: Text(title),
      subtitle: Text(subtitle),
      trailing: const Icon(Symbols.play_arrow_rounded),
      enabled: !_busy,
      onTap: () => _play(id),
    );
  }
}
