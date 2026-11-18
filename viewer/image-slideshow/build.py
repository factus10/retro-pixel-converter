"""Build the requested nine-image TS-Pico slideshow from the shared reader."""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VIEWER = ROOT.parent
sys.path.insert(0, str(VIEWER))
from build import tape_file, timex_tokens, code_data, hardware_check

IMAGES = [
    'uferrari.tap',
    'ueye.tap',
    'uflowers.tap',
    'uchamel.tap',
    'uartemis.tap',
    'umarble.tap',
    'upaint.tap',
    'upainthi.tap',
    'ulandsc.tap',
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zmakebas', default=shutil.which('zmakebas') or str(VIEWER.parent.parent / 'zmakebas/zmakebas.exe'))
    args = parser.parse_args()
    code = (VIEWER / 'ulaview.bin').read_bytes()
    source = (VIEWER / 'ulavpico.bas.in').read_text(encoding='ascii')
    source = source.replace('@HARDWARE_CHECK@', hardware_check(39942))
    data = code_data(code)
    source = source.replace('@CODE_LAST@',str(39935+len(code))).replace('@CODE_DATA@',data)
    image_lines = '\n'.join(f'{9510+i*10} DATA "{name}"' for i,name in enumerate(IMAGES+['*']))
    source = source.replace('9510 DATA "ulademo.tap","*"',image_lines)
    (ROOT / 'ulavpico.bas').write_text(source,encoding='ascii')
    temp = VIEWER / '.build'
    temp.mkdir(exist_ok=True)
    tokens = temp / 'image-slideshow-tokens.bas'
    tokens.write_text(timex_tokens(source),encoding='ascii')
    raw = temp / 'image-slideshow.basic'
    subprocess.run([args.zmakebas,'-r','-o',str(raw),str(tokens)],check=True)
    basic = raw.read_bytes()
    if len(basic)>6000:
        raise ValueError('BASIC exceeds the shared reader memory budget')
    (ROOT / 'ulavpico.tap').write_bytes(tape_file(basic,'ulavpico',0,32768,len(basic)))
    print(f'Built ulavpico.tap: {len(IMAGES)} images, 10 seconds each, looping; {len(basic)} BASIC bytes')


if __name__ == '__main__':
    main()
