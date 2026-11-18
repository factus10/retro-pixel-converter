"""Execute the SRAM viewer with banked memory and a delayed-selector model.

MEMDOCK's BASIC/firmware transaction is represented by select_region(); the
actual Z80 priming, mapping, copy, verification and display code is executed.
This is not a physical TS-Pico timing or full-ROM test.
"""
import json
import argparse
import struct
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'.build/deps'))
sys.path.insert(0,str(ROOT.parent))
from skoolkit.simulator import Simulator
from test_viewer import read_tap

LAYOUT=json.loads((ROOT/'layout.json').read_text())
SYMBOLS=LAYOUT['symbols']


class DockSimulator(Simulator):
    def ldir_fast(self,r,m,inc):
        original=super().ldir_fast(r,m,inc)
        def execute():
            dest=r[5]+256*r[4]
            if dest>=0x4000 or not m.mapped(dest):
                original();return
            # SkoolKit's Spectrum core treats 0000-3FFF as permanently ROM.
            # DOCK makes that range writable; model native LDIR for this case.
            assert not r[26]
            count=r[3]+256*r[2];source=r[7]+256*r[6]
            for i in range(count):m[(dest+i*inc)&65535]=m[(source+i*inc)&65535]
            last=m[(source+(count-1)*inc)&65535]
            dest=(dest+count*inc)&65535;source=(source+count*inc)&65535
            r[3]=r[2]=0;r[5],r[4]=dest&255,dest>>8;r[7],r[6]=source&255,source>>8
            r[15]=(r[15]&128)|((r[15]+2*count)&127)
            n=r[0]+last;r[1]=(r[1]&0xC1)+(n&2)*16+(n&8)
            r[25]+=21*count-5;r[24]=(r[24]+2)&65535
        return execute


class BankMemory:
    def __init__(self):
        self.home=[(i*19+7)&255 for i in range(65536)]
        self.ram=[bytearray(65536) for _ in range(8)]
        self.mask=0;self.ff=2;self.region=7;self.pending=None;self.accesses=0
        self.regs=None;self.screen_writes=[];self.port_writes=[]
        self.palette={};self.selected_register=0
        self.inject_fault=False

    def __len__(self):return 65536

    def select_region(self,region):
        assert self.mask==0
        self.pending=region//2
        self.accesses=0

    def mapped(self,address):
        return not self.ff&128 and self.mask&(1<<(address//8192))

    def dock(self,address):
        if self.regs:
            assert not self.regs[26],'Interrupts enabled with a DOCK overlay'
            assert not self.mapped(self.regs[24]),'Executing code was banked out'
        self.accesses+=1
        if self.pending is not None and self.accesses>=4:
            self.region=self.pending;self.pending=None
        return self.ram[self.region]

    def __getitem__(self,address):
        if isinstance(address,slice):
            return [self[i] for i in range(*address.indices(65536))]
        if self.mapped(address):return self.dock(address)[address]
        return self.home[address]

    def __setitem__(self,address,value):
        if isinstance(address,slice):
            for i,v in zip(range(*address.indices(65536)),value):self[i]=v
            return
        if self.mapped(address):
            self.dock(address)[address]=value^(1 if self.inject_fault and address==16 else 0)
        else:
            if 0x4000<=address<0x7B00:self.screen_writes.append(address)
            self.home[address]=value

    def write_port(self,registers,port,value,*timing):
        self.port_writes.append((port,value))
        if port&255==244:
            assert not value&0x90,'Overlay would hide resident code or stack'
            self.mask=value
        elif port&255==255:self.ff=value
        elif port==48955:self.selected_register=value
        elif port==65339:self.palette[self.selected_register]=value

    def read_port(self,registers,port,*timing):
        return self.ff if port&255==255 else 0


def machine():
    memory=BankMemory()
    binary=(ROOT/'ramview.bin').read_bytes()
    for start,end in LAYOUT['segments']:
        memory.home[start:end]=binary[start-0x9800:end-0x9800]
    memory.home[0x0E8E]=0xC9
    sim=DockSimulator(memory,{'SP':0xF600,'IX':0x1234,'IY':0x5C3A},config={'fast_ldir':True})
    memory.regs=sim.registers;sim.set_tracer(memory)
    return sim,memory


def call(sim,address):
    r=sim.registers;m=sim.memory
    assert m.mask==0
    r[12]=0xF5FE;m.home[0xF5FE:0xF600]=[0,1];r[24]=address
    for _ in range(3000000):
        if r[24]==256:
            assert r[12]==0xF600 and m.mask==0
            assert (r[8]<<8|r[9])==0x1234 and (r[10]<<8|r[11])==0x5C3A
            return r[2]<<8|r[3]
        sim.run()
    raise AssertionError('Instruction budget exceeded')


def put16(memory,address,value):memory.home[address:address+2]=struct.pack('<H',value)


def stage(memory,data):
    memory.home[0xA000:0xD650]=bytes(data).ljust(13904,b'\0')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--images-dir',type=Path)
    args=parser.parse_args()
    sim,memory=machine();assert call(sim,38930)==0
    before=memory.home[0xA000:0xD650].copy()
    assert call(sim,38933)==0
    assert memory.home[0xA000:0xD650]==before
    assert memory.palette[64]==0 and memory.palette[65]==0 and memory.ff==0
    assert memory.home[0x5800:0x5B00]==[56]*768
    assert memory.home[0x9B02]==0
    print('PASS native black-on-white preload screen, with staged image untouched')
    saved_top=memory.home[0xE000:0xF500].copy()
    saved_screens=memory.home[0x4000:0x7B00].copy()
    frames=[]
    # All 24 slots: low and overlapping high windows in all eight regions.
    for index in range(24):
        region=2*(index//3);base=(0,0x4000,0xA000)[index%3]
        memory.select_region(region);assert call(sim,38921)==0
        assert memory.pending is None and memory.accesses>=8
        frame=bytes((index*37+i*13+(i>>8))&255 for i in range(13904))
        frames.append(frame);stage(memory,frame);put16(memory,0x9B00,base)
        assert call(sim,38912)==0
        assert bytes(memory.ram[index//3][base:base+13904])==frame
        assert memory.home[0x4000:0x7B00]==saved_screens
    for index,frame in enumerate(frames):
        memory.select_region(2*(index//3));assert call(sim,38921)==0
        put16(memory,0x9B00,(0,0x4000,0xA000)[index%3])
        stage(memory,bytes(13904));assert call(sim,38915)==0
        assert bytes(memory.home[0xA000:0xD650])==frame
    assert memory.home[0xE000:0xF500]==saved_top
    put16(memory,0x9B00,0x8000);assert call(sim,38912)==1
    put16(memory,0x9B00,0xE000);assert call(sim,38915)==1
    memory.select_region(0);assert call(sim,38921)==0
    put16(memory,0x9B00,0);stage(memory,frames[0]);memory.inject_fault=True
    assert call(sim,38912)==1 and memory.mask==0
    memory.inject_fault=False
    print('PASS all 24 SRAM slots, delayed priming, high-window bounce copies, readback and HOME preservation')

    fixture=ROOT.parent/'.build/fixtures/ula-ecm.ulav'
    image=bytearray(fixture.read_bytes())
    stage(memory,image);assert call(sim,38918)==0
    memory.home[SYMBOLS['WIPE_MODE']]=1;memory.home[SYMBOLS['WIPE_SPEED']]=0
    memory.home[0x9B03]=0
    assert call(sim,0x9B83)==0;assert call(sim,38927)==0
    # Same palette and attributes, different pixel bitmap: direct wipe is safe.
    image[80:6224]=bytes(b^255 for b in image[80:6224])
    image[14:16]=struct.pack('<H',sum(image[16:])&65535)
    stage(memory,image);assert call(sim,38918)==0;assert call(sim,38924)==0
    assert memory.home[0x9B03]==1
    memory.port_writes.clear();memory.screen_writes.clear()
    assert call(sim,0x9B83)==0
    assert not memory.port_writes,'Direct wipe must not change palette or native mode'
    assert memory.home[0x4000:0x5800]==list(image[80:6224])
    assert memory.home[0x6000:0x7800]==list(image[6224:])
    assert call(sim,38927)==0
    # A changed attribute or palette must force the clash-free black path.
    image[6224]^=1;image[14:16]=struct.pack('<H',sum(image[16:])&65535)
    stage(memory,image);assert call(sim,38924)==0;assert memory.home[0x9B03]==0
    assert call(sim,0x9B83)==0;assert call(sim,38927)==0
    image[16]^=1;image[14:16]=struct.pack('<H',sum(image[16:])&65535)
    stage(memory,image);assert call(sim,38924)==0;assert memory.home[0x9B03]==0
    print('PASS compatible direct wipe and mandatory blanking for palette/attribute changes')

    # Decode the TAP's BASIC DATA exactly as its sparse installer does.
    blocks=read_tap(ROOT/'ramview.tap')
    header,block=blocks[:2]
    basic=block[1:-1];lines={}
    while basic:
        n=int.from_bytes(basic[:2],'big');length=int.from_bytes(basic[2:4],'little')
        lines[n],basic=basic[4:4+length],basic[4+length:]
    actual=b''.join(blocks[i][1:-1] for i in (3,5,7))
    assert len(blocks)==8
    for i,(start,end) in enumerate(LAYOUT['segments']):
        h=blocks[2+i*2]
        assert h[1]==3 and int.from_bytes(h[14:16],'little')==start
        assert len(blocks[3+i*2])-2==end-start
    assert b'ram-bank' in lines[30] and b'ram-core' in lines[35] and b'ram-help' in lines[40]
    binary=(ROOT/'ramview.bin').read_bytes()
    expected=b''.join(binary[a-0x9800:b-0x9800] for a,b in LAYOUT['segments'])
    assert actual==expected
    assert lines[500].replace(b' ',b'').startswith(b'\x7b\x7f')
    assert len(LAYOUT['images'])==9 and 'upainthi.tap' in LAYOUT['images']
    assert b'tpi:memdock' in lines[770] and b'memboot' not in block.lower()
    assert b'LOADING VIEWER CODE' in lines[25]
    assert b'PRELOADING' in lines[800]
    assert b'Writing/checking SRAM' in lines[220]
    assert b'CACHE READY' in lines[235]
    assert b'PH=' in lines[765] and b'38933' in lines[765]
    for number,line in lines.items():
        if 250<=number<=380:
            assert b'38933' not in line and b'\xf5' not in line,'Playback must not print status over images'
    print('PASS BASIC TAP framing, three resident CODE blocks and stock MEMDOCK command')
    if args.images_dir:
        actual_sim,actual_memory=machine();assert call(actual_sim,38930)==0
        current=-1;expected_frames=[]
        for index,name in enumerate(LAYOUT['images']):
            legacy=name[:4].lower()=='ecm:'
            path=args.images_dir/(name[4:] if legacy else name)
            blocks=read_tap(path)
            files={h[2:12].decode().strip():b[1:-1] for h,b in zip(blocks[::2],blocks[1::2])}
            stage(actual_memory,bytes(13904))
            if legacy:
                actual_memory.home[41040:47184]=files['ecm-pix']
                actual_memory.home[47184:53328]=files['ecm-atr']
                assert call(actual_sim,0x9B92)==0
            else:
                for h,b in zip(blocks[::2],blocks[1::2]):
                    assert h[1]==3,'Expected a data-only image TAP'
                    address=int.from_bytes(h[14:16],'little')
                    actual_memory.home[address:address+len(b)-2]=b[1:-1]
            assert call(actual_sim,38918)==0,path.name
            expected_frames.append(bytes(actual_memory.home[0xA000:0xD650]))
            region=2*(index//3)
            if region!=current:
                assert call(actual_sim,0x9B80)==0
                actual_memory.home[0x9B02]=2;actual_memory.select_region(region)
                assert call(actual_sim,38921)==0;current=region
            put16(actual_memory,0x9B00,(0,0x4000,0xA000)[index%3])
            assert call(actual_sim,38912)==0,path.name
        for loop in range(2):
            for index,frame in enumerate(expected_frames):
                region=2*(index//3)
                if region!=current:
                    assert call(actual_sim,0x9B80)==0
                    actual_memory.home[0x9B02]=2;actual_memory.home[0x9B04]=0
                    actual_memory.select_region(region);assert call(actual_sim,38921)==0;current=region
                put16(actual_memory,0x9B00,(0,0x4000,0xA000)[index%3])
                assert call(actual_sim,38915)==0
                assert bytes(actual_memory.home[0xA000:0xD650])==frame
                assert call(actual_sim,38918)==0
                actual_memory.home[SYMBOLS['WIPE_MODE']]=1+(index%4)
                actual_memory.home[SYMBOLS['WIPE_SPEED']]=0
                assert call(actual_sim,38924)==0
                assert call(actual_sim,0x9B83)==0
                assert call(actual_sim,38927)==0
                actual_memory.home[0x9B02]=2 if frame[6]==1 else frame[5]
                length1,length2=struct.unpack_from('<HH',frame,8)
                assert actual_memory.home[16384:16384+length1]==list(frame[80:80+length1])
                if length2:assert actual_memory.home[24576:24576+length2]==list(frame[80+length1:80+length1+length2])
        call(actual_sim,0x9B86)  # restore is a RANDOMIZE USR action, not a BC-status API
        assert actual_memory.mask==0 and actual_memory.palette[64]==actual_memory.palette[65]==0
        print('PASS actual image preload and two SRAM playback loops:',len(expected_frames),'images')
    print('All RAM-viewer model tests passed; physical TS-Pico playback is unverified.')


if __name__=='__main__':main()
