// Cada página do painel abre sem erros e mostra números. Corre sobre o build (npm run build),
// no CI com os dados da amostra e localmente com os dados reais: só se verifica a forma.
import { expect, test } from '@playwright/test';

const PAGES = [
	['', 'Combustível mais barato'],
	['acompanhados/', 'Postos acompanhados'],
	['analises/', 'Análises'],
	['analises/impostos/', 'Quanto do preço é imposto?'],
	['analises/comparacao/', 'Portugal e a Europa'],
	['analises/metodo/', 'Como se calcula']
];
const EURO = /\d,\d{3} €/;

/** Falha o teste com erros de JavaScript ou ficheiros do próprio site que não carregam. */
function watchErrors(page) {
	const errors = [];
	page.on('pageerror', (error) => errors.push(`erro: ${error.message}`));
	page.on('response', (response) => {
		const url = response.url();
		if (url.startsWith('http://localhost:4173/') && response.status() >= 400) {
			errors.push(`${response.status()} ${url}`);
		}
	});
	return errors;
}

/** O valor de um BigValue ("Postos 3 137") como número. */
async function bigNumber(page, title) {
	const text = await page.locator('main').innerText();
	const match = text.match(new RegExp(`${title}\\s*\\n\\s*([\\d\\s\\u00a0]+)`));
	expect(match, `não encontrei o número de "${title}"`).not.toBeNull();
	return Number(match[1].replace(/\D/g, ''));
}

for (const [path, title] of PAGES) {
	test(`a página ${path || 'inicial'} abre sem erros`, async ({ page }) => {
		const errors = watchErrors(page);
		await page.goto(path);
		await expect(page.getByRole('heading', { level: 1, name: title })).toBeVisible();
		await page.waitForLoadState('networkidle');
		expect(errors).toEqual([]);
	});
}

test('a página dos impostos mostra o preço da última semana', async ({ page }) => {
	await page.goto('analises/impostos/');
	await expect(page.locator('main')).toContainText('Preço por litro');
	await expect(page.locator('main')).toContainText(EURO);
	await expect(page.locator('main')).toContainText('Última descarga do boletim');
});

test('a comparação tem Portugal na tabela dos países', async ({ page }) => {
	await page.goto('analises/comparacao/');
	await expect(page.getByRole('cell', { name: 'Portugal', exact: true })).toBeVisible();
});

test('os postos mostram preços e o filtro de distrito reduz a lista', async ({ page }) => {
	const errors = watchErrors(page);
	await page.goto('');
	await page.waitForLoadState('networkidle');
	const all = await bigNumber(page, 'Postos');
	expect(all).toBeGreaterThan(0);
	await expect(page.locator('main')).toContainText(EURO);

	await page.locator('button', { hasText: 'Distrito' }).first().click();
	// A primeira opção a seguir a "Todos" (a lista só desenha as primeiras).
	await page.getByRole('option').nth(1).click();
	await page.keyboard.press('Escape');
	await expect.poll(() => bigNumber(page, 'Postos')).toBeLessThan(all);
	expect(await bigNumber(page, 'Postos')).toBeGreaterThan(0);
	expect(errors).toEqual([]);
});

test('a tabela por baixo do mapa vai do mais barato para o mais caro e segue o mapa', async ({ page }) => {
	const errors = watchErrors(page);
	await page.goto('');
	const mapa = page.locator('.mapa-postos[data-postos]');
	await expect(mapa.locator('tbody tr').first()).toBeVisible();
	await page.waitForLoadState('networkidle');

	const precos = async () =>
		(await mapa.locator('tbody td:nth-child(5)').allInnerTexts()).map((t) =>
			Number(t.replace(',', '.'))
		);
	const primeiros = await precos();
	expect(primeiros.length).toBeGreaterThan(0);
	expect(primeiros).toEqual([...primeiros].sort((a, b) => a - b));

	const contagem = async () =>
		Number((await mapa.locator('p[aria-live]').innerText()).match(/^[\d\s\u00a0]+/)[0].replace(/\D/g, ''));
	const todos = await contagem();
	// Escolher um posto na tabela aproxima o mapa dele: a tabela fica só com os que se veem.
	await mapa.locator('tbody button').first().click();
	await expect(page.locator('.leaflet-popup-content')).toContainText(EURO);
	await expect.poll(contagem).toBeLessThan(todos);
	expect(errors).toEqual([]);
});

test('"Perto de mim" centra o mapa na localização e mostra a distância', async ({ page, context }) => {
	// Ao lado do Parque Nascente, no Porto (a amostra dos testes tem os postos à volta).
	await context.grantPermissions(['geolocation']);
	await context.setGeolocation({ latitude: 41.1734, longitude: -8.565 });
	const errors = watchErrors(page);
	await page.goto('');
	const mapa = page.locator('.mapa-postos[data-postos]');
	await expect(mapa.locator('tbody tr').first()).toBeVisible();

	await page.getByRole('button', { name: 'Perto de mim' }).click();
	await expect(mapa.getByRole('columnheader', { name: 'Distância' })).toBeVisible();
	await expect(mapa.locator('tbody tr').first()).toContainText(/\d,\d km/);
	await expect(mapa.getByRole('link', { name: /^Ir até / }).first()).toHaveAttribute(
		'href',
		/^https:\/\/www\.google\.com\/maps\/dir\/\?api=1&destination=/
	);
	expect(errors).toEqual([]);
});

test('as páginas têm a descrição e a imagem para a partilha do link', async ({ page }) => {
	await page.goto('');
	await expect(page.locator('meta[property="og:description"]')).toHaveAttribute('content', /.+/);
	await expect(page.locator('meta[property="og:image"]')).toHaveAttribute('content', /^https:.*og\.png$/);
});

test('os postos acompanhados mostram a posição e os concorrentes', async ({ page }) => {
	const errors = watchErrors(page);
	await page.goto('acompanhados/');
	await page.waitForLoadState('networkidle');
	await expect(page.locator('main')).toContainText(EURO);
	await expect(page.locator('main')).toContainText(/\dº de \d+/);
	await expect(page.getByRole('cell').first()).toBeVisible();

	await page.locator('button', { hasText: 'Posto' }).first().click();
	await page.getByRole('option').nth(1).click();
	await page.keyboard.press('Escape');
	await expect(page.locator('main')).toContainText(/\dº de \d+/);
	expect(errors).toEqual([]);
});

test('os endereços antigos levam às páginas novas', async ({ page }) => {
	await page.goto('postos/');
	await expect(page.getByRole('heading', { level: 1, name: 'Combustível mais barato' })).toBeVisible();
	await page.goto('metodo/');
	await expect(page.getByRole('heading', { level: 1, name: 'Como se calcula' })).toBeVisible();
});

test('a interface está em português', async ({ page }) => {
	await page.goto('');
	await expect(page.locator('html')).toHaveAttribute('lang', 'pt-PT');
	await expect(page.getByText('Feito com o Evidence')).toBeAttached();
	await expect(page.getByText('Built with Evidence')).toHaveCount(0);
});

test('o método diz quantas semanas de dados há', async ({ page }) => {
	await page.goto('analises/metodo/');
	await expect(page.locator('main')).toContainText(/\d[\d\s]* semanas de dados/);
});
