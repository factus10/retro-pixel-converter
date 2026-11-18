"""Execute the real assembled viewer in SkoolKit's Z80 simulator.

Run converter fixtures first: node tests/video-modes.cjs
Then: python viewer/test_viewer.py
Install test dependency with: pip install --target viewer/.build/deps skoolkit
The Timex ROM mode service is a RET stub; its inputs and banking port sequence
are checked, but this does not claim to emulate the Timex ROM or TS-Pico.
"""
import json
import struct
import sys
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / '.build/deps'))
from skoolkit.simulator import Simulator
from pack_image import pack, image_tape


class Ports:
    def __init__(self):
        self.selected = 0
        self.values = {}
        self.quad = [0] * 4
        self.quad_address = 0
        self.events = []
        self.native = 0
        self.revealing = False
        self.on_reveal = None

    def write_port(self, registers, port, value, *timing):
        self.events.append((port, value))
        if port == 48955:
            self.selected = value
        elif port == 65339:
            self.values[self.selected] = value
            if self.selected == 68:
                self.quad_address = value
            elif self.selected == 71:
                self.quad[self.quad_address] = value
                self.quad_address = (self.quad_address + 1) % 4
        elif port & 255 == 255:
            self.native = value
        elif port & 255 == 254:
            self.revealing = value == 3  # fixture border, written immediately before reveal
            if self.revealing and self.on_reveal:
                self.on_reveal()

    def read_port(self, registers, port, *timing):
        return self.native if port & 255 == 255 else 0


class WatchedMemory(list):
    def __init__(self, values):
        super().__init__(values)
        self.ports = None
        self.writes = []
        self.reveal_writes = []
        self.first_screen_black = None

    def __setitem__(self, address, value):
        if isinstance(address, int) and self.ports and 0x4000 <= address < 0x7B00:
            if self.first_screen_black is None:
                self.first_screen_black = self.ports.values.get(64) == 1 and all(self.ports.values.get(i) == 0 for i in range(64))
            self.writes.append(address)
            if self.ports.revealing:
                self.reveal_writes.append(address)
        super().__setitem__(address, value)


def machine(image=b''):
    memory = WatchedMemory((i * 13 + 17) & 255 for i in range(65536))
    code = (ROOT / 'ulaview.bin').read_bytes()
    memory[39936:39936+len(code)] = code
    memory[40960:40960+len(image)] = image
    memory[0x0E8E] = 0xC9  # Timex ROM service stub.
    sim = Simulator(memory, {'SP': 0x9800, 'IX': 0x1234, 'IY': 0x5C3A}, config={'fast_ldir': True})
    ports = Ports()
    memory.ports = ports
    sim.set_tracer(ports)
    return sim, ports


def call(sim, address):
    # Synthetic BASIC USR return address, with a finite instruction budget.
    regs, memory = sim.registers, sim.memory
    sp = 0x9800
    regs[12] = sp - 2
    memory[sp-2:sp] = [0, 1]
    regs[24] = address
    services = []
    for _ in range(2000000):
        if regs[24] == 0x100:
            assert regs[12] == sp
            assert (regs[8] << 8 | regs[9]) == 0x1234
            assert (regs[10] << 8 | regs[11]) == 0x5C3A
            return (regs[2] << 8 | regs[3]), services
        if regs[24] == 0x0E8E:
            services.append(regs[0])
        sim.run()
    raise AssertionError('Viewer exceeded instruction budget')


def read_tap(path):
    data = path.read_bytes()
    blocks = []
    while data:
        length = struct.unpack_from('<H', data)[0]
        block, data = data[2:2+length], data[2+length:]
        assert len(block) == length
        checksum = 0
        for b in block:
            checksum ^= b
        assert checksum == 0
        blocks.append(block)
    return blocks


def main():
    sim, ports = machine()
    _, services = call(sim, 39936)
    assert services == [2], services
    assert ports.values[64] == 1 and ports.values[65] == 2
    assert all(ports.values[c] == 0 for c in range(64))
    assert sim.memory[0x4000:0x5800] == [0]*6144
    assert sim.memory[0x6000:0x7800] == [0]*6144
    assert sim.memory.first_screen_black
    assert sim.memory.writes[0] == 0x6000
    first_pixel = sim.memory.writes.index(0x4000)
    assert all(a in sim.memory.writes[:first_pixel] for a in (0x6000,0x77FF,0x5800,0x5AFF,0x7800,0x7AFF))
    # ROM service must be bracketed by HSR=1/0 and FF banking bit=1/0.
    assert [(p & 255, v) for p, v in ports.events if p & 255 == 244] == [(244,1),(244,0)]
    fixtures = sorted((ROOT / '.build/fixtures').glob('*.ulav'))
    assert len(fixtures) == 6, 'Run node tests/video-modes.cjs to create fixtures'
    for fixture in fixtures:
        data = fixture.read_bytes()
        expected = json.loads(fixture.with_suffix('.json').read_text())
        raw = bytes(b for screen in expected['screens'] for b in screen) + bytes(expected['registers'])
        assert pack(raw, fixture.stem, 3) == data, 'Python packer and converter formats differ'
        assert image_tape(data) == fixture.with_suffix('.tap').read_bytes()
        bundled = fixture.with_name(fixture.stem+'-bundled.tap').read_bytes()
        assert image_tape(data, (ROOT / 'ulaview-auto.tap').read_bytes()) == bundled
        # Model the BASIC viewer's exact sequential loads from the named files.
        tape_blocks = read_tap(fixture.with_suffix('.tap'))
        assert len(tape_blocks) == (4 if len(expected['screens']) == 1 else 6)
        staged_sim, staged_ports = machine()
        expected_names = [b'ula-pal   ', b'ula-df1   ', b'ula-df2   ']
        for i in range(0, len(tape_blocks), 2):
            header, content = tape_blocks[i:i+2]
            assert header[1] == 3 and header[2:12] == expected_names[i//2]
            address = struct.unpack_from('<H', header, 14)[0]
            size = struct.unpack_from('<H', header, 12)[0]
            assert size == len(content)-2
            staged_sim.memory[address:address+size] = content[1:-1]
            if i == 0:
                assert size == 80
                assert call(staged_sim, 39945)[0] == 0
                assert staged_ports.events == []
        assert staged_sim.memory[40960:40960+len(data)] == list(data)
        assert call(staged_sim, 39939)[0] == 0
        sim, ports = machine(data)
        untouched_top = sim.memory[0xE000:].copy()
        code_before = sim.memory[39936:40960].copy()
        result, services = call(sim, 39939)
        assert result == 0, (fixture.name, result)
        assert services == []
        for address, screen in zip((16384,24576), expected['screens']):
            assert sim.memory[address:address+len(screen)] == screen, fixture.name
        assert sim.memory[0xE000:] == untouched_top
        assert sim.memory[39936:40960] == code_before
        assert ports.native == (2 if expected['flags'] == 1 else expected['port'])
        assert ports.values[64] == (expected['flags'] & 1)
        assert ports.values[65] == (expected['port'] or 128)
        if expected['flags'] == 1:
            assert [ports.values[c] for c in range(64)] == expected['registers']
        elif expected['flags'] == 2:
            assert ports.quad == expected['registers']
        assert ports.events[-1][0] & 255 == 254 and ports.events[-1][1] == 3
        _, services = call(sim, 39942)
        assert services == [0]
        assert ports.values[64] == ports.values[65] == 0
        # Invalid magic/version/mode/flags/border/lengths/count/reserved/checksum.
        for position in (0,4,5,6,7,8,10,12,13,14,len(data)-1):
            damaged = bytearray(data)
            damaged[position] ^= 128
            bad_sim, bad_ports = machine(damaged)
            before = bad_sim.memory[0x4000:0x8000].copy()
            result, _ = call(bad_sim, 39939)
            assert result == 1, (fixture.name, position)
            assert before == bad_sim.memory[0x4000:0x8000]
            assert not bad_ports.events
        print('PASS Z80 display, palette, mode, restore and corruption checks:', fixture.stem)
    for name in ('ula-ecm', 'ula-standard', 'ula-attr', 'pv-attr'):
        fixture = ROOT / '.build/fixtures' / (name+'.ulav')
        image = bytearray(fixture.read_bytes())
        image[24] = 0  # PAPER 0 must be black for a black-background reveal.
        image[14:16] = struct.pack('<H',sum(image[16:]) & 65535)
        expected = json.loads(fixture.with_suffix('.json').read_text())
        width = 64 if name in ('ula-attr','pv-attr') else 32
        for wipe in range(1,5):
            sim, ports = machine(image)
            sim.memory[39948] = wipe
            sim.memory[39949] = 2
            assert call(sim,39939)[0] == 0, (name,wipe)
            assert sim.memory[39950] == 1, 'Expected an animated reveal'
            for address,screen in zip((16384,24576),expected['screens']):
                assert sim.memory[address:address+len(screen)] == screen, (name,wipe)
            columns=[]
            for address in sim.memory.reveal_writes:
                if 0x4000 <= address < 0x4020:
                    columns.append((address-0x4000)*(2 if width==64 else 1))
                elif width==64 and 0x6000 <= address < 0x6020:
                    columns.append((address-0x6000)*2+1)
            order = list(range(width)) if wipe==1 else list(reversed(range(width))) if wipe==2 else [c for i in range(width//2) for c in (width//2-1-i,width//2+i)] if wipe==3 else [c for offset in range(4) for c in range(offset,width,4)]
            assert columns == order, (name,wipe,columns)
        print('PASS four wipe patterns, column order and final screen bytes:',name)
    # Black may be in any INK/PAPER bank, not just the newer RPC PAPER-0 slot.
    for slot in (0,8,23,45,63):
        image = bytearray((ROOT / '.build/fixtures/ula-ecm.ulav').read_bytes())
        image[16:80] = bytes([128])*64
        image[16+slot] = 0
        image[14:16] = struct.pack('<H',sum(image[16:]) & 65535)
        sim, ports = machine(image)
        sim.memory[39948] = 1
        black_attr = ((slot//16)<<6) | (((slot&7)<<3) if slot&8 else slot&7)
        black_pixels = 0 if slot&8 else 255
        def check_hidden_frame():
            assert sim.memory[0x4000:0x5800] == [black_pixels]*6144
            assert sim.memory[0x6000:0x7800] == [black_attr]*6144
        ports.on_reveal = check_hidden_frame
        assert call(sim,39939)[0] == 0
        assert sim.memory[39950] == 1
    print('PASS fully black hidden frame with black INK/PAPER in multiple banks')
    # Earlier two-file ECM tapes have no ula-pal; synthesize metadata in RAM.
    source = (ROOT / '.build/fixtures/ula-ecm.ulav').read_bytes()
    for wipe in range(5):
        sim,ports = machine()
        sim.memory[41040:53328] = source[80:]
        assert call(sim,39954)[0] == 0
        assert bytes(sim.memory[40960:53328]) == pack(source[80:], 'ecm')
        assert call(sim,39945)[0] == 0
        sim.memory[39948] = wipe
        assert call(sim,39939)[0] == 0
        assert sim.memory[16384:22528] == list(source[80:6224])
        assert sim.memory[24576:30720] == list(source[6224:])
        assert ports.values[64] == 0 and ports.native == 2
    print('PASS legacy ECM metadata, native palette and all four wipes')
    for name in ('ulaview', 'ulavpico', 'ecmview'):
        header, block = read_tap(ROOT / f'{name}.tap')
        assert header[0:2] == b'\x00\x00'
        assert struct.unpack_from('<H', header, 12)[0] == len(block)-2
        assert struct.unpack_from('<H', header, 14)[0] == 32768  # no autostart
        basic = block[1:-1]
        lines = {}
        while basic:
            number = int.from_bytes(basic[:2], 'big')
            length = int.from_bytes(basic[2:4], 'little')
            lines[number], basic = basic[4:4+length], basic[4+length:]
        check_line = 162 if name == 'ulavpico' else 132
        assert b'40966' in lines[check_line] and b'40965' in lines[check_line]
        assert b'48955' in lines[700] and b'127' in lines[700]
        assert b'65339' in lines[710] and b'62' in lines[720]
        assert b'SA' in lines[730], 'Probe must restore the original selector'
        assert lines[740].replace(b' ',b'').startswith(b'\x7b\x7f')
        assert b'ULA+ not present' in lines[770] and b'PicoVideo required' in lines[770]
        assert lines[50][0] == 123  # genuine TS2068 ON ERR token
        assert lines[500].replace(b' ', b'').startswith(b'\x7b\x7f'), 'Error cleanup must reset ON ERR before any operation'
        reset_line = 305 if name == 'ulavpico' else 215
        assert lines[reset_line].replace(b' ', b'').startswith(b'\x7b\x7f'), 'Normal exit must reset ON ERR before STOP'
        cleanup = b':'.join(bytes([token])+str(value).encode()+b'\x0e\x00\x00'+struct.pack('<H',value)+b'\x00'
                            for token,value in ((0xE7,7),(0xDA,7),(0xD9,0),(0xDB,0),(0xDC,0),(0xDD,0),(0xDE,0))) + b':\xfb\r'
        assert lines[520] == cleanup, 'BREAK cleanup must restore black-on-white and reset display attributes'
        if name == 'ulavpico':
            assert b'LP=1\x0e\x00\x00\x01\x00\x00' in lines[70], 'Slideshow should loop by default'
        assert lines[140 if name == 'ulavpico' else 110].startswith(b'\xef')  # LOAD
        assert b'ecm-atr' in lines[600] and b'ecm-pix' in lines[610]
        assert b'39954' in lines[620]
        if name == 'ecmview':
            assert b'EC=1\x0e\x00\x00\x01\x00\x00' in lines[75]
        if name == 'ulavpico':
            assert b'ecm:' in lines[105] and b'ECM:' in lines[105]
        hex_strings = []
        for number,line in sorted(lines.items()):
            if 9010 <= number < 9500:
                hex_strings.append(line.split(b'"')[1].decode('ascii'))
        assert bytes.fromhex(''.join(hex_strings)) == (ROOT / 'ulaview.bin').read_bytes()
        print('PASS BASIC TAP header, checksum, line structure and Timex error token:', name)
    demo = read_tap(ROOT / 'ulademo.tap')
    demo_sim, _ = machine()
    assert len(demo) == 6
    for i in range(0, len(demo), 2):
        header, block = demo[i:i+2]
        addr = struct.unpack_from('<H', header, 14)[0]
        demo_sim.memory[addr:addr+len(block)-2] = block[1:-1]
    assert call(demo_sim, 39939)[0] == 0
    auto_blocks = read_tap(ROOT / 'ulaview-auto.tap')
    assert len(auto_blocks) == 4
    auto_header, auto_basic, code_header, code_block = auto_blocks
    assert code_header[1] == 3 and code_header[2:12].strip() == b'ula-code'
    assert struct.unpack_from('<H', code_header, 14)[0] == 39936
    assert code_block[1:-1] == (ROOT / 'ulaview.bin').read_bytes()
    fast_lines = {}
    remaining = auto_basic[1:-1]
    while remaining:
        number = int.from_bytes(remaining[:2], 'big')
        length = int.from_bytes(remaining[2:4], 'little')
        fast_lines[number], remaining = remaining[4:4+length], remaining[4+length:]
    assert fast_lines[30].startswith(b'\xef') and b'ula-code' in fast_lines[30]
    assert 42 not in fast_lines and not any(n >= 9000 for n in fast_lines)
    assert len(auto_basic) < 2200, 'Bundled reader must not carry a BASIC hex installer'
    for n in (50,110,160,170,215,500,520):
        assert fast_lines[n] == lines[n], 'Fast loader must preserve image loads and exit handling'
    print('PASS bundled viewer direct CODE load, no interpreted installer, unchanged display/exit flow')
    assert struct.unpack_from('<H', auto_header, 14)[0] == 10
    with ZipFile(ROOT / 'tspico-slideshow.zip') as archive:
        assert archive.read('ulapics/ulavpico.tap') == (ROOT / 'ulavpico.tap').read_bytes()
        assert archive.read('ulapics/ulademo.tap') == (ROOT / 'ulademo.tap').read_bytes()
    print('PASS packaged demonstration image')
    print('All viewer tests passed (ROM service stubbed; physical hardware untested).')


if __name__ == '__main__':
    main()
