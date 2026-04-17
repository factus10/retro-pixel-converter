# Spectrum Image Maker

A browser-based image converter that turns JPG/PNG images into ZX Spectrum SCREEN$ format, with export to `.scr`, `.tap`, and scaled PNG/JPG.

**[Try it live →](https://factus10.github.io/spectrum-image-maker/)**

## Features

- **Three display modes** covering standard ZX Spectrum + the TS 2068's advanced video modes:
  - **Standard Spectrum** — 256×192, 8×8 attribute blocks (6912 bytes)
  - **Timex Extended Color Mode (ECM)** — 256×192, **8×1** attribute blocks; each horizontal strip gets its own ink/paper/bright (12288 bytes). Port 0xFF = 2
  - **Timex 64-column hi-res** — **512×192 monochrome**, global ink + paper (12288 bytes). Port 0xFF = 6 | (ink << 3)
- **Interactive cropping** — drag to select any region of the source image, with optional 4:3 aspect lock
- **10 dithering algorithms**:
  - Floyd-Steinberg
  - Atkinson
  - Stucki
  - Jarvis-Judice-Ninke
  - Burkes
  - Sierra Lite
  - Ordered (Bayer 4×4)
  - Blue noise (interleaved gradient noise)
  - Yliluoma (palette-aware, projects onto the ink↔paper line)
  - Halftone (clustered-dot)
- **Two color strategies**:
  - Per-block best-fit — exhaustive search across all 128 ink/paper/bright combinations per 8×8 attribute block
  - Global pre-quantize — faster approximation using the dominant colors in each block
- **Live preview** with side-by-side source and converted views
- **Adjustments** for brightness, contrast, and saturation
- **Attribute grid overlay** to visualize the Spectrum's 8×8 color-clash boundaries
- **Spectrum palette** reference strip
- **Exports**:
  - `.SCR` — raw screen binary (6912 bytes standard, 12288 bytes ECM/hi-res)
  - `.TAP` — tape file with the correct number of CODE blocks for the selected mode:
    - Standard: 1 block loaded at 0x4000
    - ECM: 2 blocks — pixels at 0x4000, attributes at 0x6000
    - 64-col hi-res: 2 blocks — DF1 at 0x4000, DF2 at 0x6000
  - PNG and JPG at 1×, 2×, or 4× scale, with preserved sharp pixels

## How it works

The ZX Spectrum has a famously constrained display: 256×192 pixels with only 2 colors (ink + paper) per 8×8 attribute block, drawn from a 16-color palette (8 hues × 2 brightness levels). On a TS 2068, BRIGHT 1 INK 0 is a distinct dark gray (~#606060) rather than pure black, giving 16 usable colors instead of 15; on an original ZX Spectrum, bright black displays as black. This creates the classic "color clash" effect.

For each attribute block, Spectrum Image Maker finds the optimal ink/paper/bright combination by dithering the block with each candidate pair and measuring total perceptual error (weighted RGB distance, with green weighted highest to match human vision). The chosen attributes and dithered pixel pattern are then written to a Spectrum-layout screen buffer using the correct interleaved memory addressing:

```
addr = ((y & 0xC0) << 5) | ((y & 0x07) << 8) | ((y & 0x38) << 2) | (x >> 3)
```

### Timex/Sinclair 2068 advanced modes

The TS 2068 adds two additional video modes (set via Port 0xFF) that the app supports:

- **Extended Color Mode (ECM)** enables 8×1 attribute blocks instead of 8×8 — 24× finer vertical color resolution. Pixel data lives at 0x4000 (same interleaved layout as standard Spectrum, 6144 bytes), and attribute data lives at 0x6000 (same interleaved layout, 6144 bytes, one attribute byte per pixel byte — 32×192 = 6144 attribute bytes covering every 8×1 horizontal strip). This mode dramatically reduces color clash and is ideal for photograph conversion.

- **64-column mode** is a 512×192 monochrome mode. Even character columns (0,2,4...62) come from DF1 at 0x4000, odd columns (1,3,5...63) come from DF2 at 0x6000. A single global ink/paper is set via Port 0xFF bits 3-5. BRIGHT and FLASH are fixed at 0, border matches paper. Good for line art, dithered photos, or high-detail monochrome.

The `.TAP` export produces the correct number of CODE blocks for each mode, all loading at their proper addresses. Before loading an ECM or 64-col TAP on real hardware or an emulator, set the video mode first (e.g. `OUT 255, 2` for ECM, or `OUT 255, 6+(ink<<3)` for 64-col).

## Running locally

It's a single self-contained HTML file with no dependencies. Just open `index.html` in a browser, or serve it with any static file server:

```bash
python3 -m http.server 8000
# then visit http://localhost:8000
```

## License

GPL v3 — see [LICENSE](LICENSE).
