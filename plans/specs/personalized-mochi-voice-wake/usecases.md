# Use Cases & Acceptance Criteria: Personalized Mochi Theme + Voice + Wake Words

## UC-01: Context-True Mochi Emotion Rendering (No Continuous State Jumping)
- **Actor:** User observing the 240×320 IPS screen across idle, listening, thinking, speaking, and system alert contexts.
- **Preconditions:** `themes/shouto-mochi-fullvien-240x320.bin` flashed to `assets` (`0xAA0000`).
- **Scenario:**
  ```gherkin
  Given the robot is in the idle ("neutral") state
  When no conversation or system event is occurring
  Then the screen displays a single calm, cohesive Mochi breathing/blinking animation without jumping to unrelated sticker poses
  And when the AI or system context changes to another state (e.g., "happy", "thinking", "sad", "sleepy", or any of the 71 system icon keys)
  Then the screen smoothly switches to the corresponding single-context Mochi animation.
  ```

## UC-02: Custom Wake Words ("Hello J", "Hi J", "Yo J") with Vietnamese Primary Language
- **Actor:** User speaking `"Hello J"`, `"Hi J"`, or `"Yo J"` to wake the robot, then conversing in Vietnamese.
- **Preconditions:** `srmodels.bin` inside `assets` (`0xAA0000`) contains `mn6_en` (`MultiNet6 English`) + `fst`, and `index.json` defines `"multinet_model"` with `"HELLO J"`, `"HELLO JAY"`, `"HI J"`, `"HI JAY"`, `"YO J"`, `"YO JAY"`, `"HEY J"`, `"HEY JAY"`.
- **Scenario:**
  ```gherkin
  Given the robot boots with language "vi-VN" and assets partition at 0xAA0000
  When CustomWakeWord::Initialize loads "multinet_model" from index.json
  Then mn6_en initializes and updates FST speech commands without any LoadProhibited crash
  And when the user says "Hello J", "Hi J", or "Yo J"
  Then the robot wakes up and transitions to Listening state in Vietnamese.
  ```

## UC-03: On-Device ElevenLabs Vietnamese Voice (`Giang`)
- **Actor:** User booting, waking, or receiving system notifications from the robot.
- **Preconditions:** `07-ota1-v2.5.3-0x560000.bin` patched with ElevenLabs Custom Voice (`<ELEVENLABS_VOICE_ID>`, `eleven_v4`, `language_code="vi"`) `Ogg Opus` streams and flashed to `ota_1` (`0x560000`).
- **Scenario:**
  ```gherkin
  Given the patched ota_1 firmware is flashed to 0x560000 with valid ESP-IDF XOR checksum and SHA256 digest
  When the robot boots, wakes up ("P3_POPUP"), or announces Vietnamese system states ("welcome", "wificonfig", "upgrade", "activation", digits 0..9)
  Then AudioService::PlaySound plays the ElevenLabs Custom Voice Vietnamese voice prompts clearly through the speaker.
  ```
