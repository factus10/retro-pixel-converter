"""Two ULA+ frames with identical palette/attributes for direct RAM wipes."""
import argparse
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent))
from pack_image import pack,image_tape

palette=bytes([0,109,182,255]*16)
for name,center in [('ramone',80),('ramtwo',176)]:
    pixels=bytearray(6144);attrs=bytearray(6144)
    for y in range(192):
        offset=((y&192)<<5)|((y&7)<<8)|((y&56)<<2)
        for col in range(32):
            attrs[offset+col]=1+y//64
            value=0
            for bit in range(8):
                x=col*8+bit
                if (x-center)**2+(y-96)**2<48**2 or 176<=y<184:
                    value|=128>>bit
            pixels[offset+col]=value
    (ROOT/(name+'.tap')).write_bytes(image_tape(pack(bytes(pixels+attrs)+palette,'ula-ecm')))

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--pasmo')
args=parser.parse_args()
command=[sys.executable,str(ROOT/'build.py'),'--name','ramdemo','--image','ramone.tap','--image','ramtwo.tap']
if args.pasmo:command+=['--pasmo',args.pasmo]
subprocess.run(command,check=True)
with ZipFile(ROOT/'ramdemo.zip','w',ZIP_DEFLATED) as archive:
    for name in ('ramdemo.tap','ramone.tap','ramtwo.tap'):
        archive.write(ROOT/name,'ramdemo/'+name)
    archive.writestr('ramdemo/README.txt',
        'Load ramdemo.tap in this directory, then RUN. It preloads two frames\n'
        'to TS-Pico SRAM and loops with wipes. Both frames have identical\n'
        'palettes and attributes, so after the first black reveal they wipe\n'
        'directly between images. SHIFT-BREAK restores black-on-white BASIC.\n'
        'Uses SRAM region 0, chunks 0-3; its previous contents are replaced.\n'
        'Uses stock MEMDOCK; physical playback is not yet verified.\n')
print('Created ramdemo.zip')
