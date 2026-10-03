// Reviewer-only syntax check. Does not execute or alter the product script.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const target = path.resolve(__dirname, '../../../step2_code/backend/src/campus_assistant/static/preview.html');
const html = fs.readFileSync(target, 'utf8');
const scripts = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)];
if (!scripts.length) throw new Error('No inline script found');
for (const [index, match] of scripts.entries()) {
  new vm.Script(match[1], { filename: `preview-inline-${index + 1}.js` });
}
console.log('JavaScript syntax OK');
