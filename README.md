# Spectrum Image Maker

A browser-based image converter for classic 8-bit and 16-bit machines. Converts JPG/PNG images to native graphics formats for the ZX Spectrum, Timex/Sinclair 2068, Commodore 64, Atari 800, and Sinclair QL.

**[Try it live →](https://factus10.github.io/spectrum-image-maker/)**

## Supported display modes

| Machine | Mode | Resolution | Attributes | Colors | File |
|---|---|---|---|---|---|
| ZX Spectrum | Standard | 256×192 | 8×8 | 2 of 16 (Normal + Bright) | `.scr` / `.tap` |
| TS 2068 | Extended Color (ECM) | 256×192 | **8×1** | 2 of 16 per strip | `.scr` / `.tap` |
| TS 2068 | 64-column hi-res | 512×192 | global | 2 user-picked (mono) | `.scr` / `.tap` |
| C64 | Hi-res bitmap | 320×200 | 8×8 | 2 of 16 (Pepto) | `.prg` |
| C64 | Multicolor / Koala | 160×200 | 4×8 | 4 of 16 + global bg | `.kla` |
| Atari 800 | GR.15 / ANTIC E (MicroPainter) | 160×192 | global | 4 of 128 | `.mic` |
| Atari 800 | GR.8 | 320×192 | global | 2 user-picked (mono) | `.gr8` |
| Atari 800 | GR.9 | 80×192 | per-pixel | 16 luma shades of one hue | `.gr9` |
| QL | Mode 8 / Low res | 256×256 | per-pixel | 8 | `_scr` |
| QL | Mode 4 / Hi-res | 512×256 | per-pixel | 4 fixed (blk/red/grn/wht) | `_scr` |

Each mode's palette and attribute constraints are honored natively — C64 modes use the Pepto/Colodore palette, QL Mode 4 is locked to its 4 hardwired colors, Atari GR.15 picks 4 global colors from 128 via frequency-quantize, etc.

## Features

- **Interactive cropping** — drag to select any region of the source image, with optional 4:3 aspect lock. The source pane shows the full image with the crop rectangle overlaid; corners are resizable.
- **10 dithering algorithms**:
  - Floyd-Steinberg / Atkinson / Stucki / Jarvis-Judice-Ninke / Burkes / Sierra Lite (error diffusion)
  - Ordered (Bayer 4×4) / Blue noise (interleaved gradient noise) / Yliluoma (palette-aware) / Halftone (clustered-dot)
- **Color search strategies**:
  - **Exhaustive per-block** — try all N-combinations of palette colors per block (ZX, TS 2068 ECM, C64)
  - **Global pre-quantize** — frequency-based for modes where exhaustive is infeasible (Atari GR.15 picks 4 of 128)
  - **Pixel-direct** — 1×1 blocks with no search; just dither each pixel to the full palette (QL, Atari GR.9)
  - **User-picked** — monochrome modes with user-chosen ink/paper (TS 2068 64-col, Atari GR.8)
- **Global error diffusion** — error-diffusion dithers propagate across block boundaries (critical for ECM's 8×1 strips and QL's per-pixel modes)
- **Live preview** with side-by-side source and converted views, nearest-neighbor scaling, correct pixel aspect ratio per mode
- **Adjustments** — brightness, contrast, saturation
- **Attribute grid overlay** — visualize color-clash boundaries
- **Image export** — PNG/JPG at 1×, 2×, 4× with proper pixel aspect correction and sharp edges

## Pixel aspect ratios

The app tracks pixel aspect ratio (PAR = width/height) per mode and applies the correct stretch when rendering previews and PNG/JPG exports, so output looks physically correct on a modern square-pixel display:

| Mode | PAR | Example render |
|---|---|---|
| ZX Spectrum / ECM / C64 Hi-res | ~1.0 | square pixels |
| TS 2068 64-col hi-res | 0.5 | pixels 2× taller than wide |
| C64 Multicolor | 1.87 | fat pixels (2× wider) |
| Atari GR.15 | 2.0 | fat pixels (PAL) |
| Atari GR.8 | 1.0 | square |
| Atari GR.9 | 4.0 | very wide pixels |
| QL Mode 8 | 1.47 | slightly wide pixels |
| QL Mode 4 | 0.74 | slightly tall pixels |

## Binary formats

The "Download binary" button emits the native format for each mode:

- **ZX Spectrum SCREEN$** (`.scr`) — 6912 bytes, interleaved screen memory + 768 byte attribute file
- **TS 2068 ECM** (`.scr`) — 12288 bytes (pixels at 0x4000 + attributes at 0x6000, same interleaved layout)
- **TS 2068 64-col** (`.scr`) — 12288 bytes (DF1 even columns + DF2 odd columns)
- **C64 Hi-res PRG** (`.prg`) — 2-byte load addr + 8000 byte bitmap + 1000 byte screen RAM (fg/bg nibbles)
- **C64 Koala** (`.kla`) — 10003 bytes: 2-byte load addr + 8000 byte bitmap + 1000 screen RAM + 1000 color RAM + 1 byte background
- **Atari MicroPainter** (`.mic`) — 7684 bytes: 7680 byte bitmap + 4 color register values
- **Atari GR.8** (`.gr8`) — 7680 bytes, 1 bit/pixel, MSB-first
- **Atari GR.9** (`.gr9`) — 7680 bytes, 4 bits/pixel (16 luma levels)
- **QL Mode 4 / Mode 8** (`_scr`) — 32768 bytes, 128 bytes/line, bitplane-packed per QL screen memory layout

ZX/Timex modes additionally support `.tap` (tape image) export with correctly-addressed CODE blocks, ready to load in an emulator like Fuse.

## How the ZX Spectrum block dithering works

The ZX Spectrum has only 2 colors (ink + paper) per 8×8 attribute block, drawn from a 16-color palette (8 hues × 2 brightness levels). On a TS 2068, BRIGHT 1 INK 0 is a distinct dark gray (~#606060), giving 16 usable colors. This creates the classic "color clash" effect.

For each attribute block, the converter finds the optimal color combination by dithering the block with each candidate pair and measuring total perceptual error (weighted RGB distance: `3·dR² + 4·dG² + 2·dB²`, matching BT.601 luma contributions). The chosen attributes and pixel pattern are then written to a Spectrum-layout screen buffer using the correct interleaved memory addressing:

```
addr = ((y & 0xC0) << 5) | ((y & 0x07) << 8) | ((y & 0x38) << 2) | (x >> 3)
```

### Timex 2068 advanced modes

Per the TS 2068 Technical Manual section 5.2, set via Port 0xFF:

- **Extended Color Mode (ECM, port=2)** enables 8×1 attribute blocks — 24× finer vertical color resolution. Pixel data at 0x4000 (same layout as standard Spectrum), attribute data at 0x6000 (same interleaved layout, one attribute per pixel byte). Dramatically reduces color clash and is ideal for photo conversion.

- **64-column mode (port=6|(ink<<3))** is 512×192 monochrome. Even character columns (0,2,4...62) come from DF1 at 0x4000, odd columns (1,3,5...63) come from DF2 at 0x6000. Single global ink/paper via port bits 3-5, BRIGHT and FLASH fixed at 0.

### Loading on real hardware or emulators

ZX/Timex: the `.tap` export includes CODE blocks at the correct addresses. For ECM/64-col modes, set the video mode first (`OUT 255, 2` for ECM, `OUT 255, 6+(ink<<3)` for 64-col) before loading.

C64: the `.prg` / `.kla` files load at the standard bitmap area ($2000) and screen RAM ($4000 area); use Koala Painter or a simple viewer.

Atari 800: `.mic` loads in MicroPainter or modern viewer tools; `.gr8` / `.gr9` are raw bitmaps (load at the proper display memory address, e.g. via a short BASIC loader).

QL: the `_scr` file is a direct dump of screen RAM (base $20000), loadable by standard QL emulators (QPC2, SMSQ/E, uQLx, QLAY) using `LBYTES scr_name,131072` or equivalent.

## Running locally

Single self-contained HTML file with no dependencies. Open `index.html` in a browser, or serve it with any static file server:

```bash
python3 -m http.server 8000
# then visit http://localhost:8000
```

## Credits and references

- **ZX Spectrum / TS 2068**: Sinclair / Timex original hardware manuals (TS 2068 Technical Manual §5.2)
- **C64 Pepto palette**: Philip "Pepto" Timmermann — pepto.de/projects/colorvic, colodore.com
- **Atari palette**: computed NTSC palette approximating Altirra / Olivier references
- **QL screen layout**: RWAP Software QL Technical Guide, Dilwyn Jones QL pages
- **Dithering kernels**: classic Floyd-Steinberg (1976), Atkinson (1984), Stucki (1981), Jarvis-Judice-Ninke (1976), Sierra, Burkes
- **Yliluoma algorithm**: Joel Yliluoma's color mixing article

## License

GPL v3 — see [LICENSE](LICENSE).
