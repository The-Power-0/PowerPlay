import 'package:flutter_test/flutter_test.dart';
import 'package:plezy/services/settings_service.dart';

import '../test_helpers/prefs.dart';

void main() {
  setUp(() {
    resetSharedPreferencesForTest();
  });

  test('PowerPlay defaults apply to a fresh store and honor the existing reset policy', () async {
    final settings = await SettingsService.getInstance();
    void expectDefaults() {
      expect(settings.read(SettingsService.continueWatchingAction), ContinueWatchingAction.details);
      expect(settings.read(SettingsService.episodeAction), EpisodeAction.details);
      expect(settings.read(SettingsService.matchContentFrameRate), isTrue);
      expect(settings.read(SettingsService.skipIntroMode), SkipMarkerMode.auto);
      expect(settings.read(SettingsService.autoSkipDelay), 3);
      expect(settings.read(SettingsService.skipCreditsMode), SkipMarkerMode.button);
    }

    expectDefaults();
    await settings.write(SettingsService.continueWatchingAction, ContinueWatchingAction.play);
    await settings.write(SettingsService.episodeAction, EpisodeAction.play);
    await settings.write(SettingsService.matchContentFrameRate, false);
    await settings.write(SettingsService.skipIntroMode, SkipMarkerMode.button);
    await settings.write(SettingsService.autoSkipDelay, 5);
    await settings.resetAllSettings();
    expect(settings.read(SettingsService.continueWatchingAction), ContinueWatchingAction.details);
    expect(settings.read(SettingsService.episodeAction), EpisodeAction.details);
    expect(settings.read(SettingsService.matchContentFrameRate), isTrue);
    // Intro mode and delay are portable-only preferences in the existing app;
    // Reset All Settings deliberately preserves these saved choices.
    expect(settings.read(SettingsService.skipIntroMode), SkipMarkerMode.button);
    expect(settings.read(SettingsService.autoSkipDelay), 5);
  });

  test('upgrading preserves every explicitly saved choice', () async {
    resetSharedPreferencesForTest(initialAsync: const {
      'continue_watching_action': 'play',
      'episode_action': 'play',
      'match_content_frame_rate': false,
      'skip_intro_mode': 'button',
      'auto_skip_delay': 5,
    });
    final settings = await SettingsService.getInstance();
    expect(settings.read(SettingsService.continueWatchingAction), ContinueWatchingAction.play);
    expect(settings.read(SettingsService.episodeAction), EpisodeAction.play);
    expect(settings.read(SettingsService.matchContentFrameRate), isFalse);
    expect(settings.read(SettingsService.skipIntroMode), SkipMarkerMode.button);
    expect(settings.read(SettingsService.autoSkipDelay), 5);
  });

  test('a saved legacy false intro choice still migrates to button mode', () async {
    resetSharedPreferencesForTest(initialAsync: const {'auto_skip_intro': false});
    final settings = await SettingsService.getInstance();
    expect(settings.read(SettingsService.skipIntroMode), SkipMarkerMode.button);
  });
}
