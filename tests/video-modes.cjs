// Run with a current Node.js: node tests/video-modes.cjs
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const script = html.match(/<script type="module">([\s\S]*?)<\/script>/)[1];
new vm.Script(script); // Includes the complete app, not just extracted helpers.
// A stale embedded reader could pass export-layout checks but ship old code.
const embeddedReader = Buffer.from(script.match(/const ULAVIEW_TAP_BASE64 = "([^"]+)"/)[1], 'base64');
assert.deepEqual(embeddedReader, fs.readFileSync(path.join(__dirname, '..', 'viewer', 'ulaview-auto.tap')));
assert.equal(embeddedReader.readUInt16LE(16), 10, 'Bundled viewer must autostart at line 10');
const core = script.slice(script.indexOf('const PALETTE_NORMAL'), script.indexOf('const palettes = {};'));
const ctx = vm.createContext({console, performance, atob: s => Buffer.from(s, "base64").toString("binary")});
vm.runInContext(core, ctx);
vm.runInContext(script.slice(script.indexOf("function makeTapPair("), script.indexOf("function getActiveOutputState(")), ctx);
vm.runInContext(`
function ensureBlockGrid(_, rows, cols) { return Array.from({length: rows}, () => Array(cols)); }
function pipelineIsCurrent() { return true; }
function pipelineSchedule(fn, id) { fn(id); }
function pipelineStageDitherQuantizedBlocks() {}
`, ctx);
function run(code) { return vm.runInContext(code, ctx); }
function plain(value) { return JSON.parse(JSON.stringify(value)); }
const fixtureDir = path.join(__dirname, '..', 'viewer', '.build', 'fixtures');
fs.mkdirSync(fixtureDir, {recursive:true});
assert.deepEqual(plain(run('ulaPalette[0]')), [0,0,0]);
assert.deepEqual(plain(run('ulaPalette[255]')), [255,255,255]);
assert.deepEqual(plain(run('[0,1,2,3].map(c => ulaPalette[c][2])')), [0,109,182,255]);
assert.equal(run('new Set(ulaPalette.map(c => c.join())).size'), 256);
assert.deepEqual(plain(run('ulaPresetCodes("gray").map(c => ulaPalette[c])')), [[0,0,0],[109,109,109],[182,182,182],[255,255,255]]);
for (const preset of ['red','green','blue']) assert.equal(run(`ulaPresetCodes('${preset}').length`), preset === 'blue' ? 4 : 8);
assert.throws(() => run('parseUlaCustom("[256]", 1)'));
assert.throws(() => run('parseUlaCustom("[1.5]", 1)'));
assert.throws(() => run('parseUlaCustom("[0]", 64)'));
run('var conversionPipelineState;');
// Decode every exported pixel independently, including all four ULA banks.
for (const mode of ['ula-standard','ula-ecm','ula-hires','ula-attr','pv-attr','pv-quad']) {
  run(`
    var mode = '${mode}', cfg = modes[mode];
    var regs = Array.from({length: mode === 'pv-quad' ? 4 : 64}, (_, i) => mode === 'pv-quad' ? [0,109,182,255][i] : (i*37)&255);
    var attrs = new Uint8Array((cfg.w/cfg.blockW)*(192/cfg.blockH));
    for (let i=0;i<attrs.length;i++) attrs[i] = mode === 'ula-hires' ? 56 : mode === 'pv-attr' ? i&127 : i&255;
    var pixels = new Uint8Array(cfg.w*192*3);
    for (let y=0;y<192;y++) for (let x=0;x<cfg.w;x++) {
      const attr=attrs[Math.floor(y/cfg.blockH)*(cfg.w/cfg.blockW)+Math.floor(x/cfg.blockW)];
      const ink=(x+y)%2 === 0, base=(attr>>6)*16;
      const rgb=mode === 'pv-quad' ? ulaPalette[regs[x%4]] : mode === 'pv-attr' ?
        ((attr&64) ? PALETTE_TS_BRIGHT : PALETTE_NORMAL)[ink ? attr&7 : (attr>>3)&7] :
        ulaPalette[regs[base+(ink ? attr&7 : 8+((attr>>3)&7))]];
      pixels.set(rgb,(y*cfg.w+x)*3);
    }
    var output=generateVideoOutput(mode,pixels,attrs,{ulaRegisters:regs,atariRegs:regs});
    var decoded=new Uint8Array(pixels.length);
    for(let y=0;y<192;y++) for(let x=0;x<cfg.w;x++) {
      const col=x>>3, bank=cfg.w===512 ? col&1 : 0, column=cfg.w===512 ? col>>1 : col;
      const bytes=output.blocks[bank].data, offset=videoBitmapOffset(y)+column;
      let rgb;
      if(mode==='pv-quad') {
        const value=output.blocks[(x&7)>>2].data[y*32+col];
        rgb=ulaPalette[regs[(value>>(6-2*(x&3)))&3]];
      } else {
        const attr=mode==='ula-hires' ? 56 : mode==='ula-ecm' ? output.blocks[1].data[offset] : bytes[6144+(y>>3)*32+column];
        const ink=!!(bytes[offset]&(128>>(x&7)));
        rgb=mode==='pv-attr' ? ((attr&64) ? PALETTE_TS_BRIGHT : PALETTE_NORMAL)[ink ? attr&7 : (attr>>3)&7] :
          ulaPalette[regs[(attr>>6)*16+(ink ? attr&7 : 8+((attr>>3)&7))]];
      }
      decoded.set(rgb,(y*cfg.w+x)*3);
    }
  `);
  assert.equal(run('decoded.every((v,i) => v === pixels[i])'), true, mode+' pixel round trip');
  const sizes = {'ula-standard':6976,'ula-ecm':12352,'ula-hires':12352,'ula-attr':13888,'pv-attr':13824,'pv-quad':12292};
  assert.equal(run('output.bytes.length'), sizes[mode], mode+' byte length');
  assert.equal(run('output.blocks.at(-1).addr'), 40960);
  assert.equal(run('output.blocks.at(-1).name'), 'ula-pal');
  assert.equal(run('output.blocks.at(-1).data.length'), 80);
  assert.equal(run('output.blocks[0].addr'), 41040);
  run('var viewerData=generateUlaViewerImage(mode,pixels,attrs,{ulaRegisters:regs,atariRegs:regs},3);');
  const viewerData=Buffer.from(run('Array.from(viewerData)'));
  assert.equal(viewerData.subarray(0,5).toString('hex'),'554c415602');
  assert.equal(viewerData[7],3);
  assert.equal(viewerData.length, 80+run('output.blocks.slice(0,-1).reduce((n,b)=>n+b.data.length,0)'));
  const sum=viewerData.subarray(16).reduce((n,b)=>(n+b)&65535,0);
  assert.equal(viewerData.readUInt16LE(14),sum);
  fs.writeFileSync(path.join(fixtureDir,mode+'.ulav'),viewerData);
  run('var tapBlocks = [{data:viewerData.slice(0,80),addr:40960,name:"ula-pal"}, ...output.blocks.slice(0,-1)]; var dataTape = generateTap(tapBlocks);');
  fs.writeFileSync(path.join(fixtureDir,mode+'.tap'),Buffer.from(run('Array.from(dataTape)')));
  fs.writeFileSync(path.join(fixtureDir,mode+'-bundled.tap'),Buffer.from(run('Array.from(bundleUlaViewerTape(dataTape))')));
  fs.writeFileSync(path.join(fixtureDir,mode+'.json'),JSON.stringify(plain(run('({screens:output.blocks.slice(0,-1).map(b=>Array.from(b.data)),registers:mode === "pv-attr" ? [] : regs,port:cfg.port,flags:mode === "pv-quad" ? 2 : mode === "pv-attr" ? 0 : 1})'))));
}
// The block search must choose bank 3 and respect separate ink/paper halves.
run(`
  var regs = Array(64).fill(0); regs[48]=28; regs[56]=224;
  var work = new Float32Array(256*192*3);
  for(let i=0;i<256*192;i++) work.set(ulaPalette[i&1 ? 224 : 28],i*3);
  conversionPipelineState={mode:'ula-ecm',modeCfg:modes['ula-ecm'],screenWidth:256,
    ulaPreset:'custom',ulaCustom:JSON.stringify(regs),work,palettes:[ulaPalette],colorMasks:[new Uint8Array(256).fill(1)]};
  startUlaQuantize(1,new Float32Array(work.length));
`);
assert.equal(run('conversionPipelineState.quantizeWork.attrs.every(a => a === 192)'), true);
// Black borders reserve PAPER 0; opting into palette borders preserves custom registers.
for (const paletteBorder of [false, true]) {
  run(`
    var customRegs=Array.from({length:64},(_,i)=>i+1);
    conversionPipelineState={mode:'ula-ecm',modeCfg:{...modes['ula-ecm'],w:8},screenWidth:8,
      ulaPreset:'custom',ulaCustom:JSON.stringify(customRegs),ulaPaletteBorder:${paletteBorder},
      work:new Float32Array(8*192*3),palettes:[ulaPalette]};
    startUlaQuantize(1,new Float32Array(8*192*3));
  `);
  assert.equal(run('conversionPipelineState.quantizeWork.modeMeta.ulaRegisters[8]'), paletteBorder ? 9 : 0);
  assert.equal(run('conversionPipelineState.quantizeWork.modeMeta.paletteBorder'), paletteBorder);
}
run(`
  var customRegs=Array(64).fill(0);customRegs[15]=255;
  conversionPipelineState={mode:'ula-hires',modeCfg:modes['ula-hires'],screenWidth:512,
    ulaPreset:'custom',ulaCustom:JSON.stringify(customRegs),ulaPaletteBorder:false,
    work:new Float32Array(512*192*3),palettes:[ulaPalette]};
  startUlaQuantize(1,new Float32Array(512*192*3));
`);
assert.equal(run('conversionPipelineState.quantizeWork.modeMeta.ulaRegisters[15]'),0);
assert.equal(run('conversionPipelineState.quantizeWork.modeMeta.ulaRegisters[0]'),255);
// Presets remap luminance, and stay within their hardware channel levels.
for (const preset of ['gray','red','green','blue']) {
  run(`
    conversionPipelineState={ulaPreset:'${preset}',mode:'ula-ecm',work:new Float32Array([255,0,0,0,0,255]),colorMasks:[new Uint8Array(256).fill(1)]};
    prepareUlaSource(conversionPipelineState);
    var chosen=selectUlaColors(conversionPipelineState.work,ulaPalette,conversionPipelineState.colorMasks[0],64);
  `);
  assert.equal(run(`chosen.every(c => ulaPresetCodes('${preset}').includes(c))`), true);
}
console.log('PASS: syntax, DAC levels, palette validation, six full-screen binary round trips, bank search, shading presets');
