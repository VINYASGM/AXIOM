const { chromium } = require('playwright');

(async () => {
    // 1. Launch Browser
    console.log('Launching browser...');
    const browser = await chromium.launch({ headless: false, slowMo: 50 });
    const page = await browser.newPage();

    try {
        // 2. Navigate to Frontend
        console.log('Navigating to http://localhost:3000...');
        await page.goto('http://localhost:3000');
        await page.screenshot({ path: 'frontend_home.png' });

        // 3. Check for Login
        console.log('Checking for login...');
        // Adjust selectors based on your actual UI
        const loginInput = await page.$('input[type="email"]');

        if (loginInput) {
            console.log('Login form found. Attempting login...');
            await page.fill('input[type="email"]', 'dev@axiom.local');
            await page.fill('input[type="password"]', 'password');
            await page.click('button[type="submit"]'); // Adjust selector
            await page.waitForTimeout(2000);
            await page.screenshot({ path: 'frontend_loggedin.png' });
        } else {
            console.log('No login form found. Assuming already logged in or dashboard view.');
        }

        // 4. Intent Interaction (Optional - adjust selectors)
        // const intentInput = await page.$('textarea'); 
        // if (intentInput) {
        //     await page.fill('textarea', 'Create a new test function');
        //     await page.screenshot({ path: 'frontend_intent_typed.png' });
        // }

    } catch (error) {
        console.error('Error during test:', error);
    } finally {
        console.log('Test complete. Keeping browser open for 5 seconds...');
        await page.waitForTimeout(5000);
        await browser.close();
    }
})();
