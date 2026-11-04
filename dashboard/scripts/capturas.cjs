// Gera as capturas das páginas leves para o README (docs/images/), com o painel a correr e os
// dados reais (tema claro):
//   node scripts/capturas.cjs http://localhost:8765/combustiveis-pt/   (pasta dashboard/)
//
// - painel-resumo.png, painel-acompanhados.png, painel-ilhas.png e as análises
//   (painel-analises.png, painel-impostos.png, painel-previsao.png, painel-comparacao.png): o
//   computador, 1280×860;
// - painel-telemovel-paginas.png: as três páginas lado a lado num telemóvel (390×844).
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const IMAGES = path.join(__dirname, '..', '..', 'docs', 'images');
const base = process.argv[2];
if (!base) throw new Error('Falta o endereço do painel (…/combustiveis-pt/).');

// As três primeiras vão também para a imagem do telemóvel.
const PAGINAS = [
	['resumo/', 'painel-resumo.png'],
	['acompanhados/', 'painel-acompanhados.png'],
	['ilhas/', 'painel-ilhas.png'],
	['analises/', 'painel-analises.png'],
	['analises/impostos/', 'painel-impostos.png'],
	['analises/previsao/', 'painel-previsao.png'],
	['analises/comparacao/', 'painel-comparacao.png']
];

async function abrir(page, caminho) {
	await page.goto(new URL(caminho, base).href, { waitUntil: 'networkidle' });
	await page.locator('.cartao, figure').first().waitFor();
	// O mapa dos postos acompanhados: os mosaicos e os pontos.
	await page.waitForTimeout(1500);
}

(async () => {
	const browser = await chromium.launch(
		process.env.PW_CHROMIUM_PATH ? { executablePath: process.env.PW_CHROMIUM_PATH } : {}
	);
	const computador = await browser.newPage({ viewport: { width: 1280, height: 860 }, colorScheme: 'light' });
	for (const [caminho, ficheiro] of PAGINAS) {
		await abrir(computador, caminho);
		await computador.screenshot({ path: path.join(IMAGES, ficheiro) });
		console.log(ficheiro);
	}

	const telemovel = await browser.newPage({
		viewport: { width: 390, height: 844 },
		deviceScaleFactor: 2,
		isMobile: true,
		colorScheme: 'light'
	});
	const imagens = [];
	for (const [caminho] of PAGINAS.slice(0, 3)) {
		await abrir(telemovel, caminho);
		// Logo abaixo do título, para se ver o que interessa (os cartões).
		await telemovel.evaluate(() => {
			const alvo = document.querySelector('.filtros-pagina') ?? document.querySelector('h1');
			window.scrollTo(0, alvo.getBoundingClientRect().top + window.scrollY - 70);
		});
		imagens.push((await telemovel.screenshot()).toString('base64'));
	}
	const juntas = await browser.newPage({ viewport: { width: 1280, height: 860 } });
	await juntas.setContent(`<!doctype html><html><body style="margin:0;background:#f1f5f9;display:flex;
		justify-content:center;align-items:center;gap:32px;height:860px">
		${imagens
			.map(
				(img) => `<img src="data:image/png;base64,${img}" style="width:360px;border-radius:28px;
				box-shadow:0 10px 30px rgba(15,23,42,.25);border:8px solid #0f172a">`
			)
			.join('')}</body></html>`);
	await juntas.screenshot({ path: path.join(IMAGES, 'painel-telemovel-paginas.png') });
	console.log('painel-telemovel-paginas.png');
	await browser.close();
})();
