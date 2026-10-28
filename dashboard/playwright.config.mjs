import { defineConfig } from '@playwright/test';

// Testes do painel já construído (npm run build): abrem cada página como no GitHub Pages.
export default defineConfig({
	testDir: 'tests',
	timeout: 60_000,
	retries: 0,
	use: {
		baseURL: 'http://localhost:4173/combustiveis-pt/',
		// Nas sessões cloud do Claude Code, o Chromium já instalado (de outra versão do
		// Playwright); no CI, o que o `npx playwright install` descarrega.
		launchOptions: process.env.PW_CHROMIUM_PATH
			? { executablePath: process.env.PW_CHROMIUM_PATH }
			: {}
	},
	webServer: {
		command: 'node tests/serve.mjs',
		url: 'http://localhost:4173/combustiveis-pt/',
		reuseExistingServer: !process.env.CI
	}
});
