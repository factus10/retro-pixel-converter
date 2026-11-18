"""Generate a reproducible ULA+ ECM palette/checkerboard demonstration."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from pack_image import pack, image_tape

ROOT = Path(__file__).resolve().parent
palette = bytearray(((i >> 3) << 5) | ((i & 7) << 2) | (((i >> 1) ^ (i >> 3)) & 3) for i in range(64))
palette[8] = 0  # BORDER 0 uses bank-0 PAPER 0; keep the demo border black.
pixels, attrs = bytearray(6144), bytearray(6144)
for y in range(192):
    address = ((y & 192) << 5) | ((y & 7) << 8) | ((y & 56) << 2)
    for col in range(32):
        pixels[address+col] = 0xAA if y & 1 else 0x55
        bank = col // 8
        ink = (y // 24) & 7
        paper = (col + y // 24) & 7
        attrs[address+col] = (bank << 6) | (paper << 3) | ink
image = pack(bytes(pixels + attrs) + bytes(palette), 'ula-ecm')
(ROOT / 'ulademo.tap').write_bytes(image_tape(image))
(ROOT / 'ulademo-viewer.tap').write_bytes(image_tape(image, (ROOT / 'ulaview-auto.tap').read_bytes()))
with ZipFile(ROOT / 'tspico-slideshow.zip', 'w', ZIP_DEFLATED) as archive:
    for name in ('ulavpico.tap', 'ulademo.tap'):
        archive.write(ROOT / name, 'ulapics/' + name)
    archive.writestr('ulapics/README.txt',
        'Copy ulapics to the TS-Pico SD card.\n'
        'SAVE "tpi:cd ulapics"\nLOAD "tpi:ulavpico.tap"\nLOAD ""\nRUN\n\n'
        'Add data-only image TAPs exported with Include ULAVIEW unchecked.\n'
        'Edit line 9510 to list their filenames, followed by "*".\n'
        'Line 70 sets T (seconds, 0=wait key) and LP (1=repeat).\n'
        'Hardware playback has not yet been verified.\n')
print('Created ulademo.tap (ULA+ ECM, 64-color test pattern)')
