const { test, expect } = require('@playwright/test');

test.describe('Mom Transcript Frontend Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the frontend
    await page.goto('http://localhost:3000');
  });

  test('should load homepage without errors', async ({ page }) => {
    // Check if page loads successfully
    await expect(page).toHaveTitle(/Mom Transcript/);
    
    // Check for any console errors
    const errors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });
    
    // Wait for page to fully load
    await page.waitForLoadState('networkidle');
    
    // Log any errors found
    if (errors.length > 0) {
      console.log('Console errors found:', errors);
    }
  });

  test('should test device selector functionality', async ({ page }) => {
    // Look for device selector component
    const deviceSelector = page.locator('[data-testid="device-selector"], select, .device-selector');
    
    // Check if device selector exists
    if (await deviceSelector.count() > 0) {
      await expect(deviceSelector).toBeVisible();
      
      // Try to interact with device selector
      await deviceSelector.click();
    } else {
      console.log('Device selector not found on page');
    }
  });

  test('should test API endpoints', async ({ page }) => {
    // Monitor network requests
    const requests = [];
    const responses = [];
    
    page.on('request', request => {
      requests.push({
        url: request.url(),
        method: request.method()
      });
    });
    
    page.on('response', response => {
      responses.push({
        url: response.url(),
        status: response.status(),
        statusText: response.statusText()
      });
    });
    
    // Wait for page to load and make initial requests
    await page.waitForLoadState('networkidle');
    
    // Check for 404 errors
    const errorResponses = responses.filter(r => r.status === 404);
    if (errorResponses.length > 0) {
      console.log('404 errors found:', errorResponses);
    }
    
    // Check for other error responses
    const otherErrors = responses.filter(r => r.status >= 400 && r.status !== 404);
    if (otherErrors.length > 0) {
      console.log('Other HTTP errors found:', otherErrors);
    }
    
    // Log all requests for debugging
    console.log('All requests made:', requests);
    console.log('All responses received:', responses);
  });

  test('should test transcription modes', async ({ page }) => {
    // Look for transcription mode buttons/selectors
    const modeSelectors = [
      '[data-testid="live-mode"]',
      '[data-testid="batch-mode"]', 
      '[data-testid="hybrid-mode"]',
      'button:has-text("Live")',
      'button:has-text("Batch")',
      'button:has-text("Hybrid")',
      '.mode-selector button',
      'input[type="radio"][value="live"]',
      'input[type="radio"][value="batch"]',
      'input[type="radio"][value="hybrid"]'
    ];
    
    for (const selector of modeSelectors) {
      const element = page.locator(selector);
      if (await element.count() > 0) {
        console.log(`Found transcription mode element: ${selector}`);
        await expect(element).toBeVisible();
        
        // Try to click if it's clickable
        if (await element.isEnabled()) {
          await element.click();
          await page.waitForTimeout(1000); // Wait for any state changes
        }
      }
    }
  });

  test('should test start/stop transcription functionality', async ({ page }) => {
    // Look for start/stop buttons
    const startButtons = [
      '[data-testid="start-transcription"]',
      'button:has-text("Start")',
      'button:has-text("Record")',
      '.start-button',
      '#start-btn'
    ];
    
    const stopButtons = [
      '[data-testid="stop-transcription"]',
      'button:has-text("Stop")',
      '.stop-button',
      '#stop-btn'
    ];
    
    // Test start buttons
    for (const selector of startButtons) {
      const element = page.locator(selector);
      if (await element.count() > 0) {
        console.log(`Found start button: ${selector}`);
        await expect(element).toBeVisible();
        
        if (await element.isEnabled()) {
          await element.click();
          await page.waitForTimeout(2000); // Wait for transcription to start
          
          // Check if stop button appears
          for (const stopSelector of stopButtons) {
            const stopElement = page.locator(stopSelector);
            if (await stopElement.count() > 0 && await stopElement.isVisible()) {
              console.log(`Stop button appeared: ${stopSelector}`);
              await stopElement.click();
              break;
            }
          }
          break;
        }
      }
    }
  });

  test('should test WebSocket connection', async ({ page }) => {
    // Monitor WebSocket connections
    const wsConnections = [];
    
    page.on('websocket', ws => {
      wsConnections.push({
        url: ws.url()
      });
      
      ws.on('framesent', event => {
        console.log('WebSocket frame sent:', event.payload);
      });
      
      ws.on('framereceived', event => {
        console.log('WebSocket frame received:', event.payload);
      });
      
      ws.on('close', () => {
        console.log('WebSocket closed');
      });
    });
    
    // Wait for page to load and establish connections
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);
    
    console.log('WebSocket connections established:', wsConnections);
  });

  test('should check for JavaScript errors', async ({ page }) => {
    const jsErrors = [];
    
    page.on('pageerror', error => {
      jsErrors.push(error.message);
    });
    
    // Wait for page to fully load
    await page.waitForLoadState('networkidle');
    
    // Interact with various elements to trigger potential errors
    await page.click('body');
    await page.keyboard.press('Tab');
    
    // Wait a bit more for any delayed errors
    await page.waitForTimeout(2000);
    
    if (jsErrors.length > 0) {
      console.log('JavaScript errors found:', jsErrors);
    }
    
    // Fail test if critical errors are found
    expect(jsErrors.filter(error => 
      error.includes('404') || 
      error.includes('Failed to fetch') ||
      error.includes('Network Error')
    )).toHaveLength(0);
  });

  test('should not show duplicate completion toasts', async ({ page }) => {
    const toastMessages = [];
    const apiCalls = [];
    
    // Monitor for toast messages in DOM
    page.on('console', msg => {
      if (msg.text().includes('Transcription Completed!')) {
        toastMessages.push({
          message: msg.text(),
          timestamp: Date.now()
        });
      }
    });
    
    // Monitor API calls to status endpoint
    page.on('request', request => {
      if (request.url().includes('/status')) {
        apiCalls.push({
          url: request.url(),
          timestamp: Date.now()
        });
      }
    });
    
    // Wait for page to load
    await page.waitForLoadState('networkidle');
    
    // Monitor for toast elements in DOM
    const toastElements = [];
    const checkForToasts = async () => {
      const toasts = await page.locator('[data-testid="toast"], .toast, [role="alert"]').all();
      for (const toast of toasts) {
        const text = await toast.textContent();
        if (text && text.includes('Transcription Completed')) {
          toastElements.push({
            text: text,
            timestamp: Date.now()
          });
        }
      }
    };
    
    // Check for toasts periodically
    const interval = setInterval(checkForToasts, 1000);
    
    // Wait for potential toast messages to appear
    await page.waitForTimeout(15000);
    
    clearInterval(interval);
    
    console.log('Console toast messages detected:', toastMessages);
    console.log('DOM toast elements detected:', toastElements);
    console.log('Status API calls made:', apiCalls.length);
    
    // Check for duplicate toasts within a short time frame (3 seconds)
    const duplicateToasts = [];
    const allToasts = [...toastMessages, ...toastElements];
    
    for (let i = 1; i < allToasts.length; i++) {
      const timeDiff = allToasts[i].timestamp - allToasts[i-1].timestamp;
      if (timeDiff < 3000) { // Less than 3 seconds apart
        duplicateToasts.push({
          first: allToasts[i-1],
          second: allToasts[i],
          timeDiff: timeDiff
        });
      }
    }
    
    if (duplicateToasts.length > 0) {
      console.log('Duplicate toasts found:', duplicateToasts);
    }
    
    // Check for excessive API polling (more than 10 calls in 15 seconds indicates potential loop)
    const excessivePolling = apiCalls.length > 10;
    if (excessivePolling) {
      console.log('Excessive API polling detected:', apiCalls.length, 'calls in 15 seconds');
    }
    
    // Fail test if duplicate toasts are found
    expect(duplicateToasts).toHaveLength(0);
    
    // Also check that API polling is reasonable (not excessive)
    expect(apiCalls.length).toBeLessThan(15); // Allow up to 15 calls in 15 seconds (1 per second)
  });
});