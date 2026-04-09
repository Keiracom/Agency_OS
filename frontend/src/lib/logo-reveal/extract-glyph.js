/**
 * extract-glyph.js — Run ONCE to extract Playfair Display 900 italic "O"
 *
 * Usage:
 *   node frontend/src/lib/logo-reveal/extract-glyph.js
 *
 * Outputs the SVG path string for the "O" glyph at 200-unit em-square scale.
 * Paste the result into index.js as O_GLYPH_PATH.
 *
 * Prerequisites:
 *   npm install opentype.js node-fetch --save-dev
 *
 * The font file (Playfair_Display/PlayfairDisplay-BlackItalic.ttf) must be
 * present in public/fonts/ or downloaded from Google Fonts.
 * Weight 900 = "Black" in Playfair Display naming.
 */

const fs = require('fs');
const path = require('path');

// Try to load opentype.js
let opentype;
try {
  opentype = require('opentype.js');
} catch (e) {
  console.error('opentype.js not installed. Run: npm install opentype.js');
  process.exit(1);
}

// Font paths to try (in order of preference)
const FONT_CANDIDATES = [
  path.join(__dirname, '../../../../public/fonts/PlayfairDisplay-BlackItalic.ttf'),
  path.join(__dirname, '../../../../public/fonts/PlayfairDisplay-BoldItalic.ttf'),
  path.join(__dirname, '../../fonts/PlayfairDisplay-BlackItalic.ttf'),
  // Also try the system fonts if available
  '/usr/share/fonts/truetype/playfair/PlayfairDisplay-BlackItalic.ttf',
];

const EM_SQUARE = 200; // Output coordinate scale (matches SVG viewBox 200x200)
const CHAR = 'O';

function extractGlyph(fontPath) {
  console.log(`Loading font: ${fontPath}`);
  const font = opentype.loadSync(fontPath);
  const glyph = font.charToGlyph(CHAR);

  if (!glyph) {
    throw new Error(`Glyph for "${CHAR}" not found in font`);
  }

  const unitsPerEm = font.unitsPerEm;
  const scale = EM_SQUARE / unitsPerEm;

  // Convert glyph path to SVG path string
  // opentype.js path uses y-up convention; SVG uses y-down.
  // We flip Y: y_svg = EM_SQUARE - (y_font * scale)
  const path = glyph.getPath(0, EM_SQUARE, EM_SQUARE); // x=0, y=baseline, size=EM_SQUARE
  const svgPath = path.toSVG(4); // 4 decimal places

  // Extract just the d attribute
  const match = svgPath.match(/d="([^"]+)"/);
  if (!match) {
    throw new Error('Could not extract d attribute from SVG path');
  }

  return match[1];
}

// Main
let extracted = false;
for (const fontPath of FONT_CANDIDATES) {
  if (fs.existsSync(fontPath)) {
    try {
      const d = extractGlyph(fontPath);
      console.log('\n✓ Extracted glyph path:\n');
      console.log(`const O_GLYPH_PATH = "${d}";\n`);

      // Append to a file for easy copy-paste
      const outputFile = path.join(__dirname, 'extracted-glyph.txt');
      fs.writeFileSync(outputFile, `// Playfair Display 900 Italic "O" — extracted ${new Date().toISOString()}\n// Font: ${fontPath}\nconst O_GLYPH_PATH = "${d}";\n`);
      console.log(`✓ Written to: ${outputFile}`);
      extracted = true;
      break;
    } catch (err) {
      console.error(`Failed for ${fontPath}: ${err.message}`);
    }
  }
}

if (!extracted) {
  console.error('\nNo font file found. Download Playfair Display Black Italic from Google Fonts:');
  console.error('https://fonts.google.com/specimen/Playfair+Display');
  console.error('\nPlace the .ttf file at:');
  console.error('  frontend/public/fonts/PlayfairDisplay-BlackItalic.ttf');
  console.error('\nThen re-run this script.\n');
  console.error('FALLBACK: The demo uses an approximated ellipse path that works well for animation purposes.');
  process.exit(1);
}
