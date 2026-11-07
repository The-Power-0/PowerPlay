import 'package:flutter/material.dart';

import '../../focus/focusable_button.dart';

/// Fire TV-first two-action skip picker.
///
/// Only the two actual cooldown choices are focusable. Android Back / Escape
/// cancels the dialog without mutating history. Explicit FocusNodes and
/// directional callbacks avoid relying on Material dialog button traversal,
/// which can strand D-pad focus on action rows after a player route swap.
class PowerShuffleSkipDialog extends StatefulWidget {
  const PowerShuffleSkipDialog({super.key});

  static Future<String?> show(BuildContext context) => showDialog<String>(
        context: context,
        barrierDismissible: false,
        builder: (_) => const PowerShuffleSkipDialog(),
      );

  @override
  State<PowerShuffleSkipDialog> createState() => _PowerShuffleSkipDialogState();
}

class _PowerShuffleSkipDialogState extends State<PowerShuffleSkipDialog> {
  final _fiveDays = FocusNode(debugLabel: 'PowerShuffle Skip 5 Days');
  final _nextCycle = FocusNode(debugLabel: 'PowerShuffle Skip Next Cycle');
  bool _handled = false;

  void _finish([String? choice]) {
    if (_handled || !mounted) return;
    _handled = true;
    Navigator.of(context).pop(choice);
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _fiveDays.requestFocus();
    });
  }

  @override
  void dispose() {
    _fiveDays.dispose();
    _nextCycle.dispose();
    super.dispose();
  }

  Widget _option({
    required String keyName,
    required String value,
    required String title,
    required String description,
    required FocusNode focusNode,
    required VoidCallback moveUp,
    required VoidCallback moveDown,
    required IconData icon,
  }) {
    final theme = Theme.of(context);
    return FocusableButton(
      focusNode: focusNode,
      autofocus: value == 'five_days',
      autoScroll: true,
      useBackgroundFocus: true,
      onNavigateUp: moveUp,
      onNavigateDown: moveDown,
      onBack: () => _finish(),
      onPressed: () => _finish(value),
      child: Semantics(
        button: true,
        label: title,
        child: Container(
          key: Key('powershuffle_skip_$keyName'),
          constraints: const BoxConstraints(minHeight: 72),
          padding: const EdgeInsets.symmetric(vertical: 13, horizontal: 14),
          decoration: BoxDecoration(
            color: theme.colorScheme.surfaceContainerHigh,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            children: [
              Icon(icon, size: 24, color: theme.colorScheme.primary),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      title,
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                      softWrap: true,
                    ),
                    const SizedBox(height: 4),
                    Text(description, style: theme.textTheme.bodySmall, softWrap: true),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 460),
        child: SingleChildScrollView(
          primary: false,
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Skip this episode?',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 8),
              Text(
                'Choose when this episode returns to PowerShuffle.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 18),
              _option(
                keyName: '5_days',
                value: 'five_days',
                title: 'Skip for 5 days',
                description: 'Available again after 120 hours',
                focusNode: _fiveDays,
                moveUp: () => _nextCycle.requestFocus(),
                moveDown: () => _nextCycle.requestFocus(),
                icon: Icons.schedule_rounded,
              ),
              const SizedBox(height: 10),
              _option(
                keyName: 'next_cycle',
                value: 'next_cycle',
                title: 'Skip until next cycle',
                description: 'Available when the show starts a new rotation',
                focusNode: _nextCycle,
                moveUp: () => _fiveDays.requestFocus(),
                moveDown: () => _fiveDays.requestFocus(),
                icon: Icons.restart_alt_rounded,
              ),
              const SizedBox(height: 14),
              Align(
                alignment: Alignment.centerRight,
                child: Text(
                  'Press Back to cancel',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
            ],
            ),
          ),
        ),
      ),
    );
  }
}
