const { chromium } = require('playwright');

async function captureCompetitorDashboard(competitor, searchQuery) {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  try {
    // Try G2 first for product screenshots
    const g2Url = `https://www.g2.com/products/${competitor}/reviews`;
    console.log(`Trying G2: ${g2Url}`);
    await page.goto(g2Url, { timeout: 30000 });
    await page.waitForTimeout(2000);
    
    const screenshotPath = `/home/elliotbot/clawd/competitive/screenshots/${competitor}-g2.png`;
    await page.screenshot({ path: screenshotPath, fullPage: false });
    console.log(`Saved: ${screenshotPath}`);
    
  } catch (e) {
    console.log(`G2 failed: ${e.message}`);
  }
  
  try {
    // Try YouTube search for demo videos
    const ytUrl = `https://www.youtube.com/results?search_query=${encodeURIComponent(searchQuery)}`;
    console.log(`Trying YouTube: ${ytUrl}`);
    await page.goto(ytUrl, { timeout: 30000 });
    await page.waitForTimeout(3000);
    
    const screenshotPath = `/home/elliotbot/clawd/competitive/screenshots/${competitor}-youtube.png`;
    await page.screenshot({ path: screenshotPath, fullPage: false });
    console.log(`Saved: ${screenshotPath}`);
    
    // Click on first video if available
    const firstVideo = await page.$('ytd-video-renderer a#thumbnail');
    if (firstVideo) {
      await firstVideo.click();
      await page.waitForTimeout(5000);
      
      const videoScreenshot = `/home/elliotbot/clawd/competitive/screenshots/${competitor}-demo.png`;
      await page.screenshot({ path: videoScreenshot, fullPage: false });
      console.log(`Saved demo: ${videoScreenshot}`);
    }
    
  } catch (e) {
    console.log(`YouTube failed: ${e.message}`);
  }
  
  await browser.close();
}

const competitors = [
  { name: 'artisan', query: 'artisan ai ava dashboard demo walkthrough' },
  { name: '11x', query: '11x ai alice dashboard demo' },
  { name: 'regie', query: 'regie ai dashboard demo' },
  { name: 'aisdr', query: 'aisdr dashboard demo' },
  { name: 'instantly', query: 'instantly ai dashboard demo walkthrough' },
];

(async () => {
  const fs = require('fs');
  fs.mkdirSync('/home/elliotbot/clawd/competitive/screenshots', { recursive: true });
  
  for (const c of competitors) {
    console.log(`\n=== Capturing ${c.name} ===`);
    await captureCompetitorDashboard(c.name, c.query);
  }
  console.log('\nDone!');
})();
