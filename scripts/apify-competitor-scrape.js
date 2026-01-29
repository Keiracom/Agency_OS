const { ApifyClient } = require('apify-client');
const fs = require('fs');

const client = new ApifyClient({
  token: process.env.APIFY_API_KEY,
});

// YouTube video scraper to get demo videos
async function scrapeYouTubeSearch(query) {
  console.log(`Scraping YouTube for: ${query}`);
  
  const run = await client.actor('clockworks/youtube-scraper').call({
    searchKeywords: [query],
    maxResults: 5,
    proxyConfiguration: {
      useApifyProxy: true,
      apifyProxyGroups: ['RESIDENTIAL'],
    },
  });
  
  const { items } = await client.dataset(run.defaultDatasetId).listItems();
  return items;
}

// Web scraper for G2 reviews with screenshots
async function scrapeG2(productUrl) {
  console.log(`Scraping G2: ${productUrl}`);
  
  const run = await client.actor('apify/web-scraper').call({
    startUrls: [{ url: productUrl }],
    proxyConfiguration: {
      useApifyProxy: true,
      apifyProxyGroups: ['RESIDENTIAL'],
    },
    pageFunction: async function pageFunction(context) {
      const { page, request } = context;
      await page.waitForTimeout(3000);
      
      // Take screenshot
      const screenshot = await page.screenshot({ fullPage: false });
      
      // Get review screenshots if any
      const screenshots = await page.$$eval('img[src*="screenshot"], img[src*="product-screenshot"]', imgs => 
        imgs.map(img => img.src).slice(0, 5)
      );
      
      return {
        url: request.url,
        title: await page.title(),
        screenshots,
        pageScreenshot: screenshot.toString('base64'),
      };
    },
    maxConcurrency: 1,
  });
  
  const { items } = await client.dataset(run.defaultDatasetId).listItems();
  return items;
}

// Generic website scraper with screenshots
async function scrapeWebsite(url, name) {
  console.log(`Scraping website: ${url}`);
  
  const run = await client.actor('apify/puppeteer-scraper').call({
    startUrls: [{ url }],
    proxyConfiguration: {
      useApifyProxy: true,
      apifyProxyGroups: ['RESIDENTIAL'],
    },
    pageFunction: async function pageFunction(context) {
      const { page, request, saveSnapshot } = context;
      
      // Wait for page to load
      await page.waitForTimeout(5000);
      
      // Scroll to load lazy content
      await page.evaluate(() => {
        window.scrollBy(0, 500);
      });
      await page.waitForTimeout(2000);
      
      // Take screenshot
      await saveSnapshot({ key: request.userData.name || 'page', screenshotQuality: 90 });
      
      // Get all images that might be product screenshots
      const images = await page.$$eval('img', imgs => 
        imgs.map(img => ({
          src: img.src,
          alt: img.alt,
          width: img.width,
          height: img.height,
        })).filter(img => img.width > 400 && img.height > 300)
      );
      
      return {
        url: request.url,
        title: await page.title(),
        images,
      };
    },
    maxConcurrency: 1,
  });
  
  const { items } = await client.dataset(run.defaultDatasetId).listItems();
  
  // Get key-value store for screenshots
  const kvStore = await client.keyValueStore(run.defaultKeyValueStoreId);
  const keys = await kvStore.listKeys();
  
  for (const key of keys.items) {
    if (key.key.includes('screenshot')) {
      const record = await kvStore.getRecord(key.key);
      const buffer = Buffer.from(record.value);
      fs.writeFileSync(`/home/elliotbot/clawd/competitive/screenshots/${name}-apify.png`, buffer);
      console.log(`  Saved screenshot: ${name}-apify.png`);
    }
  }
  
  return items;
}

const competitors = [
  { name: 'artisan', g2: 'https://www.g2.com/products/artisan-ai/reviews', youtube: 'artisan ai ava demo dashboard' },
  { name: '11x', g2: 'https://www.g2.com/products/11x/reviews', youtube: '11x ai alice demo dashboard' },
  { name: 'regie', g2: 'https://www.g2.com/products/regie-ai/reviews', youtube: 'regie ai demo dashboard' },
  { name: 'aisdr', g2: 'https://www.g2.com/products/aisdr/reviews', youtube: 'aisdr demo dashboard walkthrough' },
  { name: 'instantly', g2: 'https://www.g2.com/products/instantly/reviews', youtube: 'instantly ai demo dashboard' },
];

(async () => {
  console.log('Starting Apify scrape with residential proxies...\n');
  
  for (const c of competitors) {
    console.log(`\n=== ${c.name.toUpperCase()} ===`);
    
    try {
      // Try G2 first
      const g2Results = await scrapeG2(c.g2);
      console.log(`  G2 scraped: ${g2Results.length} pages`);
      
      if (g2Results[0]?.pageScreenshot) {
        const buffer = Buffer.from(g2Results[0].pageScreenshot, 'base64');
        fs.writeFileSync(`/home/elliotbot/clawd/competitive/screenshots/${c.name}-g2-apify.png`, buffer);
        console.log(`  Saved: ${c.name}-g2-apify.png`);
      }
    } catch (e) {
      console.log(`  G2 failed: ${e.message}`);
    }
    
    try {
      // Try YouTube
      const ytResults = await scrapeYouTubeSearch(c.youtube);
      console.log(`  YouTube found: ${ytResults.length} videos`);
      
      // Save video URLs for manual review
      if (ytResults.length > 0) {
        const videoUrls = ytResults.map(v => `${v.title}: ${v.url}`).join('\n');
        fs.appendFileSync(`/home/elliotbot/clawd/competitive/screenshots/${c.name}-videos.txt`, videoUrls);
      }
    } catch (e) {
      console.log(`  YouTube failed: ${e.message}`);
    }
  }
  
  console.log('\nDone!');
})();
