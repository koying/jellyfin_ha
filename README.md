# jellyfin_ha

Jellyfin integration for Home Assistant

## Features

### Entities

- 1 media_player entity per device
- 1 sensor per server
- Supports the "upcoming-media-card" custom card

### Media Browser

- Browse medias and start playback from within Home Assistant

### Media Source

- Browse and stream to a cast device (e.g. Chromecast)

### Services

- `trigger_scan`: Trigger a server media scan
- `browse`: Show a media info on a device
- `delete`: Delete a media
- `search`: Search for media (for compatible fontends)

### Upcoming Media Card

###### Sample for ui-lovelace.yaml:

```
- type: custom:upcoming-media-card
  entity: sensor.jellyfin_media_server
  title: Latest Media
```

---

#### [View Changelog](changelog/changelog.md)

