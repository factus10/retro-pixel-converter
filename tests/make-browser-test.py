from pathlib import Path

root = Path(__file__).resolve().parent.parent
source = (root / "index.html").read_text(encoding="utf-8")
harness = r'''
(async () => {
 const report = text => { const p=document.createElement('pre'); p.className='test-report'; p.textContent=text; document.body.appendChild(p); };
 try {
 const c=document.createElement('canvas'); c.width=256;c.height=192;
 const cx=c.getContext('2d'); const g=cx.createLinearGradient(0,0,256,192);g.addColorStop(0,'#001040');g.addColorStop(.5,'#e03020');g.addColorStop(1,'#ffffff');cx.fillStyle=g;cx.fillRect(0,0,256,192);
 const data=await new Promise(resolve=>c.toBlob(resolve));
 const dt=new DataTransfer();dt.items.add(new File([data],'gradient.png',{type:'image/png'}));UI.fileInput.files=dt.files;UI.fileInput.dispatchEvent(new Event('change'));
 const wait=async()=>{ for(let i=0;i<3000;i++){ await new Promise(r=>setTimeout(r,20));if(conversionPipelineState.stage==='complete')return;if(conversionPipelineState.stage==='error')throw Error(UI.statusText.textContent); }throw Error('timeout: '+conversionPipelineState.stage+' '+UI.statusText.textContent); };
 await wait();
 cropRect={x:10,y:12,w:180,h:80};
 UI.lockAspect.checked=true;UI.lockAspect.dispatchEvent(new Event('change'));await wait();
 if(Math.abs(cropRect.w/cropRect.h-4/3)>1e-10 || Math.abs(cropRect.x+cropRect.w/2-100)>1e-10)throw Error('4:3 crop lock did not fit around the selection center');
 UI.fitCrop43.click();await wait();
 if(!cropAspectLocked || !UI.lockAspect.checked || cropRect.w!==256 || cropRect.h!==192)throw Error('Fit 4:3 did not restore the largest centered crop');
 const portraitCrop=fitCropToAspect({x:0,y:0,w:900,h:1600},900,1600);
 if(portraitCrop.w!==900 || portraitCrop.h!==675 || portraitCrop.y!==462.5)throw Error('Portrait 4:3 crop bounds');
 const cropProfile=getCurrentProfile();
 if(!cropProfile.lockAspect || Math.abs(cropProfile.cropRect.w/cropProfile.cropRect.h-4/3)>1e-10)throw Error('Crop profile did not retain 4:3 lock');
 report('PASS immediate 4:3 lock, Fit 4:3 button, portrait bounds and crop profile');
 for(const mode of ['ula-standard','ula-ecm','ula-hires','ula-attr','pv-attr','pv-quad','standard','ecm','sam-mode2']) {
  UI.displayMode.value=mode;UI.displayMode.dispatchEvent(new Event('input'));await wait();
  const state=buildBinaryExportData();if(!state.scrBytes.length)throw Error('Empty export '+mode);
  if(supportsUlaViewer(mode)) {
   if(UI.exportTap.disabled || UI.exportViewerRow.style.display==='none')throw Error('Viewer export unavailable '+mode);
   for(const bundle of [false,true]) {
    UI.bundleUlaViewer.checked=bundle;
    const originalDownload=downloadBlob;let captured;
    downloadBlob=(blob,name)=>{captured={blob,name};};
    try { UI.exportTap.click(); } finally { downloadBlob=originalDownload; }
    if(!captured || !captured.name.endsWith('.tap'))throw Error('TAP download missing '+mode);
    const data=new Uint8Array(await captured.blob.arrayBuffer());
    let offset=0;const files=[];
    while(offset<data.length){
     const length=data[offset]|(data[offset+1]<<8);offset+=2;
     const block=data.slice(offset,offset+length);offset+=length;
     if(block.reduce((a,b)=>a^b,0)!==0)throw Error('Bad TAP checksum');
     if(block[0]===0)files.push({type:block[1],name:String.fromCharCode(...block.slice(2,12)).trim(),start:block[14]|(block[15]<<8)});
    }
    const imageFiles=bundle?files.slice(2):files;
    if(bundle && (files[0].type!==0 || files[0].start!==10))throw Error('Bundled viewer not autostart');
    if(bundle && (files[1].type!==3 || files[1].name!=='ula-code' || files[1].start!==39936))throw Error('Missing direct viewer CODE load');
    if(imageFiles.some(f=>f.type!==3) || imageFiles[0].name!=='ula-pal' || imageFiles[1].name!=='ula-df1')throw Error('Wrong image files');
    if(imageFiles.length!==(mode==='ula-standard'?2:3))throw Error('Wrong file count');
    if(imageFiles.some(f=>f.name==='video-init'))throw Error('Image contains initializer code');
   }
   UI.bundleUlaViewer.checked=false;
   const originalDownload=downloadBlob;let pal;
   downloadBlob=(blob,name)=>{pal={blob,name};};
   try {UI.exportUlaPal.click();} finally {downloadBlob=originalDownload;}
   if(!pal || pal.name!=='ula-pal.bin' || pal.blob.size!==80)throw Error('Palette file download');
   const view=generateUlaViewerImage(mode,ensureStateSRGBPixels(state),state.attrs,state.modeMeta);
   if(view.length>13904)throw Error('Viewer image too large');
   if(view[7]!==0 || !state.modeCfg.fixedBlackBorder)throw Error('Default border is not black');
   if(mode.startsWith('ula-') && state.modeMeta.ulaRegisters[mode==='ula-hires'?15:8]!==0)throw Error('Black hardware palette slot missing');
  }
  report('PASS '+mode+' '+state.scrBytes.length+' bytes');
 }
 for(const preset of ['gray','green','red','blue']) {
  UI.displayMode.value='ula-ecm';UI.ulaPreset.value=preset;UI.displayMode.dispatchEvent(new Event('input'));await wait();
  const state=buildBinaryExportData();if(!state.modeMeta.ulaRegisters.every(c=>ulaPresetCodes(preset).includes(c)))throw Error('preset '+preset);
  report('PASS preset '+preset);
 }
 UI.ulaPreset.value='custom';UI.ulaCustom.value=JSON.stringify(Array.from({length:64},(_,i)=>(i*37)&255));
 UI.ulaBorder.value='palette';
 UI.ulaPreset.dispatchEvent(new Event('input'));await wait();
 const state=buildBinaryExportData();
 if(JSON.stringify(state.modeMeta.ulaRegisters)!==UI.ulaCustom.value)throw Error('custom palette changed');
 const profile=getCurrentProfile();if(profile.ulaCustom!==UI.ulaCustom.value || profile.ulaPreset!=='custom')throw Error('profile palette missing');
 const tape=generateTap(state.tapBlocks);
 for(let offset=0;offset<tape.length;){const length=tape[offset]|(tape[offset+1]<<8);offset+=2;let checksum=0;for(let i=0;i<length;i++)checksum^=tape[offset+i];if(checksum)throw Error('TAP checksum');offset+=length;}
 report('PASS fixed custom palette, profile serialization and TAP checksums');
 const reader=await fetch('../viewer/ulaview.tap');
 if(!reader.ok || (await reader.arrayBuffer()).byteLength<1000)throw Error('Reader download unavailable');
 report('PASS data-only/bundled TAP downloads, ula-pal.bin and reader asset');
 report('ALL BROWSER TESTS PASSED');
 } catch(e) { report('FAIL '+e.stack); }
})();
'''
(root / 'tests' / 'browser-harness.html').write_text(source.replace('</script>', harness + '</script>'), encoding='utf-8')
