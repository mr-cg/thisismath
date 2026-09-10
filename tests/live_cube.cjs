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
    const textCanvas = document.createElement('canvas');
    textCanvas.width = 640; textCanvas.height = 360;
    const textCtx = textCanvas.getContext('2d');
    const textPixels = () => {
      textCtx.clearRect(0, 0, 640, 360);
      drawTextPlane(textCtx, 640, 360);
      return textCanvas.toDataURL();
    };
    state.textRx = 17; state.textRy = -23; state.textRz = 31;
    const originalText = textPixels();
    for (const angles of [[50, -40, 22], [-75, 75, -45], [0, 0, 0]]) {
      [state.pan, state.tilt, state.roll] = angles;
      check(textPixels() === originalText, 'Cube rotation changed text orientation');
    }
    state.textRz += 15;
    check(textPixels() !== originalText, 'Absolute text rotation did not change text');
    $('resetBtn').click(); flush();
    let count = 0;
    for (const key of Object.keys(controls)) {
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
      ' sliders redraw before release; edge-on angles; PNG rendering.</pre>';
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
