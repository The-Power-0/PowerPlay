import 'package:flutter/foundation.dart';
import '../mixins/disposable_change_notifier_mixin.dart';
import '../services/storage_service.dart';
import '../utils/fire_tv_library_policy.dart';
import '../utils/platform_detector.dart';
import 'libraries_provider.dart';

/// Shared library visibility, combining saved choices with device defaults.
class HiddenLibrariesProvider extends ChangeNotifier with DisposableChangeNotifierMixin {
  StorageService? _storageService;
  final String? profileId;
  final LibrariesProvider? _librariesProvider;
  final bool _hide4kByDefault;
  Set<String> _hiddenLibraryKeys = {};
  Set<String> _shownLibraryOverrides = {};
  Set<String> _lastNotifiedKeys = {};
  bool _isInitialized = false;
  late final Future<void> _initFuture;

  HiddenLibrariesProvider({
    StorageService? storageService,
    this.profileId,
    LibrariesProvider? librariesProvider,
    bool? hide4kByDefault,
  }) : _storageService = storageService,
       _librariesProvider = librariesProvider,
       _hide4kByDefault = hide4kByDefault ?? TvDetectionService.is1080pOnlyFireStickSync() {
    _librariesProvider?.addListener(_onLibrariesChanged);
    _initFuture = _initialize();
  }

  Future<void> ensureInitialized() => _initFuture;
  bool get isInitialized => _isInitialized;

  /// Defaults are derived, never written into the user's saved hidden list.
  /// This also covers late server connections and renamed or new libraries.
  Set<String> get hiddenLibraryKeys => Set.unmodifiable({
    ..._hiddenLibraryKeys,
    if (_hide4kByDefault)
      for (final library in _librariesProvider?.libraries ?? [])
        if (!_shownLibraryOverrides.contains(library.globalKey) &&
            hide4kLibraryByDefault(is1080pOnlyFireStick: true, title: library.title))
          library.globalKey,
  });

  Future<void> _initialize() async {
    await _loadFromStorage();
    _isInitialized = true;
    _notifyVisibilityChanged(force: true);
  }

  Future<void> _loadFromStorage() async {
    final storage = _storageService ??= await StorageService.getInstance();
    final scopedProfileId = profileId;
    _hiddenLibraryKeys = scopedProfileId == null
        ? storage.getHiddenLibraries()
        : storage.getHiddenLibrariesForProfile(scopedProfileId);
    _shownLibraryOverrides = storage.getShownLibraryOverrides(profileId: scopedProfileId);
  }

  void _onLibrariesChanged() => _notifyVisibilityChanged();

  void _notifyVisibilityChanged({bool force = false}) {
    if (isDisposed) return;
    final next = hiddenLibraryKeys;
    if (!force && setEquals(next, _lastNotifiedKeys)) return;
    _lastNotifiedKeys = next;
    safeNotifyListeners();
  }

  Future<void> hideLibrary(String libraryKey, {void Function()? checkCurrent}) =>
      setLibraryHidden(libraryKey, true, checkCurrent: checkCurrent);

  Future<void> unhideLibrary(String libraryKey, {void Function()? checkCurrent}) =>
      setLibraryHidden(libraryKey, false, checkCurrent: checkCurrent);

  Future<void> setLibraryHidden(String libraryKey, bool hidden, {void Function()? checkCurrent}) async {
    await ensureInitialized();
    if (isDisposed) return;
    checkCurrent?.call();
    final next = Set<String>.of(_hiddenLibraryKeys);
    final shown = Set<String>.of(_shownLibraryOverrides);
    if (hidden) {
      next.add(libraryKey);
      shown.remove(libraryKey);
    } else {
      next.remove(libraryKey);
      shown.add(libraryKey);
    }
    final hiddenChanged = !setEquals(next, _hiddenLibraryKeys);
    final shownChanged = !setEquals(shown, _shownLibraryOverrides);
    if (!hiddenChanged && !shownChanged) return;
    final storage = _storageService!;
    final scopedProfileId = profileId;
    Future<void> saveHidden(Set<String> keys) => scopedProfileId == null
        ? storage.saveHiddenLibraries(keys)
        : storage.saveHiddenLibrariesForProfile(scopedProfileId, keys);
    if (hiddenChanged) await saveHidden(next);
    try {
      if (shownChanged) await storage.saveShownLibraryOverrides(shown, profileId: scopedProfileId);
    } catch (_) {
      if (hiddenChanged) await saveHidden(_hiddenLibraryKeys);
      rethrow;
    }
    if (isDisposed) return;
    checkCurrent?.call();
    _hiddenLibraryKeys = next;
    _shownLibraryOverrides = shown;
    _notifyVisibilityChanged();
  }

  @visibleForTesting
  bool isLibraryHidden(String libraryKey) => hiddenLibraryKeys.contains(libraryKey);

  Future<void> refresh() async {
    await _loadFromStorage();
    _isInitialized = true;
    _notifyVisibilityChanged(force: true);
  }

  @override
  void dispose() {
    _librariesProvider?.removeListener(_onLibrariesChanged);
    super.dispose();
  }
}
