import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:plezy/services/powerlink/powerlink_destination_takeover.dart';

void main() {
  group('PowerLink destination takeover', () {
    test('no active session: continue immediately without stopping anything', () async {
      var stopCount = 0;
      await PowerLinkDestinationTakeover.retire(
        hasVideoSession: () => false,
        stopVideoAndExit: () async {
          stopCount++;
          return true;
        },
      );
      expect(stopCount, 0);
    });

    test('already playing: await native player exit before a new queue is applied', () async {
      final retirement = Completer<bool>();
      final order = <String>[];
      final takeover = PowerLinkDestinationTakeover.retire(
        hasVideoSession: () => true,
        stopVideoAndExit: () {
          order.add('begin old player exit');
          return retirement.future;
        },
      ).then((_) => order.add('ready for incoming queue'));
      await Future<void>.delayed(Duration.zero);
      expect(order, ['begin old player exit']);
      retirement.complete(true);
      await takeover;
      expect(order, ['begin old player exit', 'ready for incoming queue']);
    });

    test('refused exit: leave existing player and queue untouched', () async {
      var destinationQueueInstalled = false;
      await expectLater(
        PowerLinkDestinationTakeover.retire(
          hasVideoSession: () => true,
          stopVideoAndExit: () async => false,
        ).then((_) => destinationQueueInstalled = true),
        throwsStateError,
      );
      expect(destinationQueueInstalled, isFalse);
    });

    test('native retirement timeout: fail closed, never start a second core', () async {
      final retirement = Completer<bool>();
      await expectLater(
        PowerLinkDestinationTakeover.retire(
          hasVideoSession: () => true,
          stopVideoAndExit: () => retirement.future,
          deadline: const Duration(milliseconds: 5),
        ),
        throwsStateError,
      );
      retirement.complete(true);
    });

    test('player shutdown failure: propagate instead of swapping queues', () async {
      await expectLater(
        PowerLinkDestinationTakeover.retire(
          hasVideoSession: () => true,
          stopVideoAndExit: () => Future<bool>.error(StateError('native shutdown failed')),
        ),
        throwsStateError,
      );
    });
  });
}
