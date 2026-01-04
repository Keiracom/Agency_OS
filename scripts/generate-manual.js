/**
 * Agency OS Admin Dashboard Manual Generator
 * Converts manual.html to ADMIN_DASHBOARD_MANUAL.pdf using Puppeteer
 */

const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

async function generatePDF() {
  console.log('Starting PDF generation...');

  const htmlPath = path.join(__dirname, 'manual.html');
  const pdfPath = path.join(__dirname, 'ADMIN_DASHBOARD_MANUAL.pdf');

  // Check if HTML file exists
  if (!fs.existsSync(htmlPath)) {
    console.error('Error: manual.html not found!');
    process.exit(1);
  }

  console.log('Launching browser...');
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  try {
    const page = await browser.newPage();

    console.log('Loading HTML file...');
    const htmlContent = fs.readFileSync(htmlPath, 'utf8');
    await page.setContent(htmlContent, {
      waitUntil: 'networkidle0'
    });

    console.log('Generating PDF...');
    await page.pdf({
      path: pdfPath,
      format: 'A4',
      printBackground: true,
      margin: {
        top: '20mm',
        right: '15mm',
        bottom: '20mm',
        left: '15mm'
      },
      displayHeaderFooter: true,
      headerTemplate: `
        <div style="width: 100%; font-size: 9px; padding: 5px 15mm; color: #6b7280;">
          <span style="float: left;">Agency OS Admin Manual v3.0</span>
          <span style="float: right;">December 2025</span>
        </div>
      `,
      footerTemplate: `
        <div style="width: 100%; font-size: 9px; padding: 5px 15mm; color: #6b7280; text-align: center;">
          Page <span class="pageNumber"></span> of <span class="totalPages"></span>
        </div>
      `
    });

    console.log(`PDF generated successfully: ${pdfPath}`);

    // Get file size
    const stats = fs.statSync(pdfPath);
    const fileSizeKB = Math.round(stats.size / 1024);
    console.log(`File size: ${fileSizeKB} KB`);

  } catch (error) {
    console.error('Error generating PDF:', error);
    process.exit(1);
  } finally {
    await browser.close();
  }
}

// Run the generator
generatePDF().then(() => {
  console.log('Done!');
}).catch(err => {
  console.error('Failed:', err);
  process.exit(1);
});
