---
status: ratified
name: design-os-robotics
aesthetic: Dark Industrial Precision
tokens: design/design.tokens.json
---

# design-os-robotics — Design Soul

## Stance

Dark, flat, single-accent engineering instrument for ESP32-S3 robotic companions. Built on an obsidian zinc canvas (`#09090b` `--c-gray-100`), elevated matte cards (`#121215` `--c-gray-200`), crisp `1px solid #27272a` (`--c-gray-400`) structural borders, self-hosted `Be Vietnam Pro` typography (`400`, `600`, `800`), system monospace telemetry (`font-variant-numeric: tabular-nums`), and one warm orange accent (`#fca849` `--c-accent` with `#09090b` `--c-accent-fg` ink). Every pixel serves physical hardware inspection, procedural 240×240 OLED expression fidelity, and zero-PII public engineering transparency.

## Always

- Use the canonical dark zinc surface ramp (`--c-canvas: #09090b`, `--c-gray-200: #121215`, `--c-gray-300: #18181b`, `--c-gray-400: #27272a`) with `1px solid var(--c-border)` hairlines and zero drop shadows.
- Reserve the single orange accent (`--c-accent: #fca849` with `--c-accent-fg: #09090b`) for the primary focus action of a view, keeping meter fills and slider tracks monochrome (`#f4f4f5` fill on `#27272a` track).
- Self-host `Be Vietnam Pro` (`400`, `600`, `800`) and pair with system monospace (`tabular-nums`) for all sensor readouts, valence/arousal coordinates, and byte counters.
- Render the Procedural Mochi-21 face at native `240×240` (`image-rendering: pixelated`) on a pure `#000000` OLED tile framed by `1px solid #27272a` and `16px` (`~7%`) corner radius.
- Build custom design-system controls (`role="slider"` track + thumb, Phosphor Regular `.ph` icons, capsule pills with `>=44px` coarse-pointer hit targets) and guard all `:hover` styles behind `@media (hover: hover)`.

## Never

- Never hotlink Google Fonts (`fonts.googleapis.com`, `fonts.gstatic.com`) or external CDN stylesheets; all fonts and icons are self-hosted in `docs/assets/`.
- Never introduce secondary neon accents (cyan, purple, emerald, rose), multi-stop gradients, glassmorphism blurs, or decorative glow shadows that compete with the 240×240 OLED face.
- Never use raw native form controls (`<input type="range">`, `<select>`, `<input type="checkbox">`) or raw Unicode/emoji glyphs where custom DS controls and Phosphor Regular `.ph` icons belong.
- Never expose MAC addresses, serial device paths, LAN IPv4 literals, port numbers, or filesystem paths in UI copy, screenshots, or committed code.

## Voice

- Write clear, grounded, first-principles hardware and companion-AI engineering prose in English.
- Name observable physical or affective quantities (`Valence`, `Arousal`, `Energy`, `Social Drive`, `Curiosity`, `USB-JTAG: Ready`, `Wi-Fi LAN: Ready`) without marketing hype or anthropomorphized fluff.
- Keep badge and button labels concise (`2–4` words) and pair every numeric telemetry readout with explicit units (`V`, `A`, `FPS`, `KB`, `%`).
