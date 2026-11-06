# PowerPlay v1.3.9 — FriBidi static-link licensing decision (OPEN)

**Scope:** the FriBidi 1.0.16 object code inside the combined `libass.a` linked statically into PowerPlay's `libasskt.so`. This document is an evidence-backed decision checklist, not a legal opinion or authorization to relicense any code.

## Verified upstream licensing facts

- The [FriBidi v1.0.16 README](https://github.com/fribidi/fribidi/blob/v1.0.16/README.md) and original source headers grant use under **LGPL-2.1-or-later**. The distributed upstream `COPYING` is the full text of LGPL v2.1.
- The [GNU LGPL-2.1, section 6](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html) addresses linked works and static-library relinking. The [GNU GPL FAQ](https://www.gnu.org/licenses/gpl-faq.en.html#LGPLStaticVsDynamic) describes the usual requirement to provide object/relink materials when static linking under LGPL.
- [LGPL-2.1 section 3](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html) **permits conversion of a specific copy of the LGPL-covered library to the ordinary GNU GPL, version 2 or later**, by altering all the covered license notices for that copy as directed by the section. The [FSF compatibility guidance](https://www.gnu.org/licenses/license-compatibility.en.html) explicitly confirms LGPL-2.1 permits relicensing to GPL-2-or-later, which includes GPLv3. The option is *not* a blanket grant to change proprietary or independently licensed components and is irreversible for the converted copy.
- PowerPlay's tracked app source is GPL-3.0; its independent libass core is ISC; FreeType can use the FreeType License option. Actual file-by-file exceptions and other native components must still be reconciled.
- The upstream libass static archive was reproduced byte-for-byte using the historical six WrapDB sources and Android NDK; this confirms the source inputs but does not itself elect any redistribution license.

## Choose and document one defensible distribution path

### Path A — Preserve FriBidi LGPL-2.1-or-later and satisfy static linking

The combination is distributed under GPLv3 for PowerPlay while FriBidi remains LGPL-2.1-or-later. Ensure all original legal notices and precise corresponding FriBidi source are provided. Provide a usable method and materials for recipients to replace/modify FriBidi and relink into the full distributed combined code, with appropriate object files or equivalent permitted mechanism, documented build commands, ABI/version, and integration steps. Validate the steps on actual Android ARMv7 and the released app. Consider the rules for device installation information separately.

*Do not assume publishing C/C++ source alone proves that a receiver can perform the required relink of the combined app.*

### Path B — Explicit LGPL section 3 conversion for a specified FriBidi source copy

For a **future corrected distribution**, prepare the precise FriBidi copy with the section 3 notice changes to specify GNU GPLv3. Retain original author/copyright text, preserve the record of the conversion, provide full GPLv3 terms and corresponding source, and build the distributed binary from that specific, documented copy. Audit all other combined libraries for independent licensing requirements. Section 3 conversion is not an undocumented shortcut that retroactively changes the copyright terms of already-distributed files. Do not claim a historical compiled binary used a GPL-converted copy unless supported by its source/notice evidence.

## Evidence required before closing LGPL-003

- [ ] Record the selected path, exact copies/files/versions and rationale; review file-level FriBidi headers, generated files and possible exceptions.
- [ ] Retain original FriBidi attribution and full source, including any generated-file source/scripts and upstream license text.
- [ ] Under **Path A**, publish recipient-usable relink materials/instructions and test them against the shipped ARMv7 stack.
- [ ] Under **Path B**, document the explicit section 3 license election, alter the covered notices for the specific source copy, rebuild the binary from it, and preserve old and new legal notices with hashes.
- [ ] Recheck project-wide GPLv3 compatibility, applicable installation-information obligations, and verification of release source/NOTICE assets.
- [ ] Legal/source reviewer acknowledges the chosen path, and the public release attachments accurately reflect that path.

**Current decision: NOT SELECTED. LGPL-003 remains BLOCKED.** Merely adding the missing libunibreak `LICENCE` file does not resolve FriBidi static-linking requirements.
