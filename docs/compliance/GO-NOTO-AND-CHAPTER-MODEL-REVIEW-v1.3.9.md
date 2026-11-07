## Go Noto and chapter model review

Go Noto Universal v7.0 source and terms are pinned to commit `0f4be64616e29390e3063970ed7f6afe77356d39`. Its generated fonts are OFL 1.1; its scripts are Unlicense. Both shipped font assets match the signed APK, the Hangul companion regenerates byte-for-byte from the archived v7.0 input, and the original font notice is included. The original OFL text specifies no Reserved Font Name.

The chapter model is byte-identical in the archived app source and release APK and was introduced in upstream commit `eb42723ee8500ba02b153bb6779b37a7a87b6334`. The original training inputs are absent; this is the remaining model provenance item.

The candidate CI APK built from app source commit `dfab0f7ae979c0edee617f9f50a6c72efac51aa4` is byte-identical to the published APK, including all 15 native libraries and 79 Flutter assets. This verifies app/AOT output identity. It does not establish a full historical Flutter engine or Cronet build.

See `font-and-model-review-v1.3.9.json` and the [APK payload review](APK-PAYLOAD-REVIEW-v1.3.9.md). Overall status remains **NOT CLEARED**.
