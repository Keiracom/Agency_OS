const { chromium } = require('playwright');

const ADMIN_PAGES = [
  { name: '01-command-center', path: '/admin', title: 'Command Center' },
  { name: '02-revenue', path: '/admin/revenue', title: 'Revenue Dashboard' },
  { name: '03-costs', path: '/admin/costs', title: 'Costs Overview' },
  { name: '04-costs-ai', path: '/admin/costs/ai', title: 'AI Costs' },
  { name: '05-costs-channels', path: '/admin/costs/channels', title: 'Channel Costs' },
  { name: '06-clients', path: '/admin/clients', title: 'Clients' },
  { name: '07-campaigns', path: '/admin/campaigns', title: 'Campaigns' },
  { name: '08-leads', path: '/admin/leads', title: 'Leads' },
  { name: '09-activity', path: '/admin/activity', title: 'Activity' },
  { name: '10-replies', path: '/admin/replies', title: 'Replies' },
  { name: '11-compliance', path: '/admin/compliance', title: 'Compliance' },
  { name: '12-compliance-bounces', path: '/admin/compliance/bounces', title: 'Bounces' },
  { name: '13-compliance-suppression', path: '/admin/compliance/suppression', title: 'Suppression' },
  { name: '14-system', path: '/admin/system', title: 'System' },
  { name: '15-system-errors', path: '/admin/system/errors', title: 'Errors' },
  { name: '16-system-queues', path: '/admin/system/queues', title: 'Queues' },
  { name: '17-system-rate-limits', path: '/admin/system/rate-limits', title: 'Rate Limits' },
  { name: '18-settings', path: '/admin/settings', title: 'Settings' },
  { name: '19-settings-users', path: '/admin/settings/users', title: 'Users' },
];

const BASE_URL = 'https://agency-os-liart.vercel.app';
const OUTPUT_DIR = 'C:/AI/Agency_OS/docs/screenshots';

async function captureScreenshots() {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  });
  const page = await context.newPage();

  console.log('Please log in manually in the browser window...');
  console.log('Navigate to: ' + BASE_URL + '/admin');
  console.log('After logging in, press Enter in this console to continue...');
  
  // Go to login page
  await page.goto(BASE_URL + '/login');
  
  // Wait for manual login - user needs to authenticate with Google
  const readline = require('readline');
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });

  await new Promise(resolve => {
    rl.question('Press Enter after you have logged in and can see /admin...', () => {
      rl.close();
      resolve();
    });
  });

  console.log('Starting screenshot capture...');

  for (const adminPage of ADMIN_PAGES) {
    const url = BASE_URL + adminPage.path;
    console.log(`Capturing: ${adminPage.title} (${adminPage.path})`);
    
    try {
      await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
      await page.waitForTimeout(2000); // Wait for animations
      
      await page.screenshot({
        path: `${OUTPUT_DIR}/${adminPage.name}.png`,
        fullPage: true
      });
      
      console.log(`  ✓ Saved: ${adminPage.name}.png`);
    } catch (error) {
      console.log(`  ✗ Failed: ${error.message}`);
    }
  }

  console.log('\\nScreenshot capture complete!');
  console.log(`Screenshots saved to: ${OUTPUT_DIR}`);
  
  await browser.close();
}

captureScreenshots().catch(console.error);
