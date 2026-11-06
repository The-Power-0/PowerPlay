import 'package:wakelock_plus/wakelock_plus.dart';

import '../../utils/app_logger.dart';

typedef WakelockPlatformToggle = Future<void> Function(bool enabled);

/// Serializes fire-and-forget wakelock requests around the latest desired state.
class WakelockController {
  WakelockController({WakelockPlatformToggle? platformToggle})
    : _platformToggle = platformToggle ?? _togglePlatformWakelock;

  final WakelockPlatformToggle _platformToggle;

  Future<void> _tail = Future<void>.value();
  bool? _effectiveEnabled;
  bool _playbackDesiredEnabled = false;
  int _temporaryHolds = 0;

  bool get _desiredEnabled => _playbackDesiredEnabled || _temporaryHolds > 0;

  /// Requests a wakelock state and completes after this queued reconciliation.
  ///
  /// Platform failures are logged and absorbed so detached UI callers cannot
  /// produce unhandled errors. A failed state is not recorded as effective;
  /// the same value can therefore be retried by a later explicit request.
  Future<void> setEnabled(bool enabled) {
    _playbackDesiredEnabled = enabled;
    return _scheduleReconciliation();
  }

  /// Keep a freshly transferred PowerLink video awake *while it is still
  /// fetching metadata and opening the player*. The ordinary playback state
  /// may briefly request an unlock during buffering; that must not cancel
  /// this bounded startup hold. Each caller releases exactly its own lease.
  Future<WakelockLease> acquireTemporaryHold() async {
    _temporaryHolds++;
    await _scheduleReconciliation();
    return WakelockLease._(() {
      _temporaryHolds--;
      return _scheduleReconciliation();
    });
  }

  Future<void> _scheduleReconciliation() {
    final operation = _tail.then((_) => _reconcile());
    _tail = operation;
    return operation;
  }

  Future<void> _reconcile() async {
    while (_effectiveEnabled != _desiredEnabled) {
      final target = _desiredEnabled;
      try {
        await _platformToggle(target);
        _effectiveEnabled = target;
      } catch (error, stackTrace) {
        appLogger.w('Wakelock ${target ? 'enable' : 'disable'} failed', error: error, stackTrace: stackTrace);

        // Do not spin on a persistent failure. If an opposing request arrived
        // during the await, it still gets one attempt before this operation
        // settles; an identical state retries only through another setEnabled.
        if (_desiredEnabled == target) return;
      }
    }
  }
}

/// Idempotent ownership handle, including interrupted and superseded links.
class WakelockLease {
  WakelockLease._(this._onRelease);

  final Future<void> Function() _onRelease;
  bool _released = false;

  Future<void> release() {
    if (_released) return Future<void>.value();
    _released = true;
    return _onRelease();
  }
}

/// A single reconciler owns Flutter's one activity-level KEEP_SCREEN_ON flag.
/// PowerLink startup and the player must not race separate wakelock plugins.
final WakelockController powerplayVideoWakelock = WakelockController();

Future<void> _togglePlatformWakelock(bool enabled) => WakelockPlus.toggle(enable: enabled);
