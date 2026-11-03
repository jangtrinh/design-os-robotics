# Brainstorm: Personalized Mochi Context-True Theme + ElevenLabs Vietnamese Voice + Custom Wake Words ("Hello J" / "Hi J" / "Yo J")

- **Date:** 2026-11-02
- **Target Hardware:** RoBot.5320 (`ESP32-S3-WROOM-1-N16R8`, MAC `AA:BB:CC:DD:EE:FF`, `/dev/cu.usbmodem*`, LAN `192.0.2.10`)
- **Firmware Base:** `TanDev - Xiaozhi AI IoT Vietnam v2.5.3` (`07-ota1-v2.5.3-0x560000.bin`)
- **Pipeline:** `es:feature-dev --full` (`Astra Work` + `Fable Thinking` epistemic ledger)

---

## 1. Press Release (Working Backwards)

**Headline:** RoBot.5320 Speaks in Your Custom Vietnamese ElevenLabs Voice (`Giang`), Wakes to `"Hello J"`, `"Hi J"`, and `"Yo J"`, and Displays Calm, Context-True Shouto Mochi Expressions.

**Problem Statement:**
1. **Continuous State Jumping in Theme:** Previously, chaining 3 distinct sticker animations (`3 scenes × 5 frames`) inside each single GIF slot (`EMOTION_SCENES_63`) caused the robot's face to jump between 3 different poses every 1.8 seconds even while sitting idle in `neutral`.
2. **Missing On-Device Custom Voice:** Generating the ElevenLabs Custom Voice (`<ELEVENLABS_VOICE_ID>`) Vietnamese audio files on disk did not change the robot's voice because the 38 embedded `Ogg Opus` audio streams live inside the compiled `ota_1` firmware partition (`0x560000`, `Seg 0` `0x02efc4..0x04aefd`).
3. **`mn7_en` Boot Panic on Custom Wake Words:** Packing `mn7_en` caused a `LoadProhibited` panic at `0x420732a1` (`strlen(NULL)`) because `CustomWakeWord::Initialize` (`0x4204ce2d`) calls `esp_mn_commands_add(id, text)` (setting `phrase->string` at `[+0]` and leaving `phrase->phonemes` at `[+4]` as `NULL`), whereas `mn7_en` (`language == 2`) reads `[+4]`.

**Solution (Machine-Code Verified `FACT`s):**
1. **Context-True Single-Scene Shouto Mochi Theme (21 Smooth GIFs + 92 Mapped Keys):**
   - Each of the 21 emotion GIF slots contains **1 cohesive, smooth, single-context animation** (`12 frames @ 8 fps`, `max_colors=12`, `240×240`).
   - When idle (`neutral`), Mochi stays calmly breathing/blinking without jumping states. It only switches to `happy`, `thinking`, `sad`, `angry`, `laughing`, `sleepy`, etc. when the AI/system context transitions to that emotion or one of the 71 mapped system/UI icon keys (`92` total keys in `index.json`).
2. **On-Device ElevenLabs Vietnamese Voice (`Giang`, `<ELEVENLABS_VOICE_ID>`) Patched into `ota_1` (`0x560000`):**
   - Disassembly of `0x42030100..0x42030850` proved that all 38 embedded `OggS` streams (`0x02efc4..0x04aefd`, `114,489 B` total) are referenced exclusively via `_start` and `_end` pointers in the literal pool at `file 0x102b98..0x102da0`, and the image ends at `0x37d340` (`3,658,560 B`) with an unencrypted 1-byte XOR checksum (`0x37d31f`) and 32-byte SHA256 digest (`0x37d320..0x37d340`).
   - We synthesize all Vietnamese voice prompts (`Ogg[16..31]`: digits `0..9`, `activation`, `err_pin`, `err_reg`, `upgrade`, `welcome`, `wificonfig`) PLUS the wake-up / listening response (`Ogg[35]` `P3_POPUP`: *"Dạ, J nói đi!"*) and boot-ready greeting (`Ogg[36]` `P3_SUCCESS`: *"Chào J! Mình sẵn sàng rồi nè!"*) using ElevenLabs Custom Voice (`eleven_v4`, `language_code="vi"`), patch them into `07-ota1-v2.5.3-0x560000.bin`, update the literal pool + XOR checksum + SHA256, and flash `ota_1`.
3. **Vietnamese Primary + `"Hello J"`, `"Hi J"`, `"Yo J"` Wake Words via `mn6_en` (`MultiNet6 English`):**
   - Disassembly of `mn6`'s `set_speech_commands` (`0x42070e64`, `file 0x170e64`) proved that `mn6_en` loads `phrase->string` (`0x170e86: l32i.n a11, a9, 0`) unconditionally and encodes uppercase English strings using SentencePiece BPE (`mn6_en/vocab`).
   - We pack `mn6_en` (`3.60 MB`) + `fst` into `srmodels.bin`, register both `"J"` and `"JAY"` phonetic spellings (`"HELLO J"`, `"HELLO JAY"`, `"HI J"`, `"HI JAY"`, `"YO J"`, `"YO JAY"`, `"HEY J"`, `"HEY JAY"`) in `index.json` -> `"multinet_model"`, and free `307 KB` by omitting optional `"background_image"` (`"background_color": "#000000"`) so the entire `assets` binary fits comfortably within `5,636,096 B` (`0x560000`).

---

## 2. Epistemic Ledger (`es:fable-thinking`)

| ID | Claim | Tier | Evidence |
|---|---|---|---|
| `E1` | `CustomWakeWord::Initialize` (`0x4204cc60`) calls `esp_mn_commands_add(id, cmd.command.c_str())` (`0x4204ce2d`), populating `phrase->string` (`[+0]`) and leaving `phrase->phonemes` (`[+4]`) as `NULL`. | `FACT` | Disassembly of `07-ota1-v2.5.3-0x560000.bin` at `file 0x14cc60..0x14ce50` and `0x15b2c4`. |
| `E2` | `mn6_en` (`vtable` at `0x09ace0`, `set_speech_commands` at `0x42070e64`) reads `phrase->string` (`0x170e86: l32i.n a11, a9, 0`) and encodes commands with SentencePiece BPE (`0x422203bc`). | `FACT` | Disassembly of `file 0x170e64..0x170eff` and `mn6_en/vocab` inspection (`7,314 B`). |
| `E3` | `CustomWakeWord::ParseWakenetModelConfig` (`0x4204c61c`) converts `threshold` (`cJSON->valuedouble`) directly to `float` via `__truncdfsf2` (`0x4000252c`) without dividing by `100.0`. | `FACT` | Disassembly of `file 0x14c6df..0x14c740`. |
| `E4` | All 38 embedded `OggS` streams (`0x02efc4..0x04aefd`, `114,489 B`) are referenced solely via `_start` and `_end` pointers in `file 0x102b98..0x102da0`. | `FACT` | Full-binary pointer scan + disassembly of `0x130100..0x130850`. |
| `E5` | `Ogg[35]` (`0x3fcad00c`, `P3_POPUP`) is played by `AudioService::PlaySound` (`0x420113bc`) whenever the robot wakes up or enters listening mode (`pc=0x12996f`, `0x12a6d6`). | `FACT` | Call-graph scan of `call8 0x11112c` in `07-ota1-v2.5.3-0x560000.bin`. |

---

## 3. MoSCoW Priorities

- **Must Have:**
  - Single-context Mochi animations (1 cohesive scene per emotion across all 21 GIFs; `neutral` stays calm until context changes) + 92 `EmojiCollection` keys mapped.
  - Custom wake words `"Hello J"`, `"Hi J"`, `"Yo J"` (plus `"Hey J"`) working via `mn6_en` without crash while keeping Vietnamese (`vi-VN`) as primary language.
  - On-device ElevenLabs Custom Voice Vietnamese voice patched into `07-ota1-v2.5.3-0x560000.bin` (`Ogg[16..31]` + `Ogg[35]` wake response + `Ogg[36]` ready greeting) and flashed to `0x560000`.
- **Should Have:**
  - Reversible backup & CLI tool (`tools/patch-ota1-voice.py`) that verifies ESP-IDF XOR checksum + SHA256 before flashing.
  - Contact sheet (`docs/assets/shouto-mochi-contact-sheet.png`) updated to reflect the 21 single-context Mochi animations.
- **Could Have:**
  - Cloud TTS Voice Clone helper instructions (`xiaozhi.me` + `00-elevenlabs-giang-22s-golden.wav`).
- **Won't Have:**
  - Chained multi-scene GIFs that jump poses inside a single emotion state.
