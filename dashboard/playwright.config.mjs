import { defineConfig } from '@playwright/test';

// Testes do painel já construído (npm run build): abrem cada página como no GitHub Pages.
export default defineConfig({
	testDir: 'tests',
	timeout: 60_000,
	retries: 0,
	use: { baseURL: 'http://localhost:4173/combustiveis-pt/' },
	webServer: {
		command: 'node tests/serve.mjs',
		url: 'http://localhost:4173/combustiveis-pt/',
		reuseExistingServer: !process.env.CI
	}
});
