# Retro Pixel Converter

A dependency-free browser image converter for classic 8-bit and 16-bit machines. It converts JPG, PNG, GIF, and WebP images into native graphics formats for the ZX81, ZX Spectrum, Timex/Sinclair 2068, Commodore 64, Atari 800, Sinclair QL, SAM Coupé, and Pico-8.

**[Try it live ->](https://factus10.github.io/retro-pixel-converter/)**

## Supported Display Modes

| Machine | Mode | Pixels | Attribute / block size | Colors | Visible border | File |
|---|---:|---:|---:|---|---|---|
| ZX Spectrum | Standard | 256x192 | 8x8 | 2 of 16, ZX bright-black behavior | 32/32/24/24 | `.scr` / `.tap` |
| ZX81 | Character graphics | 256x192 | 8x8 character cells | 64 glyphs + inverse video | 32/32/24/24 | `.zx8` |
| TS 2068 | Standard | 256x192 | 8x8 | 2 of 16, Timex bright black is dark gray | 32/32/24/24 | `.scr` / `.tap` |
| TS 2068 | Extended Color Mode | 256x192 | 8x1 | 2 of 16 per strip | 32/32/24/24 | `.scr` / `.tap` |
| TS 2068 | 64-column hi-res | 512x192 | global | 8 hardware ink/paper pairs | 64/64/24/24 | `.scr` / `.tap` |
| ZX Spectrum / TS 2068 | Mono | 256x192 | global | 2 of 8 user-picked ink/paper, no bright | 32/32/24/24 | `.scr` / `.tap` |
| C64 | Hi-res bitmap NTSC/PAL | 320x200 | 8x8 | 2 of 16 | mode-specific | `.prg` |
| C64 | Multicolor / Koala NTSC/PAL | 160x200 | 4x8 | 1 auto-picked global background + 3 of 16 per block (4 total) | mode-specific | `.kla` |
| Atari 800 | GR.15 / ANTIC E | 160x192 | global | 4 of 128 | 8/8/24/24 | `.mic` |
| Atari 800 | GR.8 | 320x192 | global | 2 user-picked hue/luma colors | 16/16/24/24 | `.gr8` |
| Atari 800 | GR.9 | 80x192 | per-pixel | 16 luma shades of one hue | 4/4/24/24 | `.gr9` |
| QL | Mode 8 / Low res | 256x256 | per-pixel | 8 | none | `_scr` |
| QL | Mode 4 / Hi-res | 512x256 | per-pixel | 4 fixed colors | none | `_scr` |
| SAM Coupé | Mode 1 | 256x192 | 8x8 | 2 per cell of a 16-color CLUT (chosen from 128) | 32/32/24/24 | `.ss1` |
| SAM Coupé | Mode 2 | 256x192 | 8x1 | 2 per cell of a 16-color CLUT (chosen from 128) | 32/32/24/24 | `.ss2` |
| SAM Coupé | Mode 3 | 512x192 | global | 4 of 128 | 64/64/24/24 | `.ss3` |
| SAM Coupé | Mode 4 | 256x192 | global | 16 of 128 | 32/32/24/24 | `.ss4` |
| Pico-8 | Standard palette | 128x128 | per-pixel | 16 fixed | 4:3 side border | `.bin` + optional hex `.txt` |

Visible borders are listed as left/right/top/bottom in mode pixels. Border color palettes are mode-aware: ZX81 uses a fixed white border, ZX Spectrum and most Timex modes use the 8 basic non-bright colors, TS 2068 hi-res follows the selected paper color, C64 modes use the active C64 palette, and modes without known border color control default to black.

Custom modes can also be imported from JSON at runtime. PNG/JPG export works for custom modes; binary export requires mode-specific exporter code.

## Rendering And Color Pipeline

- Images are loaded and processed in linear-light color space. Source adjustment, resampling, preview rendering, output visualization, and linear-to-sRGB display conversion are handled through WebGL2 where appropriate.
- Transparent source pixels keep their RGB values; alpha is ignored instead of compositing the image over black before conversion.
- Dithering and quantization operate on linear pixels, then final converted pixels are resolved back to sRGB for display and export.
- Output geometry is derived from each mode's addressable pixel area plus visible border, then mapped to a 4:3 display. Pixel aspect is calculated from that full visible frame rather than stored as a separate mode constant.
- The output starts with a 320x240 TV test pattern so scale, border, and CRT sizing are visible before an image is loaded.
- After conversion, the status bar reports total wall-clock time plus a compact stage breakdown for mapping, preparation, quantization, output application, and final display output.
- A modern browser with WebGL2 support is required. There is no build step and no runtime dependency download.

## Workflow Features

- Drag-and-drop or browse for an image, then crop interactively in the input panel.
- Leave `Autodetect` enabled to classify the source as grayscale, line art, or a photo and apply mode-aware dithering and color-search recommendations. Manual changes to either recommended control are respected; the toggle is enabled by default and its state persists locally.
- Resize the input/output split manually with the center divider.
- Lock crop aspect ratio, stretch the selected crop to the target resolution, or turn Stretch off and fill side bars with the configured RGB crop fill color. Filled bars are part of the target image and can be dithered like any other pixels.
- Use brightness, contrast, saturation, gamma, dithering, palette, and search controls to tune the conversion. Input brightness uses a signed-quadratic response for fine adjustment near the neutral value of 50 while retaining the full effect at 0 and 100.
- Reset any input-image adjustment to its default with the icon beside its slider.
- Inspect available colors with the mode-aware palette strip and disable individual colors for palette-search modes when needed.
- For Atari GR.8, choose foreground/background Atari hues and luma values directly; the palette strip is hidden because conversion uses those two selected colors.
- Show an attribute grid overlay for block-based modes.
- Snapshot the current output and switch the output panel between `Active` and `Saved` using the header radio toggle. The saved snapshot reuses the normal output canvas, CRT, border, scale, grid, and fullscreen paths.
- Export/import conversion profiles containing the selected mode, conversion controls, crop state, disabled colors, crop fill color, CRT settings, and border selection. App-level UI preferences such as `Autodetect` and ECM `.TAP` block ordering are not part of a profile.

## CRT, Borders, And Output Display

The output panel uses a `Scale` control, mode-specific pre-scaling where required, and a shader-based CRT simulation. CRT controls include scanlines, brightness, contrast, saturation, RF noise, horizontal bleed, bloom, bloom spread/threshold, and vignette. Range controls are live: a value of `0` disables effects such as noise, bleed, bloom, and vignette.

The border selector is available in the output header for modes with visible borders. The app starts with Scale `1.5` and a black border selected. Border selection persists when switching through borderless modes such as QL.

The input-panel fullscreen button shows the current adjusted and cropped source image. Fullscreen output renders the selected `Active` or `Saved` image with devicePixelRatio-aware backing resolution. The decorative CRT frame is not shown in fullscreen, but any enabled border remains because it is rendered inside the output canvas.

## Dithering And Color Search

Dithering options include Floyd-Steinberg, Atkinson, Stucki, Jarvis-Judice-Ninke, Burkes, Sierra Lite, Sierra Line, Dizzy, Hilbert diffusion, Hilbert Riemersma, Adaptive Riemersma, Blue noise, Bayer 4x4, even-lines-first and odd-lines-first Bayer 4x4, Bayer 8x8, halftone, and no dither. The line-first Bayer variants preserve Bayer's relative ordering within each scanline parity, but assign threshold ranks 0-7 to even lines and 8-15 to odd lines, or the complementary odd-first ordering. At 50% coverage this fills one line parity completely before the other. Sierra Line sends error only to the next row with symmetric 1/4, 2/4, 1/4 weights, using 2/4, 2/4 at the left and right edges; pixel order within a row and serpentine scanning therefore do not affect it. Interlaced processing is an application strategy rather than a separate dither method. In direct-pixel modes, an `Interlaced` switch is available for scanline error-diffusion and threshold dithers and uses an even-then-odd flow. Its threshold path spreads each even row's actual quantization error into the odd rows immediately above and below with a symmetric Sierra Line fan. Each adjacent row receives half the fan when both exist, or the full fan at the top and bottom edges, so the total distributed error remains one. Odd rows are rendered after all even rows and do not propagate error further. Attribute modes provide separately selectable even-first and odd-first strategies as described below. Dizzy uses a deterministic shuffled pixel order per resolution and spreads error to unvisited adjacent neighbors with lower diagonal weight. Hilbert Riemersma follows a Hilbert curve and adds a 16-entry exponentially weighted recent-error history before quantization. Adaptive Riemersma builds an image-dependent space-filling curve by merging 2x2 pixel loops by color-distance delta, then uses the same recent-error history. Blue noise uses a generated 64x64 toroidal rank map with seamless wrapped edges, avoiding the hard tile boundaries of independently shifted tiles. Two-color ordered and threshold dithers project pixels onto the selected color segment in linear RGB before thresholding. This is the Yliluoma-like part of the old ordered workflow, so a separate Yliluoma option would only duplicate Bayer 4x4 with the same two-color projection.

Color search strategies are mode-aware:

- **Best segment coverage** is the default for two-color attribute modes such as ZX/Timex and C64 hi-res. It scores candidate attribute pairs by projecting each original block pixel onto the ink-paper line segment in linear RGB and choosing the pair with the lowest coverage error.
- **Best simplex coverage** is the default for C64 multicolor modes. It scores each four-color candidate set by how well its linear RGB convex hull covers the original block.
- **Interlaced segment coverage (even first / odd first)** is available for 8x1 two-color attribute modes such as Timex ECM and SAM mode 2 with a scanline error-diffusion or threshold dither. The selected first parity chooses segment-fit attributes and renders while the other parity collects its error; the second parity then chooses attributes from its error-adjusted pixels and renders. Scanline diffusion preserves each dither's forward kernel, so first-parity error feeds following rows and two-row kernels such as Stucki and Jarvis-Judice-Ninke can also carry error within a parity. During the second phase, error aimed at finalized first-parity rows is discarded. Threshold dithers instead spread first-parity error symmetrically to available adjacent rows, and the second parity does not propagate error further.
- **Weighted average pair fit** scores candidate color pairs by how well a blend can match the block average; ZX/Timex attribute modes use linear RGB for this scoring to match their final pixel decisions.
- **Per-block best-fit** exhaustively evaluates palette combinations for block modes where that is practical.
- **Greedy global hull** is used for Atari GR.15 and SAM mode 3: it adds four global palette colors by reducing convex-hull coverage error, then runs a small swap refinement.
- **Greedy pair-segment coverage** is used for global palettes larger than four colors (SAM mode 4's 16 of 128), where per-sample hull coverage is impractical: each slot adds the color that most reduces the summed distance from every sample to its nearest single color or two-color mixing segment of the selection — the mixes two-color dithering actually renders — followed by swap refinement. With the perceptual-matching switch on, mix points stay in linear light but residuals are judged with first-order perceptual weights.
- **SAM CLUT** (SAM modes 1/2) first picks a 16-entry CLUT from the 128-color SAM palette with the pair-segment coverage selection, distributes it across the two 8-color halves by interleaving luma ranks so both halves span the full luma range (the attribute BRIGHT bit selects a half for both ink and paper, as on the hardware), then runs the regular ZX per-block attribute search over the halves, including the selectable ZX color strategies and Gauss-Seidel refinement.
- **Pixel-direct** is used for per-pixel modes such as QL and Atari GR.9.
- **User-picked** is used for hardware-constrained global-pair modes such as TS 2068 64-column, Atari GR.8, and Spectrum/Timex Mono. GR.8 exposes Atari hue selectors plus foreground/background luma sliders; the mono mode exposes individual ink and paper pickers limited to the 8 basic (non-bright) colors, e.g. for printable screens.
- **ZX81 character fit** converts the image to 32x24 fixed character cells and picks the closest normal or inverse-video glyph using multi-scale grayscale intensity matching. By default it matches directly in linear luma; the perceptual-matching switch applies the sRGB transfer to source luma before matching (the former `equalized` sub-mode).

Threshold-based dithers use linear RGB palette mixtures for multi-color palettes: the converter finds a small set of palette colors whose weighted average approximates the source color, then samples that mixture with the threshold matrix. `None` and error-propagation dithers use linear RGB nearest-color choices for multi-color palettes and ZX/Timex two-color attribute pixels, so color selection and propagated error are measured in the same space.

An optional perceptual-matching switch (under the color strategy selector) changes nearest-color *selection* for the `None` dither to a gamma-encoded weighted RGB metric: distances are measured on sRGB-encoded channels weighted by the BT.709 coefficients. The per-channel sRGB transfer undoes the dark-tone compression of linear distances while keeping hue behavior aligned with plain RGB expectations. Block searches and Gauss-Seidel refinement score candidates in the same metric so the search matches the rendering. In the ZX81 mode the same switch applies the sRGB transfer to source luma before glyph matching, and for SAM modes 1/2/4 it additionally weights the global palette-selection scoring perceptually (under any dither — selecting which colors exist is a judgment of real colors). Per-pixel matching stays linear elsewhere: error diffusion quantizes virtual accumulated values whose duty cycle is a linear-light quantity, so a perceptual metric there distorts color amounts badly on sparse palettes, and threshold dithers already match linear mixtures.

ZX/Timex exhaustive modes offer an optional Gauss-Seidel refinement pass that re-scores the worst dithered attribute blocks against the realized output and swaps in better ink/paper pairs, iterating with re-dithers until stable. It applies only to `None` and error-diffusion dithers, where diffused error couples neighboring blocks. Ordered/threshold dithers are per-pixel deterministic with no cross-block coupling, and their per-pixel error metric mis-ranks pattern-dithered blocks (favoring dark, low-contrast solid pairs), so the refinement is disabled and hidden for them.

## Display Geometry

The app displays each mode as part of a 4:3 visible screen, using border dimensions to derive the pixel aspect ratio:

| Mode | Full visible frame | Derived pixel aspect |
|---|---:|---:|
| ZX / TS standard / ECM | 320x240 | 1.000 |
| ZX81 | 320x240 | 1.000 |
| TS 2068 64-column | 640x240 | 0.500 |
| C64 hi-res NTSC | 418x235 | 0.750 |
| C64 multicolor NTSC | 209x235 | 1.499 |
| C64 hi-res PAL | 362x246 | 0.906 |
| C64 multicolor PAL | 181x246 | 1.812 |
| Atari GR.15 | 176x240 | 1.818 |
| Atari GR.8 | 352x240 | 0.909 |
| Atari GR.9 | 88x240 | 3.636 |
| QL Mode 8 | 256x256 | 1.333 |
| QL Mode 4 | 512x256 | 0.667 |
| SAM Mode 1 / 2 / 4 | 320x240 | 1.000 |
| SAM Mode 3 | 640x240 | 0.500 |
| Pico-8 | 170.667x128 | 1.000 |

Pico-8 also uses an output pre-scale of `2` before output effects, so CRT-style processing works on a larger image without changing the exported 128x128 pixel data.

## Export Formats

Image export produces sharp PNG/JPG files at 1x, 2x, or 4x with integer pixel replication approximating the active conversion's pixel aspect ratio. The selected scale is the replication count on the shorter pixel axis; the other axis uses the closest proportional integer count, capped at a 4:1 ratio. For example, 2:1 pixels export as 2x1, 4x2, and 8x4 blocks, while a 1.5:1 aspect exports as 2x1, 3x2, and 6x4 blocks. A 1:2 aspect similarly uses 1x2, 2x4, and 4x8 blocks. This keeps every converted pixel aligned to a uniform rectangle instead of rounding fractional output boundaries. PNG/JPG export reuses a WebGL2 export renderer instead of allocating a new context for each download. JPG encoding remains lossy even though its pre-encoding pixel geometry is exact. Binary export data is built lazily when a download is requested, so routine preview updates do not rebuild `.scr`, `.tap`, `.prg`, `.kla`, and other binary payloads.

| Format | Output |
|---|---|
| ZX81 character screen | `.zx8`, 768 character-code bytes |
| ZX Spectrum SCREEN$ | `.scr`, 6912 bytes |
| TS 2068 ECM | `.scr`, 12288 bytes |
| TS 2068 64-column | `.scr`, 12288 bytes |
| C64 hi-res bitmap | `.prg`, load address + bitmap + screen RAM |
| C64 Koala | `.kla`, load address + bitmap + screen RAM + color RAM + background |
| Atari MicroPainter | `.mic`, bitmap + 4 color register values |
| Atari GR.8 | `.gr8`, raw 1 bit/pixel bitmap |
| Atari GR.9 | `.gr9`, raw 4 bits/pixel luma bitmap |
| QL Mode 4 / Mode 8 | `_scr`, direct QL screen memory dump |
| SAM Coupé Mode 1 | `.ss1`, 6912 bytes screen + 41 bytes palette = 6953 bytes |
| SAM Coupé Mode 2 | `.ss2`, 14336 bytes screen (incl. 2K padding) + 41 bytes palette = 14377 bytes |
| SAM Coupé Mode 3 | `.ss3`, 24576 bytes screen + 41 bytes palette = 24617 bytes |
| SAM Coupé Mode 4 | `.ss4`, 24576 bytes screen + 41 bytes palette = 24617 bytes |
| Pico-8 | `.bin` and optional hex `.txt` |

ZX/Timex modes additionally support `.tap` tape-image export with correctly addressed CODE blocks. For ECM, the `Attributes first in .TAP` switch emits the separately addressed attribute block before the bitmap block, allowing ECMview to paint the image without temporary attribute artifacts while loading.

## Hardware Notes

ZX81: `.zx8` is a raw 32x24 row-major character-code screen using normal codes `0..63` and inverse-video codes `128..191`.

ZX/Timex: the `.tap` export includes CODE blocks at the correct addresses. ECM can optionally place its attribute block first for artifact-free painting in ECMview. For ECM/64-column modes, set the video mode first (`OUT 255,2` for ECM, `OUT 255,6+(ink<<3)` for 64-column) before loading.

C64: `.prg` and `.kla` files use standard bitmap/Koala-style layouts and can be loaded by compatible viewers or tools.

Atari 800: `.mic` loads in MicroPainter-compatible tools. `.gr8` and `.gr9` are raw display-memory images. GR.8 color choices affect preview and 1-bit conversion, but the raw `.gr8` payload contains only bitmap bits.

QL: `_scr` is a direct dump of screen RAM at base `$20000`, loadable in common QL emulators with commands such as `LBYTES file,131072`.

SAM Coupé: `.ss1`-`.ss4` are SAM SCREEN$ files (`LOAD "file" SCREEN$`, loadable in SimCoupe): the mode's screen memory as-is, followed by a 41-byte palette trailer — 16 CLUT bytes plus 4 mode-3 store bytes for each of the two flash phases (written identical here), then a `0xFF` terminator; no line-interrupt records are emitted. Palette bytes are 7-bit SAM colors (GRN1 RED1 BLU1 BRIGHT GRN0 RED0 BLU0; BRIGHT adds a half step to all guns). Mode 1 uses the Spectrum-interleaved bitmap layout; mode 2 is linear with attributes at offset 8192; both use Spectrum-style attribute bytes whose BRIGHT bit selects the CLUT half (note: some references describe mode 2 attributes as free paper/ink nibbles, but the SimCoupe reference emulator decodes them exactly like mode 1). Mode 3 pixel values 1 and 2 are fetched from CLUT entries 2 and 1 respectively, so the `.ss3` CLUT is written swap-adjusted while the mode-3 store bytes hold the colors in pixel-value order.

## Running Locally

Open `index.html` directly in a browser, or serve the repository with any static file server:

```bash
python3 -m http.server 8000
# then visit http://localhost:8000
```

There is no package install, bundler, build step, generated output, or server-side processing.

## Credits And References

Special thanks to **Josef Jelinek** for feedback and technical guidance, including palette and color-distance fixes, Timex bright-black behavior, TS 2068 64-column constraints, generalized mode configuration, CRT/output workflow, linear-space processing, and retro display geometry.

References:

- **ZX Spectrum / TS 2068**: Sinclair and Timex original hardware manuals, including TS 2068 Technical Manual section 5.2
- **C64 palette**: Philip "Pepto" Timmermann's Pepto / Colodore references
- **Atari palette**: NTSC-style approximation inspired by Altirra and related references
- **QL screen layout**: RWAP Software QL Technical Guide and Dilwyn Jones QL references
- **Dithering kernels**: Floyd-Steinberg, Atkinson, Stucki, Jarvis-Judice-Ninke, Sierra, Burkes
- **Hilbert curve**: David Hilbert's space-filling curve, applied here as an error-diffusion traversal
- **Blue noise**: deterministic generated rank map based on a best-void style placement pass

## License

GPL v3 - see [LICENSE](LICENSE).
