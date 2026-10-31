// Acessibilidade (WCAG 2.2 AA) de cada página do painel, com o axe. Corre sobre o build, no CI
// com os dados da amostra e localmente com os dados reais.
import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

const PAGES = [
	'',
	'acompanhados/',
	'analises/',
	'analises/impostos/',
	'analises/previsao/',
	'analises/comparacao/',
	'analises/metodo/'
];

/** As violações numa forma que se lê no relatório do teste. */
const summary = (violations) =>
	violations.map((v) => ({
		regra: v.id,
		impacto: v.impact,
		elementos: v.nodes.slice(0, 5).map((n) => n.target.join(' ')),
		ajuda: v.help
	}));

for (const path of PAGES) {
	for (const scheme of ['light', 'dark']) {
		test(`a página ${path || 'inicial'} cumpre a WCAG 2.2 AA (tema ${scheme === 'light' ? 'claro' : 'escuro'})`, async ({ page }) => {
			await page.emulateMedia({ colorScheme: scheme });
			await page.goto(path);
			await page.waitForLoadState('networkidle');
			const results = await new AxeBuilder({ page })
				.withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
				// Os mosaicos do mapa são imagens de fundo do OpenStreetMap, sem texto a ler.
				.exclude('.leaflet-tile-pane')
				.analyze();
			expect(summary(results.violations)).toEqual([]);
		});
	}
}
