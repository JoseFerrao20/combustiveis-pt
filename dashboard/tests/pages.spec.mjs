// Cada página do painel abre sem erros e mostra números. Corre sobre o build (npm run build),
// no CI com os dados da amostra e localmente com os dados reais: só se verifica a forma.
import { expect, test } from '@playwright/test';

const PAGES = [
	['', 'Combustível mais barato'],
	['resumo/', 'Resumo e estatísticas'],
	['acompanhados/', 'Postos acompanhados'],
	['analises/', 'Análises'],
	['analises/impostos/', 'Quanto do preço é imposto?'],
	['analises/previsao/', 'Previsão para segunda-feira'],
	['analises/comparacao/', 'Portugal e a Europa'],
	['analises/metodo/', 'Como se calcula'],
	['concelho/', 'Preços por concelho'],
	['dados-abertos/', 'Dados abertos']
];
const EURO = /\d,\d{3} €/;

/** Abre "Filtros" (distrito, concelho, marca, autoestradas, depósito e consumo). */
async function abrirFiltros(page) {
	const filtros = page.locator('details.filtros-postos');
	if ((await filtros.getAttribute('open')) === null) await filtros.locator('summary').click();
}

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

test('o resumo mostra preços e o filtro de distrito reduz a lista', async ({ page }) => {
	const errors = watchErrors(page);
	await page.goto('resumo/');
	const postos = page.locator('.cartao', { hasText: 'Postos' }).locator('.cartao-numero');
	await expect(postos).toBeVisible();
	const contar = async () => Number((await postos.innerText()).replace(/\D/g, ''));
	const all = await contar();
	expect(all).toBeGreaterThan(0);
	await expect(page.locator('main')).toContainText(EURO);

	await page.getByRole('combobox', { name: 'Distrito' }).selectOption({ index: 1 });
	await expect.poll(async () => {
		const n = await contar();
		return n > 0 && n < all;
	}).toBe(true);
	// O concelho só mostra os do distrito escolhido.
	await page.getByRole('combobox', { name: 'Concelho' }).selectOption({ index: 1 });
	await expect.poll(contar).toBeGreaterThan(0);
	expect(errors).toEqual([]);
});

test('o resumo e os postos acompanhados não descarregam o Evidence nem o DuckDB', async ({ page }) => {
	const pedidos = [];
	page.on('request', (request) => pedidos.push(request.url()));
	await page.goto('resumo/');
	await expect(page.locator('.cartao').first()).toBeVisible();
	await page.goto('acompanhados/');
	await expect(page.locator('main')).toContainText(/\dº de \d+/);
	expect(pedidos.filter((url) => /\.wasm|\.parquet|\/_app\//.test(url))).toEqual([]);
});

test('a tabela por baixo do mapa vai do mais barato para o mais caro e segue o mapa', async ({ page }) => {
	const errors = watchErrors(page);
	await page.goto('');
	const mapa = page.locator('.mapa-postos[data-postos]');
	await expect(mapa.locator('tbody tr').first()).toBeVisible();
	await page.waitForLoadState('networkidle');

	const precos = async () =>
		(await mapa.locator('tbody td.preco-celula').allInnerTexts()).map((t) =>
			Number(t.trim().split(/\s/)[0].replace(',', '.'))
		);
	const primeiros = await precos();
	expect(primeiros.length).toBeGreaterThan(0);
	expect(primeiros.every((preco) => preco > 0.5 && preco < 4)).toBe(true);
	expect(primeiros).toEqual([...primeiros].sort((a, b) => a - b));

	const contagem = async () =>
		Number((await mapa.locator('p[aria-live]').innerText()).match(/^[\d\s\u00a0]+/)[0].replace(/\D/g, ''));
	const todos = await contagem();
	// Escolher um posto na tabela aproxima o mapa dele: a tabela fica só com os que se veem.
	await expect(mapa.getByRole('columnheader', { name: 'Na semana' })).toBeVisible();
	await mapa.locator('tbody button[title="Ver no mapa"]').first().click();
	await expect(page.locator('.leaflet-popup-content')).toContainText(EURO);
	// Os preços das últimas fotografias ("28/10: 1,919"), mesmo com uma só (a amostra do CI).
	await expect(page.locator('.leaflet-popup-content')).toContainText(/Últimas fotografias: \d\d\/\d\d: \d,\d{3}/);
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

test('com a localização, a tabela diz quanto se poupa face ao posto mais perto', async ({ page, context }) => {
	await context.grantPermissions(['geolocation']);
	await context.setGeolocation({ latitude: 41.1734, longitude: -8.565 });
	await page.goto('');
	const mapa = page.locator('.mapa-postos[data-postos]');
	await expect(mapa.locator('tbody tr').first()).toBeVisible();
	await page.getByRole('button', { name: 'Perto de mim' }).click();

	await expect(mapa.getByRole('columnheader', { name: 'Poupa' })).toBeVisible();
	await expect(mapa.getByRole('cell', { name: 'o mais perto' })).toBeVisible();
	await expect(mapa.locator('td.poupa').filter({ hasText: /[+−]\d+,\d\d €/ }).first()).toBeVisible();

	// O depósito (em "Filtros") fica guardado no browser.
	await abrirFiltros(page);
	await page.getByLabel('Depósito (L)').fill('40');
	await page.getByLabel('Depósito (L)').blur();
	await expect(page.getByText(/um depósito de 40 L/)).toBeVisible();
	await page.reload();
	await page.getByRole('button', { name: 'Perto de mim' }).click();
	await abrirFiltros(page);
	await expect(page.getByLabel('Depósito (L)')).toHaveValue('40');
});

test('a estrela guarda o posto em "Os meus postos", também depois de recarregar', async ({ page }) => {
	await page.goto('');
	const mapa = page.locator('.mapa-postos[data-postos]');
	await expect(mapa.locator('tbody tr').first()).toBeVisible();
	const meus = page.locator('.meus-postos');
	await expect(meus).toHaveCount(0);
	await expect(page.getByText('Toque na estrela')).toBeVisible();

	const nome = (await mapa.locator('tbody tr').first().locator('button[title="Ver no mapa"]').innerText()).trim();
	await page.getByRole('button', { name: `Guardar ${nome} nos meus postos` }).click();
	await expect(meus.getByRole('listitem')).toHaveCount(1);
	await expect(meus).toContainText(nome);
	await expect(meus).toContainText(EURO);
	// A posição entre os concorrentes a 5 km (ou que não há nenhum).
	await expect(meus.locator('.concorrentes')).toContainText(/a 5 km/);

	await page.reload();
	await expect(meus.getByRole('listitem')).toHaveCount(1);
	await meus.getByRole('button', { name: `Tirar ${nome} dos meus postos` }).click();
	await expect(meus).toHaveCount(0);
	await expect(page.getByText('Toque na estrela')).toBeVisible();
});

test('com o mapa afastado, os postos próximos juntam-se, e tocar num grupo aproxima o mapa', async ({ page }) => {
	const errors = watchErrors(page);
	await page.goto('');
	const mapa = page.locator('.mapa-postos[data-postos]');
	await expect(mapa.locator('tbody tr').first()).toBeVisible();
	const contagem = async () =>
		Number((await mapa.locator('p[aria-live]').innerText()).match(/^[\d\s\u00a0]+/)[0].replace(/\D/g, ''));
	const antes = await contagem();
	const grupo = mapa.locator('.grupo-postos').first();
	await expect(grupo).toHaveAttribute('aria-label', /^\d+ postos, o mais barato a \d,\d{3}/);
	await grupo.click();
	await expect.poll(contagem).toBeLessThan(antes);
	expect(errors).toEqual([]);
});

test('procurar um concelho ou um posto leva o mapa até lá', async ({ page }) => {
	const errors = watchErrors(page);
	await page.goto('');
	const mapa = page.locator('.mapa-postos[data-postos]');
	await expect(mapa.locator('tbody tr').first()).toBeVisible();
	const contagem = async () =>
		Number((await mapa.locator('p[aria-live]').innerText()).match(/^[\d\s\u00a0]+/)[0].replace(/\D/g, ''));
	const todos = await contagem();

	// O concelho do posto mais barato, escrito sem acentos e em minúsculas.
	const concelho = (await mapa.locator('tbody tr').first().locator('td').nth(4).innerText()).trim();
	const procura = page.getByLabel('Procurar uma localidade ou um posto');
	await procura.fill(concelho.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase());
	await page.locator('.resultados button', { hasText: 'concelho' }).first().click();
	await expect.poll(contagem).toBeLessThan(todos);
	await expect(procura).toHaveValue('');

	// Um posto pelo nome: o mapa abre o balão dele.
	const nome = (await mapa.locator('tbody button[title="Ver no mapa"]').first().innerText()).trim();
	await procura.fill(nome);
	await page.locator('.resultados button', { hasText: 'posto ·' }).first().click();
	await expect(page.locator('.leaflet-popup-content')).toContainText(EURO);
	expect(errors).toEqual([]);
});

test('a marca, as autoestradas e o combustível ficam guardados', async ({ page }) => {
	await page.goto('');
	const mapa = page.locator('.mapa-postos[data-postos]');
	await expect(mapa.locator('tbody tr').first()).toBeVisible();

	// Outro combustível: volta a aparecer depois de recarregar, também no resumo.
	const combustivel = page.getByRole('combobox', { name: 'Combustível' });
	await combustivel.selectOption({ index: 1 });
	const escolhido = await combustivel.inputValue();
	const nome = (await combustivel.locator('option:checked').innerText()).trim();
	await expect(mapa.locator('tbody tr').first()).toBeVisible();

	await abrirFiltros(page);
	const marca = page.getByRole('combobox', { name: 'Marca' });
	const opcao = marca.locator('option').nth(1);
	const primeira = await opcao.getAttribute('value');
	// O nome da marca como aparece (sem as maiúsculas todas da DGEG), sem a contagem.
	const rotulo = (await opcao.innerText()).replace(/\s*\(\d+\)\s*$/, '').trim();
	await marca.selectOption(primeira);
	await page.getByLabel('Sem postos de autoestrada').check();
	await expect(mapa.locator('p[aria-live]')).toContainText(`só ${rotulo}, sem autoestradas`);
	const marcas = await mapa.locator('tbody td:nth-child(4)').allInnerTexts();
	expect(marcas.every((m) => m.trim() === rotulo)).toBe(true);

	await page.reload();
	await expect(mapa.locator('p[aria-live]')).toContainText(`só ${rotulo}, sem autoestradas`);
	await expect(combustivel).toHaveValue(escolhido);
	await expect(page.locator('details.filtros-postos summary')).toContainText('2 escolhidos');
	await abrirFiltros(page);
	await expect(marca).toHaveValue(primeira);
	await expect(page.getByLabel('Sem postos de autoestrada')).toBeChecked();
	await page.goto('resumo/');
	await expect(page.getByRole('combobox', { name: 'Combustível' }).locator('option:checked')).toHaveText(nome);
});

test('na página inicial, o distrito e o concelho reduzem a lista', async ({ page }) => {
	const errors = watchErrors(page);
	await page.goto('');
	const mapa = page.locator('.mapa-postos[data-postos]');
	await expect(mapa.locator('tbody tr').first()).toBeVisible();
	const contagem = async () =>
		Number((await mapa.locator('p[aria-live]').innerText()).match(/^[\d\s\u00a0]+/)[0].replace(/\D/g, ''));
	const todos = await contagem();
	await abrirFiltros(page);
	const distrito = page.getByRole('combobox', { name: 'Distrito' });
	const concelho = page.getByRole('combobox', { name: 'Concelho' });
	await distrito.selectOption({ index: 1 });
	await expect.poll(contagem).toBeLessThan(todos);
	const noDistrito = await contagem();
	expect(noDistrito).toBeGreaterThan(0);
	await concelho.selectOption({ index: 1 });
	await expect.poll(contagem).toBeLessThanOrEqual(noDistrito);
	expect(errors).toEqual([]);
});

test('no telemóvel, a lista e o mapa são separadores, e "Ver no mapa" muda para o mapa', async ({ browser }) => {
	const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
	const page = await context.newPage();
	const errors = watchErrors(page);
	await page.goto('');
	const mapa = page.locator('.mapa-postos[data-postos]');
	await expect(mapa.locator('tbody tr').first()).toBeVisible();
	// O combustível e "Perto de mim" no primeiro ecrã.
	await expect(page.getByRole('button', { name: 'Perto de mim' })).toBeInViewport();
	await expect(page.getByRole('combobox', { name: 'Combustível' })).toBeInViewport();
	await expect(page.getByRole('button', { name: 'Lista' })).toHaveAttribute('aria-pressed', 'true');
	await expect(page.locator('.leaflet-container')).not.toBeInViewport();

	await mapa.locator('tbody button[title="Ver no mapa"]').first().click();
	await expect(page.getByRole('button', { name: 'Mapa' })).toHaveAttribute('aria-pressed', 'true');
	await expect(page.locator('.leaflet-popup-content')).toContainText(EURO);
	await expect(mapa.locator('tbody')).toBeHidden();
	await page.getByRole('button', { name: 'Lista' }).click();
	await expect(mapa.locator('tbody tr').first()).toBeVisible();
	expect(errors).toEqual([]);
	await context.close();
});

test('quem já usou "Perto de mim" volta a abrir a página no sítio onde está', async ({ page, context }) => {
	await context.grantPermissions(['geolocation']);
	await context.setGeolocation({ latitude: 41.1734, longitude: -8.565 });
	await page.goto('');
	const mapa = page.locator('.mapa-postos[data-postos]');
	await expect(mapa.locator('tbody tr').first()).toBeVisible();
	// Com a localização autorizada, nem é preciso carregar no botão.
	await expect(mapa.getByRole('columnheader', { name: 'Distância' })).toBeVisible();
	await expect(mapa.locator('p[aria-live]')).toContainText('à volta');
	// Ordenar pela distância: o primeiro é o mais perto.
	await page.getByRole('combobox', { name: 'Ordenar por' }).selectOption('distancia');
	const distancias = (await mapa.locator('tbody td.distancia').allInnerTexts()).map((t) =>
		Number(t.replace(' km', '').replace(',', '.'))
	);
	expect(distancias.length).toBeGreaterThan(1);
	expect(distancias).toEqual([...distancias].sort((a, b) => a - b));
	// "Não abrir aqui" esquece a escolha (a autorização do browser fica, e é ele que manda).
	await page.getByRole('button', { name: 'Não abrir aqui' }).click();
	expect(await page.evaluate(() => localStorage.getItem('combustiveis-pt:localizacao'))).toBeNull();
});

test('o site pode instalar-se como aplicação', async ({ page, request }) => {
	await page.goto('');
	const href = await page.locator('link[rel="manifest"]').getAttribute('href');
	const manifest = await (await request.get(new URL(href, page.url()).href)).json();
	expect(manifest).toMatchObject({
		name: 'Combustível mais barato',
		start_url: '/combustiveis-pt/',
		display: 'standalone'
	});
	expect(manifest.icons.map((icon) => icon.sizes)).toEqual(expect.arrayContaining(['192x192', '512x512']));
	await expect(page.locator('meta[name="theme-color"]')).toHaveAttribute('content', /^#/);
});

test('um posto partilhado abre já no mapa, e "Partilhar" copia o link', async ({ page, context }) => {
	await context.grantPermissions(['clipboard-read', 'clipboard-write']);
	await page.goto('');
	const mapa = page.locator('.mapa-postos[data-postos]');
	await expect(mapa.locator('tbody tr').first()).toBeVisible();
	const resumo = await (await page.request.get('dados/postos-gasoleo.json')).json();
	const id = resumo.stations[0][resumo.columns.indexOf('station_id')];

	await page.goto(`?posto=${id}&combustivel=gasoleo`);
	await expect(page.getByRole('combobox', { name: 'Combustível' })).toHaveValue('gasoleo');
	const balao = page.locator('.leaflet-popup-content');
	await expect(balao).toContainText(EURO);
	// Sem o menu de partilha do telemóvel, o link vai para a área de transferência.
	await page.evaluate(() => {
		delete Navigator.prototype.share;
	});
	await balao.getByRole('button', { name: 'Partilhar' }).click();
	await expect(balao.getByRole('button', { name: 'Link copiado' })).toBeVisible();
	const copiado = await page.evaluate(() => navigator.clipboard.readText());
	expect(copiado).toContain(`?posto=${id}&combustivel=gasoleo`);
});

test('as páginas por concelho mostram os mais baratos e abrem o mapa no concelho', async ({ page }) => {
	const errors = watchErrors(page);
	await page.goto('concelho/');
	await page.locator('main ul a').first().click();
	await expect(page.getByRole('heading', { level: 1, name: /^Combustível mais barato em / })).toBeVisible();
	await expect(page.locator('meta[name="description"]')).toHaveAttribute('content', /a partir de \d,\d{3} €/);
	await expect(page.locator('tbody tr').first()).toContainText(EURO);
	// A data e a hora de cada preço (termos da DGEG).
	await expect(page.locator('tbody tr').first()).toContainText(/\d\d\/\d\d\/\d{4} \d\d:\d\d/);
	await page.getByRole('link', { name: 'Ver todos no mapa' }).click();
	const mapa = page.locator('.mapa-postos[data-postos]');
	await expect(mapa.locator('tbody tr').first()).toBeVisible();
	await expect(page.locator('details.filtros-postos summary')).toContainText('2 escolhidos');
	expect(errors).toEqual([]);
	const sitemap = await (await page.request.get('sitemap.xml')).text();
	expect(sitemap).toContain('/combustiveis-pt/concelho/');
});

test('o tema escolhido no cabeçalho fica em todas as páginas', async ({ page }) => {
	await page.emulateMedia({ colorScheme: 'light' });
	await page.goto('');
	await expect(page.locator('.mapa-postos[data-postos] tbody tr').first()).toBeVisible();
	await page.getByRole('button', { name: 'Mudar para o tema escuro' }).click();
	await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
	await page.goto('resumo/');
	await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
	await page.getByRole('button', { name: 'Mudar para o tema claro' }).click();
	await page.goto('concelho/');
	await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
});

test('os dados abertos descarregam-se a partir do rodapé', async ({ page }) => {
	await page.goto('resumo/');
	await page.getByRole('link', { name: 'Dados abertos', exact: true }).click();
	await expect(page.getByRole('heading', { level: 1, name: 'Dados abertos' })).toBeVisible();
	for (const nome of ['postos-historico.csv.gz', 'postos-ultima-fotografia.csv', 'boletim-europeu.csv.gz']) {
		const link = page.locator(`a[href="${nome}"]`);
		await expect(link).toHaveAttribute('download', '');
		const resposta = await page.request.get(`dados-abertos/${nome}`);
		expect(resposta.status(), nome).toBe(200);
		expect((await resposta.body()).length, nome).toBeGreaterThan(100);
	}
	const ultima = await (await page.request.get('dados-abertos/postos-ultima-fotografia.csv')).text();
	expect(ultima.split('\n')[0]).toContain('snapshot_date,station_id,station_name');
});

test('o balão tem o gráfico do preço nas últimas fotografias', async ({ page }) => {
	await page.goto('');
	const mapa = page.locator('.mapa-postos[data-postos]');
	await expect(mapa.locator('tbody tr').first()).toBeVisible();
	await mapa.locator('tbody button[title="Ver no mapa"]').first().click();
	const balao = page.locator('.leaflet-popup-content');
	await expect(balao).toContainText('Últimas fotografias:');
	const historico = (await balao.innerText()).match(/Últimas fotografias: (.*)/)[1];
	// Com uma só fotografia (a amostra do CI), não há gráfico.
	const grafico = balao.getByRole('img', { name: /^Preço nas últimas fotografias: / });
	if (historico.includes('·')) {
		await expect(grafico).toBeVisible();
		await expect(balao).toContainText(/de \d,\d{3} € a \d,\d{3} €/);
	} else {
		await expect(grafico).toHaveCount(0);
	}
});

test('a página inicial fica leve (limite de peso)', async ({ page }) => {
	// O código (HTML, JavaScript e CSS da página inicial) e os dados do combustível, sem
	// comprimir (o GitHub Pages comprime-os): hoje uns 255 KB e 760 KB. Um aumento grande tem de
	// ser uma decisão, e não um acidente.
	const LIMITE_CODIGO = 320_000;
	const LIMITE_DADOS = 1_200_000;
	const tamanhos = { codigo: 0, dados: 0 };
	page.on('requestfinished', async (request) => {
		const url = new URL(request.url());
		if (url.hostname !== 'localhost') return;
		const { responseBodySize } = await request.sizes();
		if (url.pathname.includes('/dados/')) tamanhos.dados += responseBodySize;
		else tamanhos.codigo += responseBodySize;
	});
	await page.goto('');
	await expect(page.locator('.mapa-postos[data-postos] tbody tr').first()).toBeVisible();
	await page.waitForLoadState('networkidle');
	expect(tamanhos.codigo).toBeGreaterThan(0);
	expect(tamanhos.codigo, `código: ${tamanhos.codigo} bytes`).toBeLessThan(LIMITE_CODIGO);
	expect(tamanhos.dados, `dados: ${tamanhos.dados} bytes`).toBeLessThan(LIMITE_DADOS);
});

test('a página inicial não descarrega o Evidence nem o DuckDB', async ({ page }) => {
	const pedidos = [];
	page.on('request', (request) => pedidos.push(request.url()));
	await page.goto('');
	await expect(page.locator('.mapa-postos[data-postos] tbody tr').first()).toBeVisible();
	expect(pedidos.filter((url) => /\.wasm|\.parquet|\/_app\//.test(url))).toEqual([]);
	// Só o JSON do combustível escolhido.
	expect(pedidos.filter((url) => url.includes('/dados/postos-'))).toHaveLength(1);
});

test('sem rede, a página inicial abre com os últimos preços guardados', async ({ page, context }) => {
	await page.goto('');
	const linhas = page.locator('.mapa-postos[data-postos] tbody tr');
	await expect(linhas.first()).toBeVisible();
	await page.evaluate(() => navigator.serviceWorker.ready);
	// Na segunda visita, já com o service worker, os preços e o mapa ficam guardados.
	await page.reload();
	await expect(linhas.first()).toBeVisible();
	await expect(page.getByText('Sem rede')).toHaveCount(0);
	// A página e os preços do combustível escolhido ficaram guardados no telemóvel.
	const guardados = await page.evaluate(async () => {
		const cache = await caches.open('combustiveis-pt-1');
		return (await cache.keys()).map((request) => new URL(request.url).pathname);
	});
	expect(guardados).toEqual(
		expect.arrayContaining(['/combustiveis-pt/', '/combustiveis-pt/dados/resumo.json', '/combustiveis-pt/dados/postos-gasolina_95.json'])
	);

	await context.setOffline(true);
	await page.reload();
	await expect(page.getByRole('status').filter({ hasText: 'Sem rede: estes são os preços guardados' })).toBeVisible();
	await expect(linhas.first()).toBeVisible();
	await context.setOffline(false);
});

test('o "Início" das páginas do Evidence leva à página inicial', async ({ page }) => {
	await page.goto('analises/');
	await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
	await page.getByRole('link', { name: 'Combustíveis em Portugal' }).first().click();
	await expect(page.locator('.mapa-postos[data-postos] tbody tr').first()).toBeVisible();
	await expect(page.locator('#app')).toBeAttached();
});

test('as páginas têm a descrição e a imagem para a partilha do link', async ({ page }) => {
	await page.goto('');
	await expect(page.locator('meta[property="og:description"]')).toHaveAttribute('content', /.+/);
	await expect(page.locator('meta[property="og:image"]')).toHaveAttribute('content', /^https:.*og\.png$/);
});

test('os postos acompanhados mostram a posição e os concorrentes', async ({ page }) => {
	const errors = watchErrors(page);
	await page.goto('acompanhados/');
	await expect(page.locator('main')).toContainText(EURO);
	await expect(page.locator('main')).toContainText(/\dº de \d+/);
	await expect(page.getByRole('cell').first()).toBeVisible();

	const posto = page.getByRole('combobox', { name: 'Posto' });
	const titulo = page.locator('main h2').first();
	const antes = await titulo.innerText();
	await posto.selectOption({ index: 1 });
	await expect(titulo).not.toHaveText(antes);
	await expect(page.locator('main')).toContainText(/\dº de \d+/);
	await expect(page.locator('.mapa-acompanhados .leaflet-interactive').first()).toBeAttached();
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
	await page.goto('resumo/');
	await expect(page.locator('html')).toHaveAttribute('lang', 'pt-PT');
	await page.goto('analises/');
	await expect(page.locator('html')).toHaveAttribute('lang', 'pt-PT');
	await expect(page.getByText('Feito com o Evidence')).toBeAttached();
	await expect(page.getByText('Built with Evidence')).toHaveCount(0);
});

test('a previsão para segunda-feira aparece na página inicial e na sua página', async ({ page }) => {
	await page.goto('');
	await expect(page.locator('.previsao-segunda')).toContainText(
		/Previsão para segunda-feira, \d\d\/\d\d: Gasolina 95 .* cêntimos, Gasóleo .* cêntimos/
	);
	await page.goto('analises/previsao/');
	await expect(page.locator('main')).toContainText(/\d,\d cêntimos/);
	// Com uma segunda-feira com fotografias, o gasóleo aparece também na comparação com os postos.
	await expect(page.getByRole('cell', { name: 'Gasóleo', exact: true }).first()).toBeVisible();
	// A comparação com os postos na própria segunda-feira (vazia até haver uma segunda com
	// fotografias da DGEG, como na amostra do CI).
	await expect(page.getByRole('heading', { name: 'Na própria segunda-feira, segundo os postos' })).toBeVisible();
	// Sem nenhuma segunda-feira com fotografias da DGEG (a amostra do CI), a faixa da página
	// inicial não fala dos postos.
	if (await page.getByText('A primeira comparação é a de segunda-feira').isVisible()) {
		await page.goto('');
		await expect(page.locator('.previsao-segunda')).not.toContainText('Nos postos');
	}
});

test('o método diz quantas semanas de dados há', async ({ page }) => {
	await page.goto('analises/metodo/');
	await expect(page.locator('main')).toContainText(/\d[\d\s]* semanas de dados/);
});
