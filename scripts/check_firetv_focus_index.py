#!/usr/bin/env python3
from pathlib import Path
s=Path("lib/focus/focusable_action_bar.dart").read_text(encoding="utf-8")
for x in ("late Map<OwnedFocusNodeBinding, int> _focusBindingIndex;",
          "final index = _focusBindingIndex[binding];",
          "_focusBindingIndex = {for (var i = 0; i < _focusBindings.length; i++) _focusBindings[i]: i};",
          "_focusBindingIndex = {for (var i = 0; i < newBindings.length; i++) newBindings[i]: i};"):
    if s.count(x)!=1: raise SystemExit("Focus-binding index missing or duplicated: "+x)
if "_focusBindings.indexOf(binding)" in s: raise SystemExit("Linear key-event lookup remains")
if "if (oldIndex == focusedOldIndex)" not in s: raise SystemExit("Focus restoration altered")
print("Focus-binding source audit passed. D-pad device tests remain pending.")
