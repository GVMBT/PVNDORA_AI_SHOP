# PVNDORA Sound Library

## File Mapping

### Background Music
- `sound.ogg` - Ambient background music (looped, 20% volume)

### UI Sounds
- `click-project.ogg` → `AudioEngine.click()` - Button clicks
- `ui-short.ogg` → `AudioEngine.open()`, `AudioEngine.close()`, `AudioEngine.panelOpen()`, `AudioEngine.panelClose()` - Modal open/close, navigation, sidebar
- `ui-long.ogg` → `AudioEngine.productOpen()` - Product card open

### System Sounds
- `Dossier.ogg` → `AudioEngine.decrypt()` - Referral dossier decrypt, data reveal

### Notification Sounds
- `success.ogg` → `AudioEngine.success()` - Success notifications
- `error.ogg` → `AudioEngine.error()` - Error notifications
- `warning.ogg` → `AudioEngine.warning()` - Warning notifications
- `notification.ogg` → `AudioEngine.notification()` - HUD log entries

### Commerce Sounds
- `add-to-cart.ogg` → `AudioEngine.addToCart()` - Item added to cart
- `transaction.ogg` → `AudioEngine.transaction()` - Purchase complete

## Missing Files (To Be Created)

The following sounds are still using procedural fallback:
- `success.ogg` - Success notification
- `error.ogg` - Error notification
- `warning.ogg` - Warning notification
- `notification.ogg` - HUD notification
- `add-to-cart.ogg` - Add to cart
- `transaction.ogg` - Transaction complete

## Procedural Sounds (No Files Needed)

These sounds use procedural generation for variety:
- `hover()` - Light hover (too short for file)
- `boot()` - Complex boot sequence
- `type()` - Random typing character
- `typewriter()` - Typewriter effect (uses procedural for variety)
- `scan()` - Dynamic scan sound
- `connect()` - Connection established
- `disconnect()` - Connection lost
- `glitch()` - Random glitch effect

## Audio Engine Architecture

### Optimization Strategy

**AudioBuffer Caching:**
- Short SFX (<1s) are loaded via `fetch` and decoded into `AudioBuffer`
- Buffers are cached in memory for instant playback
- No Audio Worker needed for short sounds - `AudioBuffer` is sufficient

**Background Music:**
- Uses `HTMLAudioElement` for long-form audio
- Preloaded via `fetch` + `Blob` URL for better buffering
- Handles `waiting`, `stalled`, `seeking` events with retry logic

**Fallback System:**
- If `.ogg` file fails to load, falls back to procedural generation
- Ensures UI always has audio feedback even if files are missing

### Preloading

Critical sounds are preloaded on `AudioEngine.init()`:
- `click`, `uiShort`, `uiLong`, `success`, `error`, `notification`

Background music is preloaded in `BootSequence` and waits for `canplaythrough`.

## File Locations

All sound files should be placed in `/public/` directory (root of public assets):
- `/public/sound.ogg` - Background music
- `/public/click-project.ogg` - Click sound
- `/public/ui-short.ogg` - UI short actions
- `/public/ui-long.ogg` - UI long actions
- `/public/Dossier.ogg` - Decrypt sound
- `/public/success.ogg` - Success (to be created)
- `/public/error.ogg` - Error (to be created)
- `/public/warning.ogg` - Warning (to be created)
- `/public/notification.ogg` - Notification (to be created)
- `/public/add-to-cart.ogg` - Add to cart (to be created)
- `/public/transaction.ogg` - Transaction (to be created)

## Format Requirements

- **Format:** OGG Vorbis (`.ogg`)
- **Sample Rate:** 44.1kHz or 48kHz
- **Bitrate:** 128-192 kbps (balance quality/size)
- **Duration:** 
  - UI sounds: 0.1-0.3s
  - Notifications: 0.2-0.5s
  - Commerce: 0.3-1.0s
  - Background music: Any length (looped)

## Integration Notes

1. All sounds are loaded asynchronously via `fetch` + `decodeAudioData`
2. Failed loads fall back to procedural generation (no errors shown to user)
3. Master volume controlled via `AudioEngine.setVolume()` (default: 0.5)
4. Individual sound volumes can be adjusted in `playSoundFile()` calls
