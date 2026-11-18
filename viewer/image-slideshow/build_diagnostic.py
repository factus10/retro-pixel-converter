"""Build a one-image diagnostic with visible loading-stage border colors."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from build import tape_file, timex_tokens

source = (ROOT / 'ulavpico.bas').read_text(encoding='ascii')
source = source.replace('LET LP=1', 'LET LP=0', 1)  # diagnostic stays a single pass
source = source[:source.index('9500 REM')]
source += '9500 REM SINGLE MODE 7 TEST\n9510 DATA "upainthi.tap","*"\n'
for line, extra in [
    ('110 RANDOMIZE USR 39936', '115 OUT 48955,64: OUT 65339,0: BORDER 1'),
    ('120 LET Q$="tpi:"+P$: LOAD Q$', '125 BORDER 2'),
    ('140 LOAD "ula-pal" CODE 40960,80', '145 BORDER 3'),
    ('160 IF V<>0 THEN GO TO 500', '165 BORDER 4'),
    ('190 LOAD "ula-df1" CODE 41040,L', '195 BORDER 5'),
    ('200 IF N<>0 THEN LOAD "ula-df2" CODE 41040+L,N', '203 BORDER 6'),
]:
    assert line in source
    source = source.replace(line, line + '\n' + extra, 1)
source = source.replace('330 STOP', '325 PRINT "MODE 7 TEST FINISHED"\n330 STOP', 1)
(ROOT / 'udiag.bas').write_text(source, encoding='ascii')
tokens = ROOT.parent / '.build/udiag-tokens.bas'
raw = ROOT.parent / '.build/udiag.basic'
tokens.write_text(timex_tokens(source), encoding='ascii')
zmakebas = ROOT.parent.parent.parent / 'zmakebas/zmakebas.exe'
subprocess.run([str(zmakebas), '-r', '-o', str(raw), str(tokens)], check=True)
basic = raw.read_bytes()
assert len(basic) <= 6000
(ROOT / 'udiag.tap').write_bytes(tape_file(basic, 'udiag', 0, 32768, len(basic)))
print('Built udiag.tap: blue=mounting, red=palette load, magenta=metadata check, green=DF1 load, cyan=DF2 load, yellow=display call')
