part of '../../video_player_screen.dart';

extension _VideoPlayerEpisodeNavigationMethods on VideoPlayerScreenState {
  void _clearEpisodeLoadingFlags() {
    if (!_episode.isLoadingNext && !_episode.isLoadingPrevious) return;
    _setPlayerState(() {
      _episode.isLoadingNext = false;
      _episode.isLoadingPrevious = false;
    });
  }

  /// Old screen-swap parity: after an in-place item change (or its failed
  /// rollback), surface the chrome and re-anchor focus on play/pause. The
  /// control that drove the swap (next button, queue item, play-next prompt)
  /// may have unmounted or unfocused by now — without a fresh route's
  /// autofocus, dpad navigation would be stranded until the chrome is hidden
  /// and re-shown. Focusing play/pause is invisible in pointer mode (focus
  /// visuals are keyboard/dpad-gated).
  void _showChromeForSwappedItem() {
    if (!mounted) return;
    _chromeController.show(focusPlayPause: true);
  }

  /// Whether the transport's next/previous commands have somewhere to go.
  ///
  /// One answer for every entry point — the on-screen buttons, the OS media
  /// session and the companion remote — so no surface can advertise a step
  /// another refuses. Live TV steps through the channel list, and each
  /// direction is answered by its own list adjacency. Off live, `next` needs
  /// a loaded next item, while `previous` always has a target:
  /// [_restartOrPlayPrevious] restarts the current item — a movie as much as
  /// an episode — when nothing earlier is loaded.
  bool get _hasNextItem => widget.isLive
      ? _hasNextChannel
      : _episode.next != null ||
          PowerShuffleSession.instance.matches(
            _currentMetadata, context.read<PlaybackStateProvider>().shuffleContextKey,
          );

  bool get _hasPreviousItem => !widget.isLive || _hasPreviousChannel;

  /// The transport's next command: a channel zap on live TV, the next
  /// episode/queue item otherwise. Both targets no-op without one.
  Future<void> _navigateToNextItem() => widget.isLive ? _switchLiveChannel(1) : _playNext();

  /// The transport's previous command: a channel zap on live TV; otherwise a
  /// restart or the previous item. A live stream has no "restart" — an
  /// absolute seek to zero would drag the playhead off the live edge — so
  /// the VOD fallback is unreachable here by construction.
  Future<void> _navigateToPreviousItem() => widget.isLive ? _switchLiveChannel(-1) : _restartOrPlayPrevious();

  /// Only explicit Next/direct episode selection offers a skip. Back cancels,
  /// pauses/exits are never interpreted as skips.
  Future<String?> _choosePowerShuffleSkipOption() => PowerShuffleSkipDialog.show(context);

  Future<void> _playNext() async {
    if (!_canNavigateMediaItems() || !mounted || _episode.isLoadingNext) return;
    final ps = PowerShuffleSession.instance;
    final psActive = ps.matches(
      _currentMetadata, context.read<PlaybackStateProvider>().shuffleContextKey,
    );
    if (_episode.next == null && !psActive) return;
    if (psActive && _powerShuffleActionInFlight) return;
    if (psActive) _powerShuffleActionInFlight = true;
    try {
      // The first frame can arrive between periodic samples and a Next
      // button press. Capture it before deciding a started episode cannot
      // be skipped.
      if (psActive && !ps.hasStarted) _tickPowerShuffle();
      final wasAtCompletion = _episode.completionLatch.triggered;
      MediaItem? target = _episode.next;
  
      if (psActive) {
        // An earlier skip may already have been committed by HA while the
        // new stream failed to initialize. Retry that same target without a
        // second skip decision or a second history mutation.
        if (ps.pendingNavigationTarget case final pending?) {
          target = pending;
        } else {
          if (!ps.hasStarted) {
            showMainSnackBar('An episode must begin playing before it can be skipped.');
            return;
          }
          final finished = wasAtCompletion || ps.completedForCurrent;
          final choice = finished ? null : await _choosePowerShuffleSkipOption();
          if (!mounted || (!finished && choice == null)) return;
          try {
            target = await ps.advance(
              context, atEnd: finished, skipChoice: choice,
            );
          } catch (_) {
            if (mounted) {
              showMainSnackBar('Home Assistant could not save the PowerShuffle skip.');
            }
            return;
          }
          if (!mounted) return;
          if (target == null) {
            showMainSnackBar('No eligible episodes remain. Check PowerShuffle cooldowns in Home Assistant.');
            await _stopVideoAndExit();
            return;
          }
        }
      }
  
      _episode.autoPlayTimer?.cancel();
      _unfocusPlayNextPrompt();
      _dismissStillWatching();
      _setPlayerState(() {
        _episode.isLoadingNext = true;
        _episode.showPlayNextDialog = false;
      });
  
      _powerShuffleNavigationApproved = psActive;
      try {
        final outcome = await _navigateToEpisode(target!);
        if (outcome == MediaReloadOutcome.failed) {
          if (psActive) {
            _clearEpisodeLoadingFlags();
            _showChromeForSwappedItem();
            showMainSnackBar('Next PowerShuffle episode did not load. Press Next to retry.');
          } else {
            _presentPlayNextRetryPrompt(wasAtCompletion: wasAtCompletion);
          }
        }
      } finally {
        _powerShuffleNavigationApproved = false;
      }
    } finally {
      if (psActive) _powerShuffleActionInFlight = false;
    }
  }

  Future<void> _playPrevious() async {
    if (!_canNavigateMediaItems()) return;
    if (_episode.previous == null || _episode.isLoadingPrevious) return;

    _setPlayerState(() {
      _episode.isLoadingPrevious = true;
    });

    await _navigateToEpisode(_episode.previous!);
  }

  Future<void> _restartOrPlayPrevious() async {
    if (!_canNavigateMediaItems()) return;
    final currentPlayer = player;
    if (!mounted || currentPlayer == null || _episode.isLoadingPrevious) return;

    if (!shouldRestartBeforePreviousItem(currentPlayer.state.position) && _episode.previous != null) {
      await _playPrevious();
      return;
    }

    _episode.autoPlayTimer?.cancel();
    _unfocusPlayNextPrompt();
    _dismissStillWatching();

    _setPlayerState(() {
      _episode.showPlayNextDialog = false;
      _episode.completionLatch.reset();
    });

    final target = clampSeekPosition(currentPlayer, Duration.zero);
    await _seekPlayback(target);
    if (!mounted || currentPlayer != player) return;

    _mediaControls.pushPlaybackState();
  }

  /// Replace this screen when an in-place reload cannot serve the new item.
  /// The route commit owns player-to-player teardown semantics.
  /// [watchTogetherCopy] is the room's file, when the room asked for it: a
  /// server's item, so it opens outside the offline library. The player still
  /// plays a download of the room's version.
  Future<void> _replaceScreenWithPlayer(MediaItem metadata, {WatchCopy? watchTogetherCopy}) async {
    final version = watchTogetherCopy == null ? null : watchTogetherVersionOf(metadata, watchTogetherCopy);
    try {
      await navigateToVideoPlayer(
        context,
        metadata: metadata,
        usePushReplacement: true,
        isOffline: _offlineLibraryMode && watchTogetherCopy == null,
        selectedMediaIndex: version?.index ?? (metadata.raw?['powerlink_media_index'] as int?),
        selectedMediaSourceId: version?.sourceId ?? (metadata.raw?['powerlink_media_id'] as String?),
        strictMediaSelection: metadata.raw?['powerlink_media_index'] != null,
        watchTogetherCopy: watchTogetherCopy,
      );
    } finally {
      // No route commit (external player or failure): keep this screen usable.
      if (mounted) {
        _clearEpisodeLoadingFlags();
      }
    }
  }

  /// Navigates to a new episode by reusing the current player whenever possible.
  ///
  /// Returns the reload outcome so [_playNext] can distinguish a failed
  /// in-place swap (previous session still on screen) from rejected or
  /// superseded attempts. The screen-replacement fallback reports
  /// [MediaReloadOutcome.rejected]: no in-place reload ran.
  Future<MediaReloadOutcome> _navigateToEpisode(MediaItem episodeMetadata) async {
    // Queue-sheet selections and Previous are also explicit item changes.
    // They may not silently evade PowerShuffle's two skip decisions.
    final ps = PowerShuffleSession.instance;
    if (!_powerShuffleNavigationApproved &&
        ps.matches(
          _currentMetadata, context.read<PlaybackStateProvider>().shuffleContextKey,
        ) &&
        PowerShuffleSession.keyOf(episodeMetadata) !=
            PowerShuffleSession.keyOf(_currentMetadata)) {
      if (!ps.hasStarted) return MediaReloadOutcome.rejected;
      final finished = _episode.completionLatch.triggered || ps.completedForCurrent;
      final choice = finished ? null : await _choosePowerShuffleSkipOption();
      if (!mounted || (!finished && choice == null)) return MediaReloadOutcome.rejected;
      try {
        final chosen = await ps.advance(
          context, atEnd: finished, skipChoice: choice, requested: episodeMetadata,
        );
        if (chosen == null) return MediaReloadOutcome.rejected;
        episodeMetadata = chosen;
      } catch (_) {
        if (mounted) showMainSnackBar('Home Assistant could not save the PowerShuffle change.');
        return MediaReloadOutcome.rejected;
      }
    }
    _episode.lastReloadFailureReason = null;
    final currentPlayer = player;
    if (currentPlayer == null) {
      if (mounted) unawaited(_replaceScreenWithPlayer(episodeMetadata));
      return MediaReloadOutcome.rejected;
    }

    // Callers fire this without awaiting (auto-play countdown, PiP, the prompt), so an escaping
    // throw would be an unhandled async error that also strands the loading flag set by
    // _playNext — which then silently disables item navigation for the rest of the session.
    try {
      // Carry the playing version to the next episode by signature — its Media
      // list may order versions differently, so the bare index is a guess and
      // the source id is per-episode.
      final currentVersionSignature =
          _effectiveSelectedMediaIndex >= 0 && _effectiveSelectedMediaIndex < _availableVersions.length
          ? _availableVersions[_effectiveSelectedMediaIndex].signature
          : null;
      // Users who curate per-episode selections server-side (e.g. via Plex Auto
      // Languages) opt out of carrying tracks across episodes entirely: with no
      // preferences, both audio and subtitles start at the server-selected
      // priority (#1717).
      final settingsService = await SettingsService.getInstance();
      if (!mounted || currentPlayer != player) {
        return MediaReloadOutcome.superseded;
      }
      final followServerSelections = settingsService.read(SettingsService.followServerTrackSelections);
      final committedSubtitleSelection = _playbackSession?.subtitleSelection;
      final primarySubtitlePreference = followServerSelections
          ? null
          : subtitlePreferenceForItemChange(
              hasCommittedSelection: committedSubtitleSelection != null,
              committedTrack: committedSubtitleSelection?.primaryTrack,
              nativeTrack: currentPlayer.state.track.subtitle,
              declinedPreference: committedSubtitleSelection?.declinedPreference,
              sessionPreference: _sessionSubtitlePreference,
            );
      final secondarySubtitlePreference = followServerSelections
          ? null
          : subtitlePreferenceForItemChange(
              hasCommittedSelection: committedSubtitleSelection != null,
              committedTrack: committedSubtitleSelection?.secondaryTrack,
              nativeTrack: currentPlayer.state.track.secondarySubtitle,
              sessionPreference: _sessionSecondarySubtitlePreference,
            );
      // PowerLink's immutable queue records the *destination's* selected
      // Plex Media version for each slot. A movie/show may have a different
      // file ordering from the previous episode; carrying that episode's
      // version index or signature could accidentally play 4K on a Stick Lite.
      final powerLinkIndex = episodeMetadata.raw?['powerlink_media_index'];
      final powerLinkSourceId = episodeMetadata.raw?['powerlink_media_id'];
      final usesPowerLinkVersion = powerLinkIndex is int;
      return await _reloadMediaInPlace(
        metadata: episodeMetadata,
        selectedMediaIndex: usesPowerLinkVersion ? powerLinkIndex : _effectiveSelectedMediaIndex,
        selectedMediaSourceId: powerLinkSourceId is String && powerLinkSourceId.isNotEmpty
            ? powerLinkSourceId
            : null,
        preferredVersionSignature: usesPowerLinkVersion ? null : currentVersionSignature,
        qualityPreset: _selectedQualityPreset,
        // Stream ids are per-part: the previous episode's audio id is
        // meaningless on the new item, so let preferences pick the track.
        useCurrentAudioStreamSelection: false,
        preserveCurrentTrackSelection: !followServerSelections,
        preservedAudioTrack: _sessionAudioPreference,
        preservedSubtitleTrack: primarySubtitlePreference,
        preservedSecondarySubtitleTrack: secondarySubtitlePreference,
        reason: 'episode navigation',
      );
    } catch (e, stackTrace) {
      appLogger.e('Failed to navigate to the next item', error: e, stackTrace: stackTrace);
      _clearEpisodeLoadingFlags();
      if (mounted) showErrorSnackBar(context, t.messages.errorLoading(error: localizedErrorReason(e)));
      return MediaReloadOutcome.failed;
    }
  }
}
