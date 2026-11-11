# Mochi Companion Housing (`MC-RB5320-R03`)

Desktop companion robotic housing for the `RB5320XZ78AI` edge computing platform, engineered with an Apple-minimalist continuous superellipse unibody (`86.0 × 48.1 × 104.0 mm` total envelope) with flush stepped architectural screen rim, 100% tool-free zero-screw snap-hinge assembly (`6` pure FDM parts, `0` screws, `0` heat-set inserts, `0` acrylic panels), open pass-through docking cradle, 3 captive rear tactile buttons (`Vol+`, `PTT`, `Vol-`), and Apple Mac Studio/Pro 132-dot parametric micro-perforations (`26` front + `93` rear + `13` top crown chimney).

Modeled natively in Blender 5.2.0 LTS using parametric BPY construction, strict manifold geometry, and automated digital production gates.

License: **FREE + source-available (PolyForm Shield 1.0.0)**. See [`../../LICENSE`](../../LICENSE).

---

## Delivery Status

| Track | Status | Verification & Evidence |
|---|---|---|
| **Digital Fit & Geometry** | **PASS** | 0 BVH interpenetrations across 75 pairs and 0 cable-plug overlaps across 10 electronic modules and 6 printed FDM components ([`integration-receipt.json`](./integration-receipt.json)). 6/6 parts passed digital production gate ([`gate-report.json`](./gate-report.json)) with full audit coverage ([`coverage-audit.json`](./coverage-audit.json)). |
| **Kinematics & Cabling** | **PASS** | `3×` captive rear buttons actuate with 12–16 hits on `EL10` tactile switches at `-0.80 mm` click stroke with 0 part or cable clashes. Dock features a 50 mm open vertical through-hole and rear cable channel with 0 collision against full-depth inserted USB-C cable plugs ([`integration-receipt.json`](./integration-receipt.json)). |
| **Media (Stills)** | **PASS** | 6 studio stills converted to metadata-free WebP showcase assets in [`../../docs/assets/housing/`](../../docs/assets/housing/). |
| **Motion (Film)** | **PASS** | Full 12-shot 30 fps product film ([English MP4](../../docs/assets/housing/motion-16x9.mp4) & [Vietnamese MP4](../../docs/assets/housing/motion-16x9.vi.mp4), `36.0s`, `1,080` distinct rendered states, `pose_rate_hz: 30.0`, muxed with licensed soundtrack *"Edge of Motion"* by Aetheric at `-14 LUFS` / `-1.5 dBTP`). |
| **Manufacture (Physical)** | **BLOCKED** | **Zero physical prototypes printed yet.** Physical production and electrical assembly remain strictly blocked pending: (1) FDM PETG/PLA+ snap-hinge deflection and 50-cycle latch fatigue coupon testing, (2) physical `RB5320XZ78AI` drop-in fit check, (3) 2-hour 18650/TP4056 thermal soak under full compute load, and (4) INMP441 microphone and speaker acoustic baffle trials. |

---

## 6-Part Printable STL Manifest

All 6 printable parts are watertight closed manifold solids (0 non-manifold edges, 0 zero-area faces, 1 closed shell each, signed volume > 0), and enforce `min_wall_mm >= 1.80 mm` throughout. 100% tool-free assembly (`6` pure FDM parts, `0` screws, `0` heat-set inserts, `0` acrylic panels).

| Part ID | Object | Dimensions (mm) | Volume (mm³) | Min Wall (mm) | Print Up | STL File & SHA-256 | Gate Status |
|---|---|---|---|---|---|---|---|
| `shell_front` | `MC_Shell_Front` | 86.0 × 24.8 × 104.0 | 32,354.00 | 1.9054 (req ≥ 1.80) | `+y` | [`./stl/shell_front.stl`](./stl/shell_front.stl)<br>`a06820c9e8dc30dbceddfcebec73467e9e79143150b66232b5d52a3262a7d02e` | **PASS** |
| `shell_rear` | `MC_Shell_Rear` | 86.0 × 28.0 × 103.97 | 34,744.80 | 1.8163 (req ≥ 1.80) | `-y` | [`./stl/shell_rear.stl`](./stl/shell_rear.stl)<br>`bc0a2747d064408f301a9b24134f7d381dbecec5c5b1c4dc614f87811d9ee413` | **PASS** |
| `btn_vol_up` | `MC_Btn_Left` | 8.8 × 24.4 × 8.1 | 635.40 | 2.6000 (req ≥ 1.80) | `+z` | [`./stl/btn_vol_up.stl`](./stl/btn_vol_up.stl)<br>`5d0ff35686e4d78bc758a6da24ff571f930ad4b4fafee8c489bd77a09de5c9c8` | **PASS** |
| `btn_ptt` | `MC_Btn_Center` | 11.0 × 24.7 × 8.1 | 738.20 | 2.3000 (req ≥ 1.80) | `+z` | [`./stl/btn_ptt.stl`](./stl/btn_ptt.stl)<br>`08162f5afe4f5c5c975569dbbc5bd289af6c0a3d586120715d07a0b27a1a3572` | **PASS** |
| `btn_vol_dn` | `MC_Btn_Right` | 8.9 × 24.4 × 8.1 | 595.22 | 2.6000 (req ≥ 1.80) | `+z` | [`./stl/btn_vol_dn.stl`](./stl/btn_vol_dn.stl)<br>`ad8090ed36d196a30fd901accce7dcb83875a2b1cb72cc832346f6d136da7261` | **PASS** |
| `desk_stand` | `MC_Desk_Stand` | 96.0 × 64.0 × 45.0 | 160,770.28 | 4.1527 (req ≥ 1.80) | `+z` | [`./stl/desk_stand.stl`](./stl/desk_stand.stl)<br>`b4d871e49fa33e19fb3a65c0177e0d81cd6c4a761d19b3ff07b1854f38068139` | **PASS** |

See [`./stl/manifest.json`](./stl/manifest.json) for machine-readable part definitions.

---

## Architectural & Mechanical Design

### 1. Continuous Superellipse Unibody
- Outer envelope: `86.0 × 48.1 × 104.0 mm`.
- Profile: Superellipse formula `|x/a|^n + |z/b|^n = 1` with curvature index `n = 3.2`, creating continuous highlight roll-off without sharp corner boundaries.
- Display integration: 2.8-inch ST7789 display module mounted flush against the stepped architectural front bezel with 0.20 mm perimeter tolerance.

### 2. 100% Tool-Free Zero-Screw Snap-Hinge Assembly
- `11°` top crown twin hook-hinges: Two curved hook claws locate and pivot the front and rear clamshell halves at the top rim.
- `0.25 mm` side elastic cantilever snap-locks: Lower side tabs lock the shells securely together with zero screws, zero brass heat-set threaded inserts, and zero acrylic panels.
- Disassembly: Release tabs flex inward through the bottom open port with a nylon spudger.

### 3. Captive Living-Hinge Rear Tactile Buttons
- `3×` rear captive push buttons (`Vol+`, `PTT`, `Vol-`) arranged vertically on the rear shell centerline.
- Kinematic stroke: `ΔY = -0.80 mm` travel onto onboard `EL10` SMD tactile switches.
- Retaining rails prevent buttons from dropping out when the housing is opened.

### 4. 132-Dot Apple Parametric Micro-Aperture Arrays
Parametric acoustic and ventilation micro-perforations inspired by Mac Studio thermal architecture:
1. **Front upper acoustic array (`Z = 99.50 mm`)**: 7 graded micro-dots (`Ø1.40 mm` to `Ø2.00 mm`) aligned with the MEMS microphone intake.
2. **Front lower chin intake (`Z = 15.20 & 18.80 mm`)**: 19 tapered honeycomb micro-dots (`Ø1.40 mm` to `Ø1.90 mm`) for cool ambient air intake.
3. **Rear upper radial acoustic halo (`Z = 76.00 mm`)**: 61 graded radial micro-dots (`Ø1.60 mm` to `Ø2.50 mm` across 4 concentric rings) tuned for the rear chamber speaker.
4. **Rear mid honeycomb intake (`Z = 38.90, 42.80, 46.70 mm`)**: 31 tapered honeycomb micro-dots (`Ø1.68 mm` to `Ø2.24 mm`) for cross-flow ventilation over the ESP32-S3 module.
5. **Rear status pinhole (`Z = 31.20 mm`)**: 1 centered `Ø2.20 mm` bore for boot/status LED visibility.
6. **Top crown chimney exhaust (`Z = 104.50 mm`)**: 13 parametric chimney vents (`Ø1.76 mm` to `Ø2.20 mm`) venting convection thermal plume.
Total: `7 + 19 + 61 + 31 + 1 + 13 = 132` micro-apertures.

### 5. 50.0 mm Open-Floor Weighted Desk Dock
- Base dimensions: `96.0 × 64.0 × 45.0 mm`.
- Elevation: Elevates companion unit `35.0 mm` above desktop with a relaxed `12°` backward viewing tilt.
- Cable pass-through: `50.0 mm` wide open vertical floor aperture with rear U-channel, allowing all 3 bottom USB-C cables (TP4056 charge input + dual ESP32-S3 auxiliary ports) to remain permanently connected while seating or lifting the companion.
- Weight cavity: Internal cavity accommodates ballast plates or lead-free weights for stable one-handed docking.

---

## Engineering Receipts

Authoritative digital validation receipts generated during automated Blender headless gate execution:
- [`spec.json`](./spec.json) — Authoritative engineering specification defining envelope, tolerances, hole patterns, fastener constraints, and gate criteria.
- [`gate-report.json`](./gate-report.json) — Automated digital production gate report verifying watertight topology, dimensional accuracy, minimum wall thickness, and manifold status across all 6 printable parts.
- [`coverage-audit.json`](./coverage-audit.json) — Coverage audit confirming every declared part and feature check was executed without waivers or skips.
- [`integration-receipt.json`](./integration-receipt.json) — Digital clearance and kinematic actuation check report confirming zero part clashes and zero cable collisions.
- [`stl/manifest.json`](./stl/manifest.json) — Hash-verified STL part manifest with geometry metrics.

---

## Media & Product Film

- **12-Shot 3D Product Film**:
  - English Master (`1080p30 MP4`): [`../../docs/assets/housing/motion-16x9.mp4`](../../docs/assets/housing/motion-16x9.mp4)
  - Vietnamese Master (`1080p30 MP4`): [`../../docs/assets/housing/motion-16x9.vi.mp4`](../../docs/assets/housing/motion-16x9.vi.mp4)
  - Audio License & Provenance: [`../../docs/assets/housing/AUDIO-PROVENANCE.md`](../../docs/assets/housing/AUDIO-PROVENANCE.md)
  - Music track: *Edge of Motion* by Aetheric — Source: https://freetouse.com/music
- **Studio Stills Gallery**: [`../../docs/assets/housing/`](../../docs/assets/housing/)
