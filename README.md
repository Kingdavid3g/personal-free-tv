# Personal Free TV — USA

## Playlist URL

```text
https://raw.githubusercontent.com/Kingdavid3g/personal-free-tv/main/playlist.m3u
```

## EPG URL (TiviMate and UHF)

```text
https://raw.githubusercontent.com/Kingdavid3g/personal-free-tv/main/epg.xml
```

Refresh the playlist first to load the updated channel IDs, then refresh the EPG. Add the EPG URL as this playlist's XMLTV/guide source if your player does not detect the embedded URL. No account or token is required to download either file. If GitHub briefly returns the old playlist, wait a few minutes and refresh again, or use https://raw.githubusercontent.com/Kingdavid3g/personal-free-tv/refs/heads/main/playlist.m3u as the playlist URL.

For TiviMate: add the guide under EPG sources, assign it to this playlist, then update the guide. For UHF: use this guide URL as the playlist's EPG source and refresh the playlist and guide. Menu wording depends on the app version. No manual time offset should be needed; guide timestamps include time zones.

## Coverage and updates

The first published guide has upcoming schedules for 978 of 1,167 playlist entries (about 84%). This is not complete or necessarily gap-free coverage. All channels remain in the lineup, including ones without schedules. [Current coverage and missing-channel list](COVERAGE.md) is rebuilt with the guide.

GitHub Actions is scheduled to refresh guide data every four hours, with a manual Run workflow option under Actions → Refresh TV guide. Scheduled runs can be delayed. Check Actions if the guide becomes stale. The channel lineup itself is a fixed snapshot and is not automatically expanded or checked for dead streams.

Guide matching uses provider-specific channel IDs, exact normalized names, and Tubi stream identifiers. It does not substitute another service's schedule or fabricate programmes. The DistroTV source currently has no unexpired programmes; no verified Stirr guide source is configured. Other gaps reflect missing or ambiguous channel matches or unavailable schedules.

## Maintenance

Edit channels.m3u to change the lineup; playlist.m3u is generated and will be overwritten by guide updates. The updater preserves stream URLs and assigns stable guide IDs. scripts/update_epg.py generates epg.xml, playlist.m3u, COVERAGE.md, and coverage.json. If fewer than half the lineup has upcoming schedules, the update fails instead of overwriting the published files. A failed update does not keep the previously published schedules fresh.

## Sources

Channel lists: https://github.com/iptv-org/iptv/tree/master/streams (USA Pluto, Plex, Tubi, Samsung, Roku, Xumo, DistroTV, Stirr files).

Guide feeds: https://github.com/matthuisman/i.mjh.nz (Pluto TV, Samsung TV Plus, Plex and Roku); https://github.com/BuddyChewChew/tubi-scraper (Tubi); https://epgshare01.online/epgshare01/ (DistroTV). Xumo schedule API and channel mapping are based on https://github.com/iptv-org/epg/tree/master/sites/xumo.tv.

These are community-listed streams, not complete official service catalogs. Original stream manifest checks were performed September 24, 2026; actual playback and regional availability vary. World at War is not included because no verified free public stream was found; Newsmax lists it with Newsmax+: https://www.newsmaxplus.com/.

This repository hosts playlist and guide text, not video.
