import 'package:flutter_test/flutter_test.dart';
import 'package:plezy/media/media_backend.dart';
import 'package:plezy/media/media_library.dart';
import 'package:plezy/providers/hidden_libraries_provider.dart';
import 'package:plezy/providers/libraries_provider.dart';
import 'package:plezy/services/storage_service.dart';
import 'package:plezy/utils/fire_tv_library_policy.dart';
import 'package:plezy/utils/platform_detector.dart';

import '../test_helpers/prefs.dart';

class _Libraries extends LibrariesProvider {
  List<MediaLibrary> items = [];
  @override
  List<MediaLibrary> get libraries => List.unmodifiable(items);

  void replace(List<MediaLibrary> next) {
    items = next;
    notifyListeners();
  }
}

MediaLibrary _library(String id, String title, {String serverId = 'plex'}) =>
    MediaLibrary(id: id, title: title, backend: MediaBackend.plex, serverId: serverId);

void main() {
  setUp(resetSharedPreferencesForTest);

  test('known Full HD sticks are recognized only with the Fire TV feature', () {
    for (final model in ['AFTSS', 'AFTSSS', 'AFTT', 'AFTM']) {
      expect(is1080pOnlyFireTvStick(isFireTv: true, model: model), isTrue);
      expect(is1080pOnlyFireTvStick(isFireTv: false, model: model), isFalse);
    }
    expect(is1080pOnlyFireTvStick(isFireTv: true, model: ' aftss '), isTrue);
  });

  test('4K sticks and unknown hardware never get a Full HD default', () {
    for (final model in ['AFTMA08C15', 'AFTKM', 'AFTKRT', 'AFTKA', 'AFTMM', 'future-model', '']) {
      expect(is1080pOnlyFireTvStick(isFireTv: true, model: model), isFalse);
    }
  });

  test('fallback feature detection carries hardware output and rejects automotive', () {
    final hd = detectAndroidTvFromSystemFeatures(['amazon.hardware.fire_tv'], model: 'AFTSS');
    expect(hd.is1080pOnlyFireStick, isTrue);
    final car = detectAndroidTvFromSystemFeatures(
      ['amazon.hardware.fire_tv', 'android.hardware.type.automotive'], model: 'AFTSS',
    );
    expect(car.is1080pOnlyFireStick, isFalse);
  });

  test('only a literal bracketed 4K marker matches, case insensitively', () {
    for (final title in ['Movies [4K]', 'TV Shows [4K]', '[4k] Movies']) {
      expect(hide4kLibraryByDefault(is1080pOnlyFireStick: true, title: title), isTrue);
    }
    for (final title in ['Movies', 'TV Shows', '4K Movies', 'Movies [4K HDR]', 'Movies [1080p]']) {
      expect(hide4kLibraryByDefault(is1080pOnlyFireStick: true, title: title), isFalse);
    }
    expect(hide4kLibraryByDefault(is1080pOnlyFireStick: false, title: 'Movies [4K]'), isFalse);
  });

  test('1080p defaults hide exactly the two 4K libraries without saving automatic choices', () async {
    final libraries = _Libraries()..items = [
      _library('1', 'Movies'), _library('2', 'TV Shows'),
      _library('3', 'Movies [4K]'), _library('4', 'TV Shows [4K]'),
    ];
    final hidden = HiddenLibrariesProvider(librariesProvider: libraries, hide4kByDefault: true);
    addTearDown(hidden.dispose);
    addTearDown(libraries.dispose);
    await hidden.ensureInitialized();
    expect(hidden.hiddenLibraryKeys, {'plex:3', 'plex:4'});
    expect((await StorageService.getInstance()).getHiddenLibraries(), isEmpty);
  });

  test('4K defaults keep every library visible and preserve manual hiding', () async {
    final libraries = _Libraries()..items = [_library('3', 'Movies [4K]'), _library('4', 'TV Shows [4K]')];
    final hidden = HiddenLibrariesProvider(librariesProvider: libraries, hide4kByDefault: false);
    addTearDown(hidden.dispose);
    addTearDown(libraries.dispose);
    await hidden.ensureInitialized();
    expect(hidden.hiddenLibraryKeys, isEmpty);
    await hidden.hideLibrary('plex:3');
    expect(hidden.hiddenLibraryKeys, {'plex:3'});
  });

  test('explicit Show survives reload and a new provider on a 1080p stick', () async {
    final libraries = _Libraries()..items = [_library('3', 'Movies [4K]')];
    addTearDown(libraries.dispose);
    final first = HiddenLibrariesProvider(librariesProvider: libraries, hide4kByDefault: true, profileId: 'owner');
    await first.ensureInitialized();
    await first.unhideLibrary('plex:3');
    await first.refresh();
    expect(first.hiddenLibraryKeys, isEmpty);
    first.dispose();
    final second = HiddenLibrariesProvider(librariesProvider: libraries, hide4kByDefault: true, profileId: 'owner');
    addTearDown(second.dispose);
    await second.ensureInitialized();
    expect(second.hiddenLibraryKeys, isEmpty);
    await second.hideLibrary('plex:3');
    expect(second.hiddenLibraryKeys, {'plex:3'});
  });

  test('visibility overrides are isolated by profile and server', () async {
    final libraries = _Libraries()..items = [
      _library('3', 'Movies [4K]'), _library('3', 'Movies [4K]', serverId: 'other'),
    ];
    addTearDown(libraries.dispose);
    final owner = HiddenLibrariesProvider(librariesProvider: libraries, hide4kByDefault: true, profileId: 'owner');
    final kids = HiddenLibrariesProvider(librariesProvider: libraries, hide4kByDefault: true, profileId: 'kids');
    addTearDown(owner.dispose);
    addTearDown(kids.dispose);
    await owner.unhideLibrary('plex:3');
    await kids.ensureInitialized();
    expect(owner.hiddenLibraryKeys, {'other:3'});
    expect(kids.hiddenLibraryKeys, {'plex:3', 'other:3'});
  });

  test('late libraries get defaults; renames remove only the automatic default', () async {
    final libraries = _Libraries();
    addTearDown(libraries.dispose);
    final hidden = HiddenLibrariesProvider(librariesProvider: libraries, hide4kByDefault: true);
    addTearDown(hidden.dispose);
    await hidden.ensureInitialized();
    var notifications = 0;
    hidden.addListener(() => notifications++);
    libraries.replace([_library('3', 'Movies [4K]')]);
    expect(hidden.hiddenLibraryKeys, {'plex:3'});
    expect(notifications, 1);
    libraries.replace([_library('3', 'Movies [4K]')]);
    expect(notifications, 1);
    libraries.replace([_library('3', 'Movies')]);
    expect(hidden.hiddenLibraryKeys, isEmpty);
  });

  test('a saved manual Hide remains authoritative after renaming', () async {
    final libraries = _Libraries()..items = [_library('3', 'Movies [4K]')];
    addTearDown(libraries.dispose);
    final hidden = HiddenLibrariesProvider(librariesProvider: libraries, hide4kByDefault: true);
    addTearDown(hidden.dispose);
    await hidden.hideLibrary('plex:3');
    libraries.replace([_library('3', 'Movies')]);
    expect(hidden.hiddenLibraryKeys, {'plex:3'});
  });

  test('clearing library preferences clears the explicit Show override', () async {
    final libraries = _Libraries()..items = [_library('3', 'Movies [4K]')];
    addTearDown(libraries.dispose);
    final hidden = HiddenLibrariesProvider(librariesProvider: libraries, hide4kByDefault: true);
    addTearDown(hidden.dispose);
    await hidden.unhideLibrary('plex:3');
    await (await StorageService.getInstance()).clearLibraryPreferences();
    await hidden.refresh();
    expect(hidden.hiddenLibraryKeys, {'plex:3'});
  });

  test('disposed visibility providers stop listening to library changes', () async {
    final libraries = _Libraries();
    addTearDown(libraries.dispose);
    final hidden = HiddenLibrariesProvider(librariesProvider: libraries, hide4kByDefault: true);
    await hidden.ensureInitialized();
    hidden.dispose();
    expect(() => libraries.replace([_library('3', 'Movies [4K]')]), returnsNormally);
  });
}
