import 'dart:async';

/// Prepares a destination that may already have a native video core.
///
/// PowerLink must never replace the queue while a different video still owns
/// the player: navigation would otherwise reject the new launch with
/// `playbackActive`, leaving the old show running under the new queue.
///
/// Stop the old session and await its native retirement *before* committing
/// the incoming queue. If the old owner cannot exit, fail closed so the
/// caller's existing queue/playback remain unchanged.
class PowerLinkDestinationTakeover {
  const PowerLinkDestinationTakeover._();

  static Future<void> retire({
    required bool Function() hasVideoSession,
    required Future<bool> Function() stopVideoAndExit,
    Duration deadline = const Duration(seconds: 15),
  }) async {
    if (!hasVideoSession()) return;
    final exited = await stopVideoAndExit().timeout(
      deadline,
      onTimeout: () => throw StateError(
        'Existing PowerPlay video did not finish shutting down for handoff',
      ),
    );
    if (!exited) {
      throw StateError(
        'Existing PowerPlay video cannot leave its current route; '
        'handoff will not replace its queue',
      );
    }
  }
}
