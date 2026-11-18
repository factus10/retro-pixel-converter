"""Build the TS2068 viewers with Pasmo and zmakebas (no runtime dependencies)."""
import argparse
import base64
import functools
import operator
import shutil
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def tape_block(data):
    checksum = functools.reduce(operator.xor, data, 0)
    return struct.pack('<H', len(data) + 1) + data + bytes([checksum])


def tape_file(data, name, kind, param1, param2):
    header = bytes([0, kind]) + name.encode('ascii').ljust(10, b' ')[:10]
    header += struct.pack('<HHH', len(data), param1, param2)
    return tape_block(header) + tape_block(b'\xff' + data)


def timex_tokens(source):
    """Emit Timex-only tokens even with a Spectrum-only zmakebas."""
    return source.replace('ON ERR RESET', r'\{123} \{127}').replace('ON ERR', r'\{123}')


def code_data(code):
    # Hex strings avoid BASIC's five-byte numeric trailer per DATA value.
    return '\n'.join(f'{9010+i//32*10} DATA "{code[i:i+32].hex().upper()}"' for i in range(0, len(code), 32))


def hardware_check(exit_address, start=700):
    # PicoVideo echoes its selector at BF3B and exposes version at register 7F.
    # Two selector challenges reject constant/floating buses. Restore selector;
    # never change palette data or insist on a specific firmware version.
    lines = [
        'LET SA=IN 48955: OUT 48955,127',
        'LET PV=(IN 48955=127): LET HV=IN 65339',
        'OUT 48955,62: LET PV=PV AND (IN 48955=62) AND HV<>0 AND HV<>255',
        'OUT 48955,SA: IF PV THEN RETURN',
        'ON ERR RESET',
        f'RANDOMIZE USR {exit_address}',
        'BORDER 7: PAPER 7: INK 0: FLASH 0: BRIGHT 0: INVERSE 0: OVER 0: CLS',
        'PRINT "ULA+ not present": PRINT "(PicoVideo required)"',
        'STOP',
    ]
    return '\n'.join(f'{start+i*10} {line}' for i,line in enumerate(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pasmo', default=shutil.which('pasmo') or str(ROOT / '.build/pasmo.exe'))
    parser.add_argument('--zmakebas', default=shutil.which('zmakebas') or str(ROOT.parent.parent / 'zmakebas/zmakebas.exe'))
    args = parser.parse_args()
    build = ROOT / '.build'
    build.mkdir(exist_ok=True)
    subprocess.run([args.pasmo, '--bin', 'ulaview.asm', 'ulaview.bin', 'ulaview.sym'], cwd=ROOT, check=True)
    code = (ROOT / 'ulaview.bin').read_bytes()
    if 39936 + len(code) > 40960:
        raise ValueError('Resident code overlaps image buffer')
    if 9010 + ((len(code)-1)//32)*10 >= 9500:
        raise ValueError('DATA lines overlap slideshow list')
    for name in ('ulaview', 'ulavpico', 'ecmview'):
        template = 'ulaview' if name == 'ecmview' else name
        source = (ROOT / f'{template}.bas.in').read_text(encoding='utf-8')
        if name == 'ecmview':
            source = source.replace('75 LET EC=0', '75 LET EC=1')
        source = source.replace('@HARDWARE_CHECK@', hardware_check(39942))
        source = source.replace('@CODE_LAST@', str(39935 + len(code))).replace('@CODE_DATA@', code_data(code))
        (ROOT / f'{name}.bas').write_text(source, encoding='ascii')
        # The old local zmakebas predates Timex ON ERR. Emit its literal 0x7B
        # token instead; this also works with modern Timex-aware zmakebas.
        token_input = build / f'{name}-tokens.bas'
        token_input.write_text(timex_tokens(source), encoding='ascii')
        raw = build / f'{name}.basic'
        subprocess.run([args.zmakebas, '-r', '-o', str(raw), str(token_input)], check=True)
        basic = raw.read_bytes()
        if len(basic) > 6000:
            raise ValueError('BASIC listing leaves too little room after Timex relocation')
        # Deliberately no autostart, matching ECMVIEW: LOAD "", mount image, RUN.
        (ROOT / f'{name}.tap').write_bytes(tape_file(basic, name, 0, 32768, len(basic)))
        if name == 'ulaview':
            # Bundled tapes can load CODE immediately after BASIC, before
            # their image files. Avoid interpreting a hex installer at startup.
            fast_source = '\n'.join(line for line in source.splitlines()
                if int(line.split()[0]) < 30 or 50 <= int(line.split()[0]) < 9000)
            fast_source = fast_source.replace('50 ON ERR', '30 LOAD "ula-code" CODE 39936,' + str(len(code)) + '\n50 ON ERR')
            fast_source = fast_source.replace('ULAVIEW: RUN FOR ANOTHER IMAGE', 'ULAVIEW: IMAGE FINISHED') + '\n'
            (ROOT / 'ulaview-auto.bas').write_text(fast_source, encoding='ascii')
            token_input.write_text(timex_tokens(fast_source), encoding='ascii')
            subprocess.run([args.zmakebas, '-r', '-o', str(raw), str(token_input)], check=True)
            fast_basic = raw.read_bytes()
            auto = tape_file(fast_basic, name, 0, 10, len(fast_basic))
            auto += tape_file(code, 'ula-code', 3, 39936, 32768)
            (ROOT / 'ulaview-auto.tap').write_bytes(auto)
            print(f'Bundled viewer: {len(fast_basic)} BASIC bytes + direct {len(code)}-byte CODE load (no hex installer)')
            # Inline data keeps bundling functional when index.html is opened
            # directly from disk, where fetch() cannot read a sibling TAP.
            index = ROOT.parent / 'index.html'
            html = index.read_text(encoding='utf-8')
            start = html.index('// BEGIN GENERATED ULAVIEW READER')
            end = html.index('// END GENERATED ULAVIEW READER', start)
            encoded = base64.b64encode(auto).decode('ascii')
            html = html[:start] + '// BEGIN GENERATED ULAVIEW READER\nconst ULAVIEW_TAP_BASE64 = "' + encoded + '";\n' + html[end:]
            index.write_text(html, encoding='utf-8')
        print(f'{name}.tap: {len(basic)} BASIC bytes, {len(code)} resident bytes')


if __name__ == '__main__':
    main()
