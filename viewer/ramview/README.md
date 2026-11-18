# RAMVIEW: TS-Pico SRAM slideshow

`ramview.tap` is a separate viewer that preloads the current nine-image list into **TS-Pico expansion SRAM**, then loops from RAM. The existing SD-loading viewer is unchanged. It uses the installed TS-Pico BASIC `MEMDOCK` interface, not replacement Pico firmware, Flash updates, or MEMBOOT changes.

## Run it

Copy `ramview.tap` into the SD-card directory containing the same nine images as the working slideshow:

```text
uferrari.tap   ueye.tap      uflowers.tap
uchamel.tap    uartemis.tap  umarble.tap
upaint.tap     upainthi.tap  ulandsc.tap
```

Keep the working short name `upainthi.tap`; all filenames must fit 8.3. Mount and load the viewer from that directory:

```basic
LOAD "tpi:ramview.tap"
LOAD ""
RUN
```

Startup loads three small CODE files from the same TAP, then displays `CODE READY`. There is no slow BASIC hex installer. Leave the TAP positioned immediately after loading BASIC and use RUN so the three following CODE files can be read before any image is mounted. After BREAK, remount/reload ramview.tap before restarting. Resident initialization briefly uses a cyan border and screen preparation a yellow border; preparation itself then blacks the palette and border.

Preloading then uses a native black-on-white status screen (ULA+ disabled during loading, with BASIC still reserving the ECM workspace) showing image number/total, overall percentage, filename and current step: mounting, palette/screen loading, image checking, SRAM region selection, or SRAM writing/readback verification. The percentage counts fully cached images rather than pretending to measure byte progress inside a ROM LOAD. A 100%/cache-ready message appears before playback starts. Status text is used only during preloading and never overlaid on playback images. SRAM is volatile: a restart/RUN preloads again; no persistent image cache is saved to the SD card.

SHIFT-BREAK uses the error handler to restore native video, clear to black text on white with a white border, disable the error trap, and stop in BASIC. During short interrupt-disabled copy/wipe routines, BREAK is handled when BASIC resumes. The diagnostic line reports the current image and stage if loading or verification fails.

**RAM ownership:** the supplied nine-image list uses even SRAM regions **0, 2 and 4**, reserving chunks 0-3 and 5-6 in each. Previous contents in those cache areas are replaced. This is a standalone application, not a cache to run alongside an active SRAM RAMDisk or another program's unsaved SRAM assets. It does not write the Flash/boot image. Exit leaves HOME mapped (`F4=0`); the last SRAM region remains selected for DOCK. Another cartridge/RAM application should select its own region before using DOCK. To select the usual Flash slot 0 manually, use `SAVE "tpi:memdock" CODE 2,0` after returning to BASIC.

## Transitions without color clash

RAMVIEW keeps the old picture visible while fetching the next cached frame within the same SRAM region. It permits a **direct picture-to-picture wipe only when all these match**:

- Display mode, palette kind, border and screen lengths.
- Every palette entry.
- Every attribute byte in the active screen file(s).

With matching attributes, both old and new pixels use the same two colors per block throughout the wipe. The direct path does not reprogram the palette or blank the screen. This is useful for animation frames or pictures authored with a shared palette and attribute map.

If the palette or attributes differ, the viewer uses the existing safe black-out and reveal instead. It blacks the palette before clearing attributes/pixels, then reveals the new image with its own colors. This avoids drawing old pixels under new attributes or changing the old picture's colors during a palette update. A mode change also uses this safe path. Hi-res and quad modes remain instant reveals.

Changing SRAM regions needs a `MEMDOCK` command through the Pico. That boundary uses a black screen before issuing the command, so ROM/Pico command messages cannot damage a visible picture. Direct wipes are therefore possible within a three-image region, not across region boundaries. Most independently optimized ULA+ photos have different palettes, so expect black reveals for those; a RAM cache cannot make incompatible palette changes visually safe.

## Controls

Edit the BASIC listing, or rebuild from `ramview.bas.in`:

| Line | Setting | Default |
|---:|---|---|
| 60 | `NI` number of images | 9; must match the DATA list |
| 60 | `T` seconds per image | 10; 0 waits for a key |
| 60 | `LP` repeat | 1; 0 runs once |
| 62 | `RW` random wipes | 1; 0 selects fixed `W` |
| 62 | `W` wipe | 0 instant, 1 left, 2 right, 3 curtain, 4 blinds |
| 62 | `WS` wipe delay | 2; 0 is fastest |
| 62 | `DP` allow compatible direct wipes | 1; 0 always blanks |

The build generates `NI` and the DATA list together. It compacts numeric constants as BASIC `VAL` strings to keep the status UI small. Unlike the SD viewer, this list contains exactly `NI` entries and no `"*"` terminator. Up to 24 slots are supported, subject to the BASIC listing-size guard. For old standard ECM TAPs, prefix an entry with `ecm:`; the reader strips it before mounting and loads `ecm-atr`/`ecm-pix` with native Timex colors. ULA+ entries use `ula-pal`/`ula-df1`/`ula-df2`. Use data-only image TAPs, not images with a bundled BASIC viewer.

### Direct-wipe demonstration

Extract `ramdemo.zip` to an SD-card directory and load `ramdemo.tap` there. It preloads `ramone.tap` and `ramtwo.tap`. These frames have the same palette and attributes but different bitmaps. The first image reveals from black; subsequent changes can wipe directly between the two without an intermediate black frame or a Pico command per transition. The demo owns region 0, chunks 0-3. Its hardware playback is also unverified.

## SRAM layout and performance boundary

Each cached record reserves a 16 KiB slot and stores 13,904 bytes: the maximum supported palette/mode header plus screen data. Shorter images are padded with ignored staging bytes. The original image checksum still covers only its meaningful data.

Within each even MEMDOCK region, the three records begin at CPU/DOCK addresses:

| Record within region | Start | Reserved windows |
|---:|---|---|
| 0 | `$0000` | chunks 0-1 |
| 1 | `$4000` | chunks 2-3 |
| 2 | `$A000` | chunks 5-6 |

Image indices 1-3 use region 0, 4-6 region 2, 7-9 region 4, and so on through region 14. Even slots identify eight independent 64 KiB regions on the stock V2.2 mapping; odd slots are not treated as extra banks. The unused DOCK chunks 4 and 7 are not image storage because those CPU chunks must keep the viewer and stack in HOME.

Low-window frames use direct `LDIR` copies to/from HOME staging. The high window overlaps that staging address, so its transfer alternates through a fixed HOME bounce buffer. Every store is read back and compared byte for byte. Every recalled image is validated before display. After each MEMDOCK selection the gateway performs eight read-only DOCK accesses before writing, following the successful stock-SRAM priming sequence in the local TS-Pico development notes.

Playback does **not remount or reload image files**, but a region change still sends a MEMDOCK command. SRAM copying, checksum validation, wipes and that command all take time. No physical transition-rate benchmark is claimed. This uses the stock controller rather than a custom single-OUT page-switching firmware.

## HOME memory map

| Range | Use |
|---|---|
| Below `$9800` | BASIC, managed by the Timex ROM; `CLEAR 38911` reserves the viewer's area |
| `$9800-$99FF` | Resident SRAM copy/priming gateway |
| `$9A00-$9AFF` | HOME bounce buffer |
| `$9B00-$9B7F` | Cache arguments/state |
| `$9B80-$9FFF` | RAM-enabled display/wipe routines |
| `$A000-$D64F` | Current image staging, maximum 13,904 bytes |
| `$D700-$D74F` | Previous frame's palette/mode metadata |
| `$D800-$DFFF` | Comparison/validation helpers; run only with HOME mapped |
| `$E000-$FFFF` | No application buffers; left for ROM/Pico workspace and the ROM's relocated stack |

The bank gateway disables interrupts while DOCK is overlaid, never overlays chunks 4 or 7, and restores HOME before returning to BASIC. Its entry points are BASIC USR actions, entered with HOME mapped and interrupts enabled; they are not a general ISR/interrupt-disabled banking ABI. It uses a software FF shadow instead of guessing readback. This map is checked during assembly.

## Diagnostic stages

On a stopped/error screen, `IMAGE` is the one-based list index:

| Stage | Operation |
|---:|---|
| 1 | Mounting the source TAP during preload |
| 2 | Loading palette and screen data, or old ECM blocks |
| 3 | Validating a loaded image / selecting its SRAM region |
| 4 | Writing SRAM and verifying readback |
| 5 | Recalling and validating a cached image |
| 6 | Display/wipe or normal viewing pause |

The installed TS-Pico BASIC client owns command transport and its timing/error behavior. A firmware-level stuck transaction cannot be made recoverable by the viewer's RAM tests. Retain the existing SD viewer as a fallback while checking this new build on hardware.

## Build and tests

```shell
python viewer/ramview/build.py --pasmo /path/to/pasmo --zmakebas /path/to/zmakebas
python viewer/ramview/build.py --image uferrari.tap --image ecm:ferrari.tap --name myram
python viewer/ramview/make_demo.py --pasmo /path/to/pasmo
python viewer/ramview/test_ramview.py --images-dir /path/to/your/image/directory
```

The default list comes from `viewer/image-slideshow/build.py`, including the working short-name alias. The TAP is self-contained: BASIC is followed by three CODE files named ram-bank, ram-core and ram-help. The BASIC loader reads them before mounting any image. `ramview.bin` is an assembler memory image containing gaps, not a standalone file to LOAD directly.

Tests execute the actual assembled gateway/display routines with all 24 slots, delayed bank-selector latching, readonly priming, overlapping-window copies, store-readback faults, HOME/stack preservation, matching-frame direct wipes, and mandatory blanking for palette/attribute differences. With `--images-dir`, they preload your actual images and execute two complete cache-playback loops. The Spectrum-oriented simulator is extended to allow writable DOCK below `$4000`. MEMDOCK transactions and the Timex ROM service are modeled/stubbed rather than running installed firmware. Physical SRAM bus timing, installed BASIC-client compatibility and real playback speed still need hardware testing.

## Hardware validation

Jon confirmed the fast CODE-loader RAMVIEW works on his real TS2068 with TSPico/PicoVideo. The earlier BASIC hex installer stalled after installation and is replaced. Complete nine-image looping, every transition type, and BREAK/error recovery have not yet been separately confirmed for this build. Model tests do not emulate the complete Timex ROM or Pico firmware.
