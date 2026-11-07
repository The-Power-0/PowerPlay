import 'package:flutter/widgets.dart';
import 'package:provider/provider.dart';

import '../../profiles/active_profile_provider.dart';

import '../../services/playback_coordinator.dart';
import '../powershuffle/powershuffle_session.dart';
import '../../utils/app_logger.dart';
import '../../utils/snackbar_helper.dart';
import '../deep_links/deep_link.dart';
import 'powerlink_transfer.dart';

/// HA requests a capture through a fresh Android intent. No periodic tasks,
/// keepalives or background activity run on the Fire Stick during playback.
class PowerLinkCapture {
  PowerLinkCapture._();

  static Future<void> send(BuildContext context, PowerLinkCaptureLink link) async {
    final snapshot = PlaybackCoordinator.instance.capturePowerLinkQueue();
    if (snapshot == null) {
      if (context.mounted) {
        showMainSnackBar('PowerLink needs an active, complete movie or TV playback queue.');
      }
      return;
    }
    try {
      // Profile identity is a Plex Home UUID (or local profile ID), never a
      // secret. It is required for receiver-side profile isolation and causes
      // the existing PIN prompt when the destination profile is protected.
      final active = context.read<ActiveProfileProvider>().active;
      if (active == null) throw const FormatException('No active Plex Home profile');
      final profileRef = linkProfileRef(active);
      // An automatic PowerShuffle handoff has no time to wait for the next
      // periodic heartbeat. Flush unique viewed ranges before presenting the
      // source's current playhead to Home Assistant. Timeout is deliberately
      // below PowerLink's one-shot capture deadline.
      try {
        await PowerShuffleSession.instance.flushBeforeHandoff()
            .timeout(const Duration(seconds: 3));
      } catch (error) {
        appLogger.w('PowerShuffle coverage flush failed before PowerLink capture', error: error);
        // Preserve handoff availability; the last acknowledged viewed
        // ranges remain in HA. The exact native playhead is still captured.
      }
      // The HA nonce is bound to this exact source entity and expires after
      // the capture deadline. Nothing is written to preferences or logs.
      await PowerLinkTransferClient(link.request).publishCapture({
        ...snapshot,
        'source_device': link.sourceDevice,
        'profile_id': profileRef,
      });
    } catch (error, stack) {
      appLogger.w('PowerLink capture was rejected or the HA endpoint is unreachable',
        error: error, stackTrace: stack);
      if (context.mounted) {
        showMainSnackBar('PowerLink could not send this queue to Home Assistant.');
      }
    }
  }
}
