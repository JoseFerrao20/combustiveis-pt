// Cada página do painel abre sem erros e mostra números. Corre sobre o build (npm run build),
// no CI com os dados da amostra e localmente com os dados reais: só se verifica a forma.
import { expect, test } from '@playwright/test';

const PAGES = [
	['', 'Quanto do preço é imposto?'],
	['comparacao/', 'Portugal e a Europa'],
	['postos/', 'Postos em Portugal'],
	['metodo/', 'Como se calcula']
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

test('a página inicial mostra o preço da última semana', async ({ page }) => {
	await page.goto('');
	await expect(page.locator('main')).toContainText('Preço por litro');
	await expect(page.locator('main')).toContainText(EURO);
	await expect(page.locator('main')).toContainText('Última descarga do boletim');
});

test('a comparação tem Portugal na tabela dos países', async ({ page }) => {
	await page.goto('comparacao/');
	await expect(page.getByRole('cell', { name: 'Portugal', exact: true })).toBeVisible();
});

test('os postos mostram preços e o filtro de distrito reduz a lista', async ({ page }) => {
	const errors = watchErrors(page);
	await page.goto('postos/');
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

test('o método diz quantas semanas de dados há', async ({ page }) => {
	await page.goto('metodo/');
	await expect(page.locator('main')).toContainText(/\d[\d\s]* semanas de dados/);
});
