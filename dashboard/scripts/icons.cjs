// Gera os ícones do site (static/*.png e static/favicon.ico) a partir de static/icon.svg,
// com o Chromium do Playwright: node scripts/icons.cjs (pasta dashboard/).
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const STATIC = path.join(__dirname, '..', 'static');
const svg = fs.readFileSync(path.join(STATIC, 'icon.svg'), 'utf8');

/** Um ICO com um só PNG lá dentro (o formato aceita PNG desde o Windows Vista). */
function ico(png, size) {
	const header = Buffer.alloc(22);
	header.writeUInt16LE(0, 0);
	header.writeUInt16LE(1, 2);
	header.writeUInt16LE(1, 4);
	header.writeUInt8(size, 6);
	header.writeUInt8(size, 7);
	header.writeUInt16LE(1, 10); // planos
	header.writeUInt16LE(32, 12); // bits por pixel
	header.writeUInt32LE(png.length, 14);
	header.writeUInt32LE(22, 18); // o PNG começa a seguir ao cabeçalho
	return Buffer.concat([header, png]);
}

(async () => {
	const browser = await chromium.launch(
		process.env.PW_CHROMIUM_PATH ? { executablePath: process.env.PW_CHROMIUM_PATH } : {}
	);
	const page = await browser.newPage();
	// O iOS põe fundo preto nos cantos transparentes e arredonda o ícone sozinho: lá vai quadrado.
	const render = async (size, square = false) => {
		await page.setViewportSize({ width: size, height: size });
		await page.setContent(
			`<style>html,body{margin:0;background:transparent}svg{width:${size}px;height:${size}px;display:block}</style>${square ? svg.replace('rx="112"', 'rx="0"') : svg}`
		);
		return page.screenshot({ omitBackground: true });
	};
	fs.writeFileSync(path.join(STATIC, 'apple-touch-icon.png'), await render(180, true));
	for (const [name, size] of [['icon-192.png', 192], ['icon-512.png', 512]]) {
		fs.writeFileSync(path.join(STATIC, name), await render(size));
	}
	fs.writeFileSync(path.join(STATIC, 'favicon.ico'), ico(await render(32), 32));
	await browser.close();
})();
