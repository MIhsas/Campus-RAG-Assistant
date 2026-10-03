// Check inline JS syntax in static HTML files. Does not execute product code.
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const staticDir = path.resolve(__dirname, '../src/campus_assistant/static');
const files = fs.readdirSync(staticDir).filter(f => f.endsWith('.html'));

if (!files.length) {
  console.error('No HTML files found in ' + staticDir);
  process.exit(1);
}

let ok = 0;
for (const file of files) {
  const html = fs.readFileSync(path.join(staticDir, file), 'utf8');
  const scripts = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)];
  if (!scripts.length) {
    console.error(file + ': no inline script found');
    process.exit(1);
  }
  for (const [index, match] of scripts.entries()) {
    try {
      new vm.Script(match[1], { filename: file + '-inline-' + (index + 1) + '.js' });
    } catch (e) {
      console.error(file + ': ' + e.message);
      process.exit(1);
    }
  }
  ok++;
  console.log(file + ': syntax OK');
}
console.log('\nAll ' + ok + ' HTML files passed syntax check.');
