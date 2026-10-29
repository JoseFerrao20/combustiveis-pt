// Gera static/og.png (1200×630), a imagem que aparece quando se partilha o link (WhatsApp,
// Facebook, etc.): o ícone, o título e o mapa dos postos. Precisa do painel a correr:
//   node scripts/og.cjs http://localhost:8765/combustiveis-pt/postos/   (pasta dashboard/)
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const STATIC = path.join(__dirname, '..', 'static');
const url = process.argv[2];
if (!url) throw new Error('Falta o endereço da página dos postos.');

(async () => {
	const browser = await chromium.launch(
		process.env.PW_CHROMIUM_PATH ? { executablePath: process.env.PW_CHROMIUM_PATH } : {}
	);
	const page = await browser.newPage({ viewport: { width: 1280, height: 900 }, colorScheme: 'light' });
	await page.goto(url, { waitUntil: 'networkidle' });
	await page.locator('.mapa-postos[data-postos]').waitFor();
	await page.waitForTimeout(3000);
	const map = await page.locator('.mapa-postos .leaflet-container').screenshot();

	const icon = fs.readFileSync(path.join(STATIC, 'icon.svg'), 'utf8');
	await page.setViewportSize({ width: 1200, height: 630 });
	await page.setContent(`<!doctype html><html><head><style>
		body { margin: 0; width: 1200px; height: 630px; display: flex; font-family: system-ui, sans-serif;
		       background: #ffffff; color: #111827; overflow: hidden; }
		.texto { width: 560px; padding: 64px 48px 64px 64px; display: flex; flex-direction: column; gap: 28px; }
		.texto svg { width: 120px; height: 120px; }
		h1 { font-size: 60px; line-height: 1.05; margin: 0; }
		p { font-size: 28px; line-height: 1.3; margin: 0; color: #374151; }
		.mapa { flex: 1; position: relative; background: url(data:image/png;base64,${map.toString('base64')}) center / cover; }
		small { position: absolute; right: 0; bottom: 0; padding: 4px 8px; font-size: 16px;
		        background: rgba(255, 255, 255, 0.85); }
	</style></head><body>
		<div class="texto">${icon}
			<h1>Combustível mais barato perto de si</h1>
			<p>O preço de cada posto em Portugal, atualizado todos os dias.</p>
		</div>
		<div class="mapa"><small>© OpenStreetMap</small></div>
	</body></html>`);
	fs.writeFileSync(path.join(STATIC, 'og.png'), await page.screenshot());
	await browser.close();
})();
