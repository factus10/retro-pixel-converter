# ULAVIEW for TS2068 + PicoVideo

For a separate viewer that preloads images into stock TS-Pico expansion SRAM, see [RAMVIEW](ramview/README.md). It keeps image-file loading out of playback and permits direct wipes only for compatible palette/attribute maps.

Image TAPs contain data only by default: named CODE files **ula-pal**, **ula-df1**, and, when needed, **ula-df2**. The reader owns all display code and palette/mode programming. These are files inside one host TAP, not three separate SD-card files.

DF means display file (screen-memory area). In ECM, DF1 is the bitmap and DF2 its 8x1 attributes. In hi-res they hold alternating pixel groups. Mode 7 has pixels and attributes in both. Quad color puts the first four pixels of each eight-pixel group in DF1 and the next four in DF2. Standard ULA+ needs only DF1, including its 8x8 attributes.

## Converter options

- **Download .TAP** saves the palette/mode and screen CODE files in palette-first order, with no executable code.
- **Include ULAVIEW program in .TAP**, unchecked by default, prepends a single-image BASIC viewer with autostart line 10 and a direct-loading `ula-code` file. LOAD "" loads BASIC; it autostarts and loads the machine code, palette and image from the same tape, without a BASIC hex installer.
- **Download ula-pal.bin** saves the 80-byte palette/mode file alone. It is already included in every image TAP, so another palette file on the SD card is unnecessary.
- Palette JSON remains an optional editing/reuse format; the TS2068 reader does not load JSON.

The earlier experimental single-block ula-image format and video-init image TAPs are superseded. Regenerate those TAPs, or package their raw converter exports with pack_image.py.

## Reader files and loading

- **ulaview.tap**: reusable single-image reader without autostart. LOAD "", select/mount an image tape, then RUN. Select another image and RUN again without reloading the reader.
- **ecmview.tap**: the same reader preset for earlier standard ECM tapes containing `ecm-atr` and `ecm-pix`, with native Timex colors and the same wipes/cleanup. No palette file or conversion is required. In ulaview.bas, line 75 selects `EC=0` for ULA files or `EC=1` for old ECM files.
- **ulavpico.tap**: reusable TS-Pico slideshow reader; its DATA list names data-only image TAPs.
- **ulaview-auto.tap**: autostart reader used by the bundling option.
- **ulademo.tap**: data-only ULA+ ECM demonstration.
- **ulademo-viewer.tap**: the same image with the autostart reader prepended.
- **tspico-slideshow.zip**: an ulapics directory with the slideshow and data-only demo, ready to extract to an SD card.

The supported modes are ULA+ standard, Timex ULA+ ECM, ULA+ hi-res, PicoVideo mode 7 with or without ULA+, and PicoVideo quad color. Mode 5 character/font conversion is not included.

Earlier standard Timex ECM images are supported too. For a single image, load `ecmview.tap`, mount the old image TAP, and RUN. The reader stages `ecm-atr` and `ecm-pix` off-screen, then constructs native ECM metadata in RAM. Existing files are not modified. Attributes-first tapes work directly; TS-Pico's named-file search also handles the earlier pixel-first tapes. With a physical sequential tape, put attributes first, as with the original ECMVIEW workflow.

The viewer displays for ten seconds or until a key is pressed. Line 70 sets T: 0 waits for a key. On exit, BREAK or loading error, it blanks the palette, clears attributes before pixels, disables ULA+, clears the mode override, and calls the Timex ROM normal-display service. After the routines are installed, RANDOMIZE USR 39942 is the resident restore entry if BASIC's handler has been bypassed. It restores ordinary Timex colors rather than preserving a previously loaded custom palette.

## Wipes and blanking

ECMVIEW's four reveal patterns are available for ECM, standard ULA+, and mode 7: left-to-right, right-to-left, center curtain, and blinds. Both reader variants default to random wipes. Line 74 sets `RW`, `W`, and `WS`: `RW=1` chooses a random wipe per picture; `RW=0` uses fixed `W` (0 instant, 1 left, 2 right, 3 curtain, 4 blinds). `WS` is a delay from 0 (fastest) to 255 (slowest), default 2. For example, `74 LET RW=0: LET W=3: LET WS=2: POKE 39949,WS` selects the curtain. The resident controls are WIPE_MODE at 39948 and WIPE_SPEED at 39949.

Blanking first programs a black palette without exposing the old screen through native colors. It clears ECM and 8x8 attribute areas before the bitmap. Before a wipe, the viewer finds an existing black INK or PAPER slot in the incoming palette and fills the hidden screen to select that slot. It then copies matching attributes and pixels one column at a time, preserving the image's palette. A black INK slot works too, including the older images with black only in register 0. Mode 7 uses 64 logical columns; standard and ECM use 32. Native mode 7 can use its fixed black color. Native hi-res, quad color, and custom palettes with no black entry use instant reveal.

Both normal exit and the first error-handler statement execute ON ERR RESET before cleanup. This is required because TS2068 BASIC traps STOP as an error too; leaving the handler active would repeatedly re-enter it. Cleanup also resets FLASH, BRIGHT, INVERSE and OVER before clearing the screen.

## TS-Pico slideshow directory

Keep one slideshow program and multiple data-only image TAPs:

```text
ulapics/
  ulavpico.tap
  ulademo.tap
  portrait.tap
  landscape.tap
```

Mount and load it using ECMVIEW's TS-Pico convention:

```basic
SAVE "tpi:cd ulapics"
LOAD "tpi:ulavpico.tap"
LOAD ""
RUN
```

Edit line 9510 to name your pictures, ending with "*":

```basic
9510 DATA "ulademo.tap","portrait.tap","landscape.tap","*"
```

The supplied list contains only ulademo.tap and the terminator. Line 70 sets T (seconds) and LP: the default is 1, repeating continuously; 0 runs once. SHIFT-BREAK uses the error handler to disable the trap, blank safely, restore native video mode, and clear to black text on a white screen with a white border before stopping in BASIC. FLASH, BRIGHT, INVERSE and OVER are reset. The single-image diagnostic stays one pass. Leave **Include ULAVIEW program** unchecked for each slideshow image. When rebuilding, edit ulavpico.bas.in; generated .bas listings are overwritten.

For mixed slideshows, prefix old ECM entries with `ecm:` (uppercase `ECM:` also works):

```basic
9510 DATA "uferrari.tap","ecm:ferrari.tap","upainthi.tap","*"
```

The prefix is a reader instruction, not part of the disk filename. It is stripped before the `tpi:` mount command, so keep the actual files named `ferrari.tap`, etc., with 8.3 names. Unprefixed entries use `ula-pal`/`ula-df1`/`ula-df2`; prefixed entries use `ecm-atr`/`ecm-pix`. Explicit selection avoids searching indefinitely for a palette file that is absent from an old tape. Wipes, looping, display time and BREAK cleanup apply to both formats.

## ula-pal file format, version 2

ula-pal is exactly **80 bytes**: 16 metadata bytes and 64 hardware palette slots. It contains no instructions. The raw ula-pal.bin download has the same bytes as the named CODE file in the TAP.

| Offset | Bytes | Meaning |
|---:|---:|---|
| 0 | 4 | ASCII ULAV |
| 4 | 1 | Version 2 |
| 5 | 1 | Port FF video mode: 0, 2, 6, 7 or 3 |
| 6 | 1 | Palette kind: 1 ULA+, 2 quad table, 0 native |
| 7 | 1 | Border index 0-7 |
| 8 | 2 | DF1 byte count, little endian |
| 10 | 2 | DF2 byte count, little endian; zero means absent |
| 12 | 1 | Used palette slots: 64, 4 or 0 |
| 13 | 1 | Reserved, must be zero |
| 14 | 2 | Sum of all 64 palette slots plus every DF1 and DF2 byte, modulo 65536; little endian |
| 16 | 64 | GGGRRRBB hardware bytes in register order; unused slots zero |

ULA+ colors use green bits 7-5, red bits 4-2, blue bits 1-0. Red and green have eight levels. Blue 00/01/10/11 expands to three-bit 000/011/101/111. The 64 registers form four banks of 16, each with eight INK and eight PAPER entries. Attribute bits 7-6 choose the bank, bits 2-0 choose INK, and bits 5-3 choose PAPER. Quad mode uses the first four bytes as a direct GRB table. Native mode 7 has no custom colors.

The checksum ties ula-pal to its matching screen files. To reuse colors in another conversion, import their JSON palette and export fresh matching files. The border selects bank-0 PAPER entries 8-15 with ULA+; hi-res follows its hardware PAPER color.

RPC defaults to **Black** in its ULA+ / PicoVideo border selector. ULA+ conversion reserves register 8 as black before fitting blocks, and exports border index 0. This applies to automatic and custom palettes. Hi-res instead reserves register 15 (its PAPER), using the brighter of the selected pair as INK; its border and PAPER cannot differ. Choose **Use palette color from border picker** to preserve the custom palette entries and allow a colored border. The choice is saved in conversion profiles. Native mode 7 and quad color use ordinary border index 0 for black. The viewer needs no extra code or format flag: the image's palette and border index fully describe the choice.

Grayscale and single-channel shading require no extra mode flag: their hardware color values are carried in the palette.

Only these mode combinations are valid:

| Mode | Port | Kind | DF1 bytes | DF2 bytes | Palette slots |
|---|---:|---:|---:|---:|---:|
| ULA+ standard | 0 | 1 | 6912 | 0 | 64 |
| ULA+ ECM | 2 | 1 | 6144 | 6144 | 64 |
| ULA+ hi-res | 6 | 1 | 6144 | 6144 | 64 |
| ULA+ mode 7 | 7 | 1 | 6912 | 6912 | 64 |
| Native mode 7 | 7 | 0 | 6912 | 6912 | 0 |
| Quad color | 3 | 2 | 6144 | 6144 | 4 |
| Native ECM | 2 | 0 | 6144 | 6144 | 0 |

## TAP order and memory

| Tape filename | Staging address | Size |
|---|---|---|
| ula-pal | $A000 (40960) | 80 bytes |
| ula-df1 | $A050 (41040) | DF1 length from metadata |
| ula-df2 | $A050 + DF1 length | DF2 length; omitted if zero |

Each is an ordinary CODE header/data pair. For ECM the ranges are $A000-$A04F, $A050-$B84F and $B850-$D04F. The data-only ECM TAP is **12,443 bytes**, including TAP framing and three CODE headers. The reader copies the screens to $4000 and $6000 only after all data is loaded and verified. Bitmap/attribute layouts match the converter's raw hardware exports.

The optional bundled tape prepends one BASIC file named ulaview, autostart line 10. Its following image files are byte-identical to the data-only image. There is no per-image video-init routine.

BASIC reserves memory with CLEAR 39935. Resident code starts at $9C00; entry jumps are prepare (39936), show (39939), restore (39942), and metadata validation (39945). Staged data ends by $D64F. $E000-$FFFF is left unused, following ECMVIEW's TS-Pico transfer-workspace margin. The Timex ROM service reserves both screen files and moves BASIC before loading. An all-black palette hides loading text. Palette-first staging needs no attributes-first option.

After staging the old pixel/attribute files at $A050/$B850, `USR 39954` constructs native ECM metadata at $A000, with a checksum covering both screen files. This metadata exists only in RAM; old ECM TAPs do not need an added ula-pal file.

PicoVideo register 65 receives an explicit override ($80 for mode 0, otherwise 2/3/6/7). For ULA+ images the physical Timex port FF stays in native ECM mode 2, matching the ROM's reserved display layout; register 65 selects the PicoVideo output independently. In particular, ULA+ mode 7 is not written as a native Timex mode. The metadata still records the requested PicoVideo mode. Native-palette mode 7 and quad mode require their native port values because the PicoVideo override applies only while ULA+ is enabled. Exit disables ULA+ and clears the override before restoring the ROM's normal video mode.

## Package existing raw exports

```shell
python viewer/pack_image.py picture.scr --mode ula-ecm -o picture.tap
python viewer/pack_image.py picture.scr --mode ula-ecm --bundle-viewer -o standalone.tap
```

Input must be a converter raw screen export with its palette trailer, not a PNG/JPG or old image TAP. Choose the correct mode from pack_image.py.

## Build and verify

Prebuilt TAPs are ready to copy. Rebuilding requires Pasmo and zmakebas:

```shell
python viewer/build.py --pasmo /path/to/pasmo --zmakebas /path/to/zmakebas
python viewer/make_demo.py
```

The bundled viewer uses a small BASIC loader followed by a 1001-byte `ula-code` CODE file at `$9C00`, then the palette and image files. It loads machine code directly rather than decoding hex in BASIC. Reload the complete bundled TAP to show it again. Separate reusable readers retain their hex-string installer so they can be loaded first and RUN after another image TAP is mounted. It emits the genuine Timex ON ERR/RESET tokens and updates the converter's inline autostart reader. Keeping it inline makes bundling work when index.html is opened directly from disk. make_demo.py generates both demo tapes and the SD-card ZIP.

```shell
node tests/video-modes.cjs
python -m pip install --target viewer/.build/deps skoolkit
python viewer/test_viewer.py
```

Tests cover all six display layouts, JavaScript/Python format agreement, named-file loads and staging, optional bundling, assembled Z80 palette/mode/display code, corrupted-image rejection and TAP/BASIC structure. Browser tests exercise data-only and bundled exports and the palette download. The Timex ROM service is stubbed and its banking sequence checked. The full TS2068 ROM and TS-Pico firmware are not emulated; Jon has confirmed SD slideshow playback on a real TS2068/PicoVideo setup. This is not exhaustive hardware validation of every layout, transition or error path.

References: Jon Becker's local ECMVIEW release, and [PicoVideo firmware/documentation](https://github.com/timex-sinclair-projects/PicoVideo).

### Missing display hardware

ULA+ and PicoVideo images check selector readback at `$BF3B` using two values, plus a nonzero/non-`$FF` version response from register `$7F`. The check restores the previous selector and never writes palette data. If the check fails, the viewer restores a usable native BASIC screen, displays `ULA+ not present (PicoVideo required)` over two lines, and stops with error trapping disabled. Legacy native ECM images bypass the check. This targets PicoVideo readback; it is not a guarantee that unrelated ULA+ implementations or every firmware revision implement the required display modes.
