/**
 * Agency OS Dashboard Manuals Generator
 * Converts admin-manual.html and user-manual.html to PDF using Puppeteer
 *
 * Usage:
 *   node generate-manuals.js          - Generate both manuals
 *   node generate-manuals.js admin    - Generate admin manual only
 *   node generate-manuals.js user     - Generate user manual only
 */

const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

const manuals = {
  admin: {
    html: 'admin-manual.html',
    pdf: 'ADMIN_DASHBOARD_MANUAL.pdf',
    title: 'Agency OS Admin Manual v3.0',
    headerTitle: 'Agency OS Admin Dashboard Manual v3.0'
  },
  user: {
    html: 'user-manual.html',
    pdf: 'USER_DASHBOARD_MANUAL.pdf',
    title: 'Agency OS User Manual v3.0',
    headerTitle: 'Agency OS User Dashboard Manual v3.0'
  }
};

async function generatePDF(manualType) {
  const manual = manuals[manualType];
  if (!manual) {
    console.error(`Unknown manual type: ${manualType}`);
    return false;
  }

  const htmlPath = path.join(__dirname, manual.html);
  const pdfPath = path.join(__dirname, manual.pdf);

  // Check if HTML file exists
  if (!fs.existsSync(htmlPath)) {
    console.error(`Error: ${manual.html} not found!`);
    return false;
  }

  console.log(`\n[${manualType.toUpperCase()}] Starting PDF generation...`);
  console.log(`  Source: ${manual.html}`);
  console.log(`  Output: ${manual.pdf}`);

  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  try {
    const page = await browser.newPage();

    console.log(`  Loading HTML file...`);
    const htmlContent = fs.readFileSync(htmlPath, 'utf8');
    await page.setContent(htmlContent, {
      waitUntil: 'networkidle0'
    });

    console.log(`  Generating PDF...`);
    await page.pdf({
      path: pdfPath,
      format: 'A4',
      printBackground: true,
      margin: {
        top: '25mm',
        right: '15mm',
        bottom: '25mm',
        left: '15mm'
      },
      displayHeaderFooter: true,
      headerTemplate: `
        <div style="width: 100%; font-size: 9px; padding: 0 15mm; color: #6b7280; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
          <span style="float: left;">${manual.headerTitle}</span>
          <span style="float: right;">December 2025</span>
        </div>
      `,
      footerTemplate: `
        <div style="width: 100%; font-size: 9px; padding: 0 15mm; color: #6b7280; text-align: center; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
          Page <span class="pageNumber"></span> of <span class="totalPages"></span>
        </div>
      `
    });

    // Get file size
    const stats = fs.statSync(pdfPath);
    const fileSizeKB = Math.round(stats.size / 1024);
    console.log(`  SUCCESS: ${pdfPath} (${fileSizeKB} KB)`);

    return true;

  } catch (error) {
    console.error(`  Error generating ${manual.pdf}:`, error.message);
    return false;
  } finally {
    await browser.close();
  }
}

async function main() {
  console.log('========================================');
  console.log('Agency OS Documentation Generator');
  console.log('========================================');

  const args = process.argv.slice(2);
  let targets = [];

  if (args.length === 0) {
    // Generate both manuals
    targets = ['admin', 'user'];
  } else if (args[0] === 'admin' || args[0] === 'user') {
    targets = [args[0]];
  } else {
    console.error('Usage: node generate-manuals.js [admin|user]');
    console.error('  No argument: generates both manuals');
    console.error('  admin: generates admin manual only');
    console.error('  user: generates user manual only');
    process.exit(1);
  }

  console.log(`\nTargets: ${targets.join(', ')}`);
  console.log(`Date: ${new Date().toISOString()}`);

  let successCount = 0;
  let failCount = 0;

  for (const target of targets) {
    const success = await generatePDF(target);
    if (success) {
      successCount++;
    } else {
      failCount++;
    }
  }

  console.log('\n========================================');
  console.log('Generation Complete');
  console.log('========================================');
  console.log(`  Successful: ${successCount}`);
  console.log(`  Failed: ${failCount}`);

  if (successCount > 0) {
    console.log('\nGenerated files:');
    for (const target of targets) {
      const pdfPath = path.join(__dirname, manuals[target].pdf);
      if (fs.existsSync(pdfPath)) {
        const stats = fs.statSync(pdfPath);
        console.log(`  - ${manuals[target].pdf} (${Math.round(stats.size / 1024)} KB)`);
      }
    }
  }

  if (failCount > 0) {
    process.exit(1);
  }
}

// Run the generator
main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
