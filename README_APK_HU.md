# JustMusic! Mobile 1.0 — APK READY

Ez a projekt NEM a desktop Tkinter program közvetlen átalakítása.
Androidra külön Kivy UI készült, hogy valódi APK legyen belőle.

## Ami már benne van
- Neon / party háttér
- Helyi Music és Download mappa beolvasása
- Dalok listázása és keresése
- Play / pause / előző / következő
- Időcsúszka
- LRC dalszöveg támogatás
- Teljes mobilos dalszöveg nézet
- Android média-hozzáférési engedélykérés
- GitHub Actions APK build

## APK építés — legegyszerűbb
1. GitHubon nyisd meg a JustMusic-Mobile repositoryt.
2. A ZIP TELJES tartalmát töltsd fel a repository gyökerébe.
   FONTOS: a `.github` mappa is menjen fel.
3. Commit.
4. Actions -> `Build JustMusic Android APK`.
5. `Run workflow`.
6. Ha zöld pipa lett, nyisd meg a futást.
7. Artifacts -> `JustMusic-Android-APK`.
8. Töltsd le a ZIP-et; benne lesz az APK.

## Telefon
A zenéket tedd például:
- /storage/emulated/0/Music
- /storage/emulated/0/Download

Az LRC fájl neve egyezzen a zenével:
`zene.mp3`
`zene.lrc`
