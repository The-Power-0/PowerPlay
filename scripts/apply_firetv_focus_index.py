#!/usr/bin/env python3
"""Stage 07: remove linear binding scans from Fire TV action-bar focus changes."""
from pathlib import Path
p=Path("lib/focus/focusable_action_bar.dart")
s=p.read_text(encoding="utf-8")
def once(a,b):
    global s
    if s.count(a)!=1:
        raise SystemExit(f"Focus source layout changed: {a[:90]!r} ({s.count(a)})")
    s=s.replace(a,b)
once("  late List<OwnedFocusNodeBinding> _focusBindings;\n",
     "  late List<OwnedFocusNodeBinding> _focusBindings;\n"
     "  // Binding identity is stable across action reorder; indexes are rebuilt\n"
     "  // only when the action list changes, not on every D-pad focus callback.\n"
     "  late Map<OwnedFocusNodeBinding, int> _focusBindingIndex;\n")
once("    final index = _focusBindings.indexOf(binding);\n    if (index != -1) {",
     "    final index = _focusBindingIndex[binding];\n    if (index != null) {")
once("    _focusBindings = [for (var i = 0; i < widget.actions.length; i++) _createBinding(widget.actions[i], i)];\n"
     "    _focusNodes = [for (final binding in _focusBindings) binding.node];",
     "    _focusBindings = [for (var i = 0; i < widget.actions.length; i++) _createBinding(widget.actions[i], i)];\n"
     "    _focusBindingIndex = {for (var i = 0; i < _focusBindings.length; i++) _focusBindings[i]: i};\n"
     "    _focusNodes = [for (final binding in _focusBindings) binding.node];")
once("    _focusBindings = newBindings;\n    _focusNodes = [for (final binding in newBindings) binding.node];",
     "    _focusBindings = newBindings;\n"
     "    _focusBindingIndex = {for (var i = 0; i < newBindings.length; i++) newBindings[i]: i};\n"
     "    _focusNodes = [for (final binding in newBindings) binding.node];")
# Preserve old identity matching, focus transfer and disabled Select semantics.
p.write_text(s,encoding="utf-8")
print("Action-bar focus callbacks now resolve owned node positions in O(1).")
print("No Flutter build, remote key injection or focus regression test run.")
