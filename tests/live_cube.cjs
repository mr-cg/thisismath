// Run with: node tests/live_cube.cjs [path-to-Chrome-or-Chromium]
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const {spawnSync} = require('node:child_process');
const assert = require('node:assert/strict');

const browser = process.argv[2] || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'cube-test-'));
const checks = `
  const check = (condition, message) => { if (!condition) throw Error(message); };
  const flush = () => { while (window.framesToTest.length) window.framesToTest.shift()(); };
  try {
    flush();
    const panel = document.querySelector('.panel');
    const previewBeforeScroll = preview.getBoundingClientRect();
    const panelBounds = panel.getBoundingClientRect();
    check(Math.abs(panelBounds.height - previewBeforeScroll.height) < 1,
      'Slider menu and cube preview must have the same height');
    if (innerWidth > 850) {
      check(Math.abs(panelBounds.top - previewBeforeScroll.top) < 1 &&
        Math.abs(panelBounds.bottom - previewBeforeScroll.bottom) < 1,
        'Menu and preview must align at both top and bottom');
    }
    check(panel.scrollHeight > panel.clientHeight, 'Menu must have its own scroll area');
    panel.scrollTop = panel.scrollHeight;
    check(panel.scrollTop > 0, 'Menu did not scroll');
    const previewAfterScroll = preview.getBoundingClientRect();
    check(previewBeforeScroll.top === previewAfterScroll.top, 'Menu scrolling moved preview');
    check(previewAfterScroll.top >= 0 && previewAfterScroll.bottom <= innerHeight,
      'Preview extends outside the visible viewport');
    check(document.documentElement.scrollHeight <= innerHeight, 'Page scrolls instead of menu');
    panel.scrollTop = 0;
    const textCanvas = document.createElement('canvas');
    textCanvas.width = 640; textCanvas.height = 360;
    const textCtx = textCanvas.getContext('2d');
    const textPixels = () => {
      textCtx.clearRect(0, 0, 640, 360);
      drawText(textCtx, 640, 360);
      return textCanvas.toDataURL();
    };
    state.textRx = 17; state.textRy = -23; state.textRz = 31;
    state.textTx = 0.3; state.textTy = -0.2; state.textTz = 0.4;
    const center = projectLocal([0, 0, 0], rotation(17, -23, 31), 640, 360,
      [state.textTx, state.textTy, state.textTz]);
    const unrotatedCenter = projectLocal([0, 0, 0], rotation(0, 0, 0), 640, 360,
      [state.textTx, state.textTy, state.textTz]);
    check(JSON.stringify(center) === JSON.stringify(unrotatedCenter), 'Rotation changed translation axes');
    check(center.x > 320 && center.y > 180 && center.z === 5.4, 'Translation direction is incorrect');
    const originalText = textPixels();
    for (const angles of [[50, -40, 22], [-75, 75, -45], [0, 0, 0]]) {
      [state.pan, state.tilt, state.roll] = angles;
      check(textPixels() === originalText, 'Cube rotation changed text orientation');
    }
    state.textRz += 15;
    check(textPixels() !== originalText, 'Absolute text rotation did not change text');
    $('resetBtn').click(); flush();
    const independent = textPixels();
    $('followCube').click(); flush();
    check(state.followCube && textPixels() !== independent, 'Follow toggle did not attach text to cube');
    const attached = textPixels();
    state.pan += 30;
    check(textPixels() !== attached, 'Attached text did not follow cube rotation');
    $('followCube').click(); flush();
    check(textPixels() === independent, 'Turning follow off did not restore absolute text');
    state.textTx = 0.5;
    $('followCube').click(); flush();
    const expectedPosition = matVec(rotation(state.tilt, state.pan, state.roll), [0.5,0,0]);
    check(JSON.stringify(textTransform().position) === JSON.stringify(expectedPosition), 'Attached text position did not orbit cube');
    $('resetBtn').click(); flush();
    state.textRy = 35;
    const flat = textPixels();
    $('text3d').click(); flush();
    check(state.text3d && !$('depthControl').hidden, '3D toggle did not expose thickness');
    check(textPixels() !== flat, '3D text did not add visible sides');
    state.textRy = 90;
    textPixels();
    check(textCtx.getImageData(0,0,640,360).data.some((value, i) => i%4 === 3 && value > 0), 'Edge-on 3D text has no visible thickness');
    state.textRy = 35;
    $('text3d').click(); flush();
    check(textPixels() === flat, 'Turning 3D off did not restore flat text');
    $('resetBtn').click(); flush();
    check(!state.text3d && !state.followCube && $('depthControl').hidden, 'Reset did not clear toggles');
    let count = 0;
    for (const key of Object.keys(controls)) {
      if (key === 'textDepth') { $('text3d').click(); state.textRy = 35; scheduleRender(); flush(); }
      const input = $(controls[key][0]);
      const before = preview.toDataURL();
      input.dispatchEvent(new PointerEvent('pointerdown', {buttons: 1}));
      input.value = Number(input.value) + (Number(input.max) - Number(input.min)) / 8;
      // Deliberately no change or pointerup event: the preview must already update.
      input.dispatchEvent(new Event('input', {bubbles: true}));
      flush();
      check(state[key] === Number(input.value), key + ' did not update on input');
      check(preview.toDataURL() !== before, key + ' did not redraw before release');
      count++;
      $('resetBtn').click(); flush();
    }
    state.textRx = 90; textPixels();
    state.textRx = 0; state.textRy = -90; textPixels();
    const exported = document.createElement('canvas');
    exported.width = 800; exported.height = 600;
    renderTo(exported.getContext('2d'), 800, 600);
    check(exported.toDataURL().startsWith('data:image/png;base64,'), 'PNG render failed');
    document.body.innerHTML = '<pre>PASS: independent text rotation; ' + count +
      ' sliders redraw before release; follow toggle; 3D thickness and edge-on sides; reset; fixed-axis translation; independent menu scrolling; PNG rendering.</pre>';
  } catch (error) {
    document.body.innerHTML = '<pre>FAIL: ' + error.message + '</pre>';
  }
`;
try {
  let html = fs.readFileSync(path.join(__dirname, '..', 'live_cube.html'), 'utf8');
  html = html.replace('<script>', '<script>window.framesToTest=[]; window.requestAnimationFrame=fn=>window.framesToTest.push(fn);</script><script>');
  html = html.replace('})();\n</script>', checks + '\n})();\n</script>');
  // Accommodate Windows checkouts with CRLF line endings.
  if (!html.includes('PASS: independent')) {
    html = html.replace('})();\r\n</script>', checks + '\n})();\n</script>');
  }
  const file = path.join(directory, 'test.html');
  fs.writeFileSync(file, html);
  const result = spawnSync(browser, [
    '--headless', '--no-sandbox', '--disable-gpu', '--no-first-run',
    '--window-size=' + (process.argv[3] || '1440,900'),
    '--user-data-dir=' + path.join(directory, 'profile'), '--dump-dom',
    'file:///' + file.replaceAll('\\', '/'),
  ], {encoding: 'utf8', timeout: 60000, maxBuffer: 1024 * 1024});
  assert.equal(result.status, 0, result.error?.message || result.stderr);
  const verdict = result.stdout.match(/<pre>(.*?)<\/pre>/s)?.[1];
  assert.ok(verdict?.startsWith('PASS:'), verdict || result.stdout);
  console.log(verdict);
} finally {
  fs.rmSync(directory, {recursive: true, force: true, maxRetries: 5});
}
