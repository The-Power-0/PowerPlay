import 'package:flutter/widgets.dart';

import '../../services/playback_coordinator.dart';
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
      // The HA nonce is bound to this exact source entity and expires after
      // the capture deadline. Nothing is written to preferences or logs.
      await PowerLinkTransferClient(link.request).publishCapture({
        ...snapshot,
        'source_device': link.sourceDevice,
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
