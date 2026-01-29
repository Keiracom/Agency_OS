const { chromium } = require('playwright');

async function captureMarketingSite(name, urls) {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  for (let i = 0; i < urls.length; i++) {
    try {
      console.log(`  Visiting: ${urls[i]}`);
      await page.goto(urls[i], { timeout: 30000, waitUntil: 'networkidle' });
      await page.waitForTimeout(2000);
      
      // Scroll down to load lazy content
      await page.evaluate(() => window.scrollBy(0, 500));
      await page.waitForTimeout(1000);
      
      const screenshotPath = `/home/elliotbot/clawd/competitive/screenshots/${name}-site-${i+1}.png`;
      await page.screenshot({ path: screenshotPath, fullPage: false });
      console.log(`  Saved: ${screenshotPath}`);
      
    } catch (e) {
      console.log(`  Failed: ${e.message}`);
    }
  }
  
  await browser.close();
}

const competitors = [
  { 
    name: 'artisan', 
    urls: [
      'https://www.artisan.co/ava',
      'https://www.artisan.co/features',
    ]
  },
  { 
    name: '11x', 
    urls: [
      'https://www.11x.ai/worker/alice',
      'https://www.11x.ai/platform',
    ]
  },
  { 
    name: 'regie', 
    urls: [
      'https://www.regie.ai/product',
      'https://www.regie.ai/platform',
    ]
  },
  { 
    name: 'aisdr', 
    urls: [
      'https://aisdr.com/platform/',
      'https://aisdr.com/features/',
    ]
  },
  { 
    name: 'instantly', 
    urls: [
      'https://instantly.ai/features',
      'https://instantly.ai/dashboard',
    ]
  },
];

(async () => {
  for (const c of competitors) {
    console.log(`\n=== ${c.name.toUpperCase()} ===`);
    await captureMarketingSite(c.name, c.urls);
  }
  console.log('\nDone!');
})();
