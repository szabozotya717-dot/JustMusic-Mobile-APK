"""JustMusic! v1.8.6 REV6 — Android foreground media notification service.

A külön Python-for-Android folyamat az Android MediaSession/MediaStyle kártya
élettartamát kezeli. A meglévő Kivy NativeAudio marad a tényleges lejátszó.

A média gombok visszanyitják az Activity-t (PendingIntent), amely a korábbi
intent-kezelővel végzi el a parancsot. Teljes háttérbeli gombvezérléshez
később külön natív MediaSession.Callback szükséges.
"""
import json
import os
import time
import traceback


def run():
    from jnius import autoclass

    Service = autoclass('org.kivy.android.PythonService')
    service = Service.mService
    if service is None:
        raise RuntimeError('PythonService.mService is null')

    context = autoclass('android.content.Context')
    notification_cls = autoclass('android.app.Notification')
    builder_cls = autoclass('android.app.Notification$Builder')
    channel_cls = autoclass('android.app.NotificationChannel')
    manager_cls = autoclass('android.app.NotificationManager')
    session_cls = autoclass('android.media.session.MediaSession')
    metadata_cls = autoclass('android.media.MediaMetadata')
    state_cls = autoclass('android.media.session.PlaybackState')
    android_drawable = autoclass('android.R$drawable')
    intent_cls = autoclass('android.content.Intent')
    pending_cls = autoclass('android.app.PendingIntent')
    activity_cls = autoclass('org.kivy.android.PythonActivity')
    build_version = autoclass('android.os.Build$VERSION')

    manager = service.getSystemService(context.NOTIFICATION_SERVICE)
    channel_id = 'justmusic_background_media_v1'
    if build_version.SDK_INT >= 26:
        channel = channel_cls(channel_id, 'JustMusic! – háttérlejátszás',
                              manager_cls.IMPORTANCE_LOW)
        channel.setDescription('Zárolt képernyős zenevezérlő')
        manager.createNotificationChannel(channel)

    session = session_cls(service, 'JustMusic! Background')
    try:
        session.setFlags(session_cls.FLAG_HANDLES_MEDIA_BUTTONS |
                         session_cls.FLAG_HANDLES_TRANSPORT_CONTROLS)
    except Exception:
        pass
    session.setActive(True)
    state_builder_cls = autoclass('android.media.session.PlaybackState$Builder')
    meta_builder_cls = autoclass('android.media.MediaMetadata$Builder')

    def activity_intent(action=None, code=4200):
        intent = intent_cls(service, activity_cls)
        intent.addFlags(intent_cls.FLAG_ACTIVITY_SINGLE_TOP)
        intent.addFlags(intent_cls.FLAG_ACTIVITY_CLEAR_TOP)
        if action:
            intent.setAction(action)
        flags = pending_cls.FLAG_UPDATE_CURRENT
        if build_version.SDK_INT >= 23:
            flags |= pending_cls.FLAG_IMMUTABLE
        return pending_cls.getActivity(service, int(code), intent, flags)

    session.setSessionActivity(activity_intent())
    # A média-gombot az Activity kapja meg, ahol a már létező on_new_intent
    # kezelő működik. Android/gyártófüggő lehet a háttérbeli működése.
    try:
        session.setMediaButtonReceiver(activity_intent(
            'android.intent.action.MEDIA_BUTTON', 4280))
    except Exception:
        pass

    media_style_cls = autoclass('android.app.Notification$MediaStyle')
    bitmap_factory = autoclass('android.graphics.BitmapFactory')
    actions = (state_cls.ACTION_PLAY | state_cls.ACTION_PAUSE |
               state_cls.ACTION_PLAY_PAUSE | state_cls.ACTION_SKIP_TO_NEXT |
               state_cls.ACTION_SKIP_TO_PREVIOUS | state_cls.ACTION_SEEK_TO)

    def update_session(data):
        metadata = meta_builder_cls()
        title = str(data.get('title') or 'JustMusic!')
        artist = str(data.get('artist') or 'Ismeretlen előadó')
        metadata.putString(metadata_cls.METADATA_KEY_TITLE, title)
        metadata.putString(metadata_cls.METADATA_KEY_DISPLAY_TITLE, title)
        metadata.putString(metadata_cls.METADATA_KEY_ARTIST, artist)
        metadata.putString(metadata_cls.METADATA_KEY_DISPLAY_SUBTITLE, artist)
        metadata.putString(metadata_cls.METADATA_KEY_ALBUM,
                           str(data.get('album') or ''))
        metadata.putLong(metadata_cls.METADATA_KEY_DURATION,
                         int(data.get('duration_ms') or 0))
        cover_bitmap = None
        cover = str(data.get('cover') or '')
        if cover and os.path.isfile(cover):
            try:
                cover_bitmap = bitmap_factory.decodeFile(cover)
                if cover_bitmap is not None:
                    metadata.putBitmap(metadata_cls.METADATA_KEY_ART, cover_bitmap)
                    metadata.putBitmap(metadata_cls.METADATA_KEY_ALBUM_ART, cover_bitmap)
            except Exception as exc:
                print('JustMusic service cover:', exc)
        session.setMetadata(metadata.build())
        return cover_bitmap

    def update_playback_state(data):
        playing = bool(data.get('playing'))
        state = state_builder_cls()
        state.setActions(actions)
        state.setState(
            state_cls.STATE_PLAYING if playing else state_cls.STATE_PAUSED,
            int(data.get('position_ms') or 0), 1.0 if playing else 0.0)
        session.setPlaybackState(state.build())

    def update_notification(data, bitmap):
        playing = bool(data.get('playing'))
        if build_version.SDK_INT >= 26:
            builder = builder_cls(service, channel_id)
        else:
            builder = builder_cls(service)
        builder.setSmallIcon(android_drawable.ic_media_play)
        builder.setContentTitle(str(data.get('title') or 'JustMusic!'))
        builder.setContentText(str(data.get('artist') or 'Ismeretlen előadó'))
        builder.setSubText(str(data.get('album') or ''))
        builder.setContentIntent(activity_intent())
        builder.setCategory(notification_cls.CATEGORY_TRANSPORT)
        builder.setVisibility(notification_cls.VISIBILITY_PUBLIC)
        builder.setOngoing(playing)
        builder.setOnlyAlertOnce(True)
        try:
            builder.setPriority(notification_cls.PRIORITY_LOW)
        except Exception:
            pass
        if bitmap is not None:
            builder.setLargeIcon(bitmap)
        for icon, name, action, code in (
            (android_drawable.ic_media_previous, 'Előző',
             'hu.zs420ller.justmusic.action.PREVIOUS', 4201),
            (android_drawable.ic_media_pause if playing else android_drawable.ic_media_play,
             'Szünet' if playing else 'Lejátszás',
             'hu.zs420ller.justmusic.action.TOGGLE', 4202),
            (android_drawable.ic_media_next, 'Következő',
             'hu.zs420ller.justmusic.action.NEXT', 4203),
        ):
            builder.addAction(icon, name, activity_intent(action, code))
        try:
            style = media_style_cls()
            style.setMediaSession(session.getSessionToken())
            style.setShowActionsInCompactView([0, 1, 2])
            builder.setStyle(style)
        except Exception as exc:
            print('JustMusic service MediaStyle:', exc)
        # A notification most már valódi előtérszolgáltatáshoz tartozik.
        service.startForeground(420, builder.build())

    path = os.environ.get('PYTHON_SERVICE_ARGUMENT', '')
    if not path:
        raise RuntimeError('Hiányzik a médiastátusz-fájl útvonala')
    heartbeat_path = path + '.heartbeat'
    last_heartbeat = 0.0
    last_seq = None
    last_track = None
    last_playing = None
    try:
        while True:
            try:
                if time.monotonic() - last_heartbeat > 2.5:
                    with open(heartbeat_path, 'w', encoding='utf-8') as hb:
                        hb.write(str(time.time()))
                    last_heartbeat = time.monotonic()
                with open(path, encoding='utf-8') as f:
                    data = json.load(f)
                if data.get('shutdown'):
                    break
                seq = data.get('seq')
                if seq != last_seq:
                    key = (data.get('title'), data.get('artist'), data.get('album'),
                           data.get('duration_ms'), data.get('cover'))
                    playing = bool(data.get('playing'))
                    if key != last_track or playing != last_playing:
                        bitmap = update_session(data)
                        update_playback_state(data)
                        update_notification(data, bitmap)
                        last_track, last_playing = key, playing
                    else:
                        update_playback_state(data)
                    last_seq = seq
            except FileNotFoundError:
                pass
            except (ValueError, OSError) as exc:
                print('JustMusic service state read:', exc)
            time.sleep(.65)
    finally:
        try:
            os.unlink(heartbeat_path)
        except OSError:
            pass
        try:
            session.setActive(False)
            session.release()
        except Exception:
            pass
        try:
            service.stopForeground(True)
            service.stopSelf()
        except Exception:
            pass


if __name__ == '__main__':
    try:
        run()
    except BaseException:
        traceback.print_exc()
