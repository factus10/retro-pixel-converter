TS-Pico slideshow for the nine requested images

Copy this ulavpico.tap into the same SD-card directory as:
  uferrari.tap
  ueye.tap
  uflowers.tap
  uchamel.tap
  uartemis.tap
  umarble.tap
  upaint.tap
  upainthi.tap
  ulandsc.tap

upwithview.tap is deliberately excluded.
upainthi.tap is a byte-identical 8.3-name copy of upainthires.tap. The original
long-named image is preserved, but this slideshow uses the shorter alias to
test compatibility with the installed TS-Pico firmware's mounting path.
Unprefixed entries use the data-only ula-pal / ula-df1 / ula-df2 format.
Old standard ECM images are also supported by prefixing their DATA entries:
  DATA "ecm:ferrari.tap"
This loads the actual file ferrari.tap and its ecm-atr/ecm-pix blocks using
native Timex colors. Do not rename the disk file to include "ecm:".
Use ecmview.tap for a single old ECM image without editing the ULA preset.

Change to that directory on the TS-Pico, then:
  LOAD "tpi:ulavpico.tap"
  LOAD ""
  RUN

Displays each picture for 10 seconds (a key advances early), in the order
above, repeating continuously by default (LP=1 in line 70). Set LP=0 for
one pass. SHIFT-BREAK resets the error trap, restores normal Timex video,
and clears to black text on white with a white border before stopping in
BASIC. FLASH, BRIGHT, INVERSE and OVER are reset too.

Wipes are enabled by default: line 74 has RW=1 (random), W=0, WS=2 (speed).
Set RW=0 for a fixed W: 0 instant, 1 left, 2 right, 3 curtain, 4 blinds.
WS=0 is fastest; larger values slow the wipe. ECM, standard and mode 7 use
wipes when the palette contains black. Other modes reveal instantly.
Blanking now blacks the palette and clears attributes before bitmap pixels.

ulavpico.bas is the editable listing. build.py reproduces this custom version
from the shared reader and the filename list; run it after rebuilding the
shared viewer if its machine code changes.

The TAP and list were checked locally. Physical playback and the actual image
files have not been checked; the list was transcribed from the screenshot.

Mode 7 update: ULA+ output modes now use PicoVideo register 65 while the
physical Timex stays in native ECM mode 2. The actual image files in the
extcolor/ulaview folder, including upainthires.tap, passed simulated display
and checksum checks with this reader. Hardware confirmation is still needed.

udiag.tap is a one-image diagnostic for upainthi.tap. Load it from the
same directory and RUN. Its last visible border identifies the current step:
  blue: mounting upainthi.tap
  red: loading ula-pal
  magenta: validating palette/mode metadata
  green: loading ula-df1
  cyan: loading ula-df2
  yellow: validating/copying the image and selecting the display
If the image displays, it should return to BASIC after 10 seconds.
