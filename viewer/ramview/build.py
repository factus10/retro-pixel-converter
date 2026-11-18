"""Build a stock-MEMDOCK SRAM slideshow; no Pico firmware replacement."""
import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent))
from build import tape_file, timex_tokens, hardware_check


def compact_numbers(source):
    # BASIC stores a six-byte numeric marker/value after every literal.
    # VAL strings save three bytes each; keep the frequent installer loop
    # untouched. Never rewrite quoted filenames, messages, DATA or comments.
    result=[]
    for line in source.splitlines():
        match=re.match(r'(\d+)\s+(.*)',line)
        if not match or not 50<=int(match[1])<7000 or match[2].startswith('REM '):
            result.append(line);continue
        pieces=re.split(r'("[^"]*")',match[2])
        for i in range(0,len(pieces),2):
            pieces[i]=re.sub(r'(?<![\w$])\d+(?![\w$])',lambda n:'VAL "'+n[0]+'"',pieces[i])
        result.append(match[1]+' '+''.join(pieces))
    return '\n'.join(result)+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pasmo',default=shutil.which('pasmo') or str(ROOT.parent/'.build/pasmo.exe'))
    parser.add_argument('--zmakebas',default=shutil.which('zmakebas') or str(ROOT.parent.parent.parent/'zmakebas/zmakebas.exe'))
    parser.add_argument('--image',action='append',help='Image TAP name, optionally prefixed ecm:; repeat for a custom list')
    parser.add_argument('--name',default='ramview',help='Output TAP/BASIC basename (1..8 letters/digits)')
    args=parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9]{1,8}',args.name):parser.error('Output name must be 1..8 letters/digits')
    if args.image:
        images=args.image
    else:
        spec=importlib.util.spec_from_file_location('image_list',ROOT.parent/'image-slideshow/build.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        images=module.IMAGES
    if not 1<=len(images)<=24:
        parser.error('The RAM viewer supports 1..24 images, three per 64 KiB SRAM region')
    for name in images:
        filename=name[4:] if name[:4].lower()=='ecm:' else name
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,8}\.[Tt][Aa][Pp]',filename):
            parser.error(f'Use an 8.3 TAP filename: {name}')
    subprocess.run([args.pasmo,'--bin','ramview.asm','ramview.bin','ramview.sym'],cwd=ROOT,check=True)
    symbols={m[1]:int(m[2],16) for line in (ROOT/'ramview.sym').read_text().splitlines()
             if (m:=re.match(r'(\w+)\s+EQU\s+0?([0-9A-F]+)H',line))}
    assert symbols['CACHE_END']<=0x9A00,'Bank gateway overlaps its bounce buffer'
    assert symbols['CODE_END']<=0xA000,'Display code overlaps image staging'
    assert symbols['RAM_HELPER_END']<=0xE000,'Helpers overlap TS-Pico top-memory margin'
    segments=[(0x9800,symbols['CACHE_END']),(0x9B80,symbols['CODE_END']),(0xD800,symbols['RAM_HELPER_END'])]
    blob=(ROOT/'ramview.bin').read_bytes()
    source=(ROOT/'ramview.bas.in').read_text(encoding='ascii')
    values={'@CACHE_NEXT@':str(segments[0][1]),'@CORE_NEXT@':str(segments[1][1]),
            '@HELPER_LAST@':str(segments[2][1]-1),'@IMAGE_COUNT@':str(len(images)),
            '@CODE_BYTES@':str(sum(end-start for start,end in segments)),

            '@IMAGE_DATA@':'\n'.join(f'{9510+i*10} DATA "{name}"' for i,name in enumerate(images))}
    for key,value in values.items():source=source.replace(key,value)
    source=source.replace('@HARDWARE_CHECK@', hardware_check(39814,900))
    source=compact_numbers(source)
    (ROOT/(args.name+'.bas')).write_text(source,encoding='ascii')
    scratch=ROOT.parent/'.build'
    tokens=scratch/'ramview-tokens.bas';raw=scratch/'ramview.basic'
    tokens.write_text(timex_tokens(source),encoding='ascii')
    subprocess.run([args.zmakebas,'-r','-o',str(raw),str(tokens)],check=True)
    basic=raw.read_bytes()
    if len(basic)>6500:raise ValueError(f'BASIC too large for reserved map: {len(basic)} bytes')
    tap=tape_file(basic,args.name,0,32768,len(basic))
    for name,(start,end) in zip(('ram-bank','ram-core','ram-help'),segments):
        tap+=tape_file(blob[start-0x9800:end-0x9800],name,3,start,32768)
    (ROOT/(args.name+'.tap')).write_bytes(tap)
    layout_name='layout.json' if args.name=='ramview' else args.name+'.json'
    (ROOT/layout_name).write_text(json.dumps({'images':images,'segments':segments,
        'cache_regions':list(range(0,2*((len(images)+2)//3),2)), 'frame_bytes':13904,
        'basic_bytes':len(basic),'symbols':symbols},indent=2)+'\n')
    print(f'{args.name}.tap: {len(images)} images, {len(basic)} BASIC bytes; cache gateway {segments[0][1]-segments[0][0]} bytes; display {segments[1][1]-segments[1][0]} bytes')


if __name__=='__main__':main()
