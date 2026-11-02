/// Fire Stick hardware models with a documented maximum HDMI output of 1080p.
/// Do not infer this from the current mode, UI size, RAM, or decoding limits:
/// a 4K stick can run a 1080p UI or be attached to a 1080p television.
/// Source: Amazon's Identify Fire TV Devices and streaming-player specifications.
/// https://developer.amazon.com/docs/device-specs/identify-fire-tv-devices.html
const _fullHdFireStickModels = {'AFTSS', 'AFTSSS', 'AFTT', 'AFTM'};

bool is1080pOnlyFireTvStick({required bool isFireTv, required String model}) =>
    isFireTv && _fullHdFireStickModels.contains(model.trim().toUpperCase());

/// Unknown hardware keeps libraries visible. An explicit user visibility choice
/// is applied separately by HiddenLibrariesProvider and always wins.
bool hide4kLibraryByDefault({required bool is1080pOnlyFireStick, required String title}) =>
    is1080pOnlyFireStick && title.toUpperCase().contains('[4K]');
