"""Wrap a RetroPixelConverter raw output as a ULAVIEW image TAP."""
import argparse
import struct
from pathlib import Path
from build import tape_file

# port, flags, DF1 bytes, DF2 bytes, palette register count
LAYOUTS = {
    'ecm': (2, 0, 6144, 6144, 0),
    'ula-standard': (0, 1, 6912, 0, 64),
    'ula-ecm': (2, 1, 6144, 6144, 64),
    'ula-hires': (6, 1, 6144, 6144, 64),
    'ula-attr': (7, 1, 6912, 6912, 64),
    'pv-attr': (7, 0, 6912, 6912, 0),
    'pv-quad': (3, 2, 6144, 6144, 4),
}


def pack(raw, mode, border=0):
    port, flags, length1, length2, count = LAYOUTS[mode]
    if len(raw) != length1 + length2 + count:
        raise ValueError(f'{mode} requires {length1+length2+count} raw bytes; got {len(raw)}')
    if not 0 <= border <= 7:
        raise ValueError('Border must be 0..7')
    palette = raw[length1+length2:].ljust(64, b'\x00')
    payload = palette + raw[:length1+length2]
    header = b'ULAV' + bytes([2, port, flags, border])
    header += struct.pack('<HHBBH', length1, length2, count, 0, sum(payload) & 65535)
    return header + payload


def image_tape(image, viewer=b''):
    """Palette/mode metadata first, then one or two screen CODE files."""
    length1, length2 = struct.unpack_from('<HH', image, 8)
    if image[:5] != b'ULAV\x02' or len(image) != 80 + length1 + length2:
        raise ValueError('Invalid ULAV v2 staging image')
    tape = viewer + tape_file(image[:80], 'ula-pal', 3, 40960, 32768)
    tape += tape_file(image[80:80+length1], 'ula-df1', 3, 41040, 32768)
    if length2:
        tape += tape_file(image[80+length1:], 'ula-df2', 3, 41040+length1, 32768)
    return tape


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--mode', required=True, choices=LAYOUTS)
    parser.add_argument('--border', type=int, default=0)
    parser.add_argument('-o', '--output', type=Path)
    parser.add_argument('--bundle-viewer', action='store_true', help='Prepend the autostart single-image viewer')
    args = parser.parse_args()
    try:
        image = pack(args.input.read_bytes(), args.mode, args.border)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    output = args.output or args.input.with_name(args.input.stem + '_ulaview.tap')
    if output.resolve() == args.input.resolve():
        parser.error('Output must differ from input')
    viewer = Path(__file__).with_name('ulaview-auto.tap').read_bytes() if args.bundle_viewer else b''
    output.write_bytes(image_tape(image, viewer))
    print(f'{output}: {len(image)} image bytes; palette included')


if __name__ == '__main__':
    main()
