<!--
	A página inicial do site: o mapa e a tabela dos postos (o mesmo componente das páginas do
	Evidence), com os filtros do combustível, do distrito e do concelho. Lê os JSON que o
	`combustiveis site` escreve em dados/: o resumo e os postos do combustível escolhido.
-->
<script>
	import { onMount } from 'svelte';
	import { writable } from 'svelte/store';
	import MapaPostos from '../../components/MapaPostos.svelte';

	const BASE = import.meta.env.BASE_URL;
	const REPOSITORY = 'https://github.com/JoseFerrao20/combustiveis-pt';

	/** O resumo: o dia da fotografia, os combustíveis, os distritos e a previsão. */
	let resumo = null;
	/** O combustível escolhido da última vez (o mapa guarda-o), ou a gasolina 95. */
	let combustivel = 'gasolina_95';
	try {
		combustivel = localStorage.getItem('combustiveis-pt:combustivel') ?? combustivel;
	} catch {
		// Sem acesso ao armazenamento do browser: fica a gasolina 95.
	}
	let distrito = '';
	let concelho = '';
	/** Todos os postos do combustível escolhido. */
	let postos = [];
	let aCarregar = true;
	let erro = '';
	/** Os preços vieram do que ficou guardado no telemóvel (sem rede), e não da rede. */
	let guardados = false;
	/** O browser diz que não há rede. */
	let semRede = typeof navigator !== 'undefined' && navigator.onLine === false;
	const data = writable([]);

	async function lerJson(nome) {
		const response = await fetch(`${BASE}dados/${nome}`);
		if (!response.ok) throw new Error(`HTTP ${response.status}`);
		// O service worker (sw.js) marca as respostas que vêm do que ficou guardado.
		return { conteudo: await response.json(), guardado: response.headers.has('x-combustiveis-guardado') };
	}

	async function carregarPostos(escolhido) {
		aCarregar = true;
		erro = '';
		try {
			const { conteudo, guardado } = await lerJson(`postos-${escolhido}.json`);
			if (escolhido !== combustivel) return; // Entretanto escolheu-se outro.
			guardados = guardado;
			postos = conteudo.stations.map((linha) =>
				Object.fromEntries(conteudo.columns.map((coluna, i) => [coluna, linha[i]]))
			);
		} catch {
			postos = [];
			erro = 'Não foi possível carregar os preços (sem rede?). Tente outra vez daqui a pouco.';
		}
		aCarregar = false;
	}

	onMount(async () => {
		const mudouARede = () => (semRede = !navigator.onLine);
		window.addEventListener('online', mudouARede);
		window.addEventListener('offline', mudouARede);
		try {
			const { conteudo, guardado } = await lerJson('resumo.json');
			resumo = conteudo;
			guardados = guardado;
			if (!resumo.fuels.some((fuel) => fuel.fuel === combustivel)) combustivel = resumo.fuels[0].fuel;
		} catch {
			aCarregar = false;
			erro = 'Não foi possível carregar os preços (sem rede?). Tente outra vez daqui a pouco.';
		}
	});

	$: if (resumo) carregarPostos(combustivel);
	$: concelhos = resumo
		? distrito
			? (resumo.districts[distrito] ?? [])
			: Object.values(resumo.districts).flat().sort((a, b) => a.localeCompare(b, 'pt'))
		: [];
	$: if (concelho && !concelhos.includes(concelho)) concelho = '';
	$: data.set(
		postos.filter(
			(posto) => (!distrito || posto.district === distrito) && (!concelho || posto.municipality === concelho)
		)
	);

	const pad = (n) => String(n).padStart(2, '0');
	/** "02/11/2026" ou "02/11/2026 11:40" (as horas vêm como a hora de Lisboa, em UTC). */
	function quando(texto, comHora = false) {
		if (!texto) return '';
		const d = new Date(texto);
		const dia = `${pad(d.getUTCDate())}/${pad(d.getUTCMonth() + 1)}/${d.getUTCFullYear()}`;
		return comHora ? `${dia} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}` : dia;
	}
</script>

<header class="topo">
	<a class="nome-site" href={BASE}>Combustíveis em Portugal</a>
	<nav aria-label="Outras páginas">
		<a href="{BASE}resumo/">Resumo</a>
		<a href="{BASE}acompanhados/">Postos acompanhados</a>
		<a href="{BASE}analises/">Análises</a>
		<a href={REPOSITORY}>Código no GitHub</a>
	</nav>
</header>

<main>
	<h1>Combustível mais barato</h1>
	<p class="intro">
		O preço de cada posto de Portugal continental, atualizado todas as segundas-feiras. Carregue em
		<strong>Perto de mim</strong>, por baixo, para ver os mais baratos à sua volta, ou escolha o distrito e o
		concelho.
	</p>

	{#if resumo?.forecast}
		<p class="previsao-segunda">
			{resumo.forecast} <a href="{BASE}analises/previsao/">Ver como se calcula</a>.
		</p>
	{/if}

	{#if (guardados || semRede) && resumo}
		<p class="aviso" role="status">
			Sem rede: estes são os preços guardados neste telemóvel, da fotografia de
			{quando(resumo.snapshot_date)}. O fundo do mapa pode não aparecer.
		</p>
	{/if}

	<div class="filtros">
		<label>
			Combustível
			<select bind:value={combustivel} disabled={!resumo}>
				{#each resumo?.fuels ?? [] as fuel}
					<option value={fuel.fuel}>{fuel.name}</option>
				{/each}
			</select>
		</label>
		<label>
			Distrito
			<select bind:value={distrito} disabled={!resumo}>
				<option value="">Todos</option>
				{#each Object.keys(resumo?.districts ?? {}) as nome}
					<option value={nome}>{nome}</option>
				{/each}
			</select>
		</label>
		<label>
			Concelho
			<select bind:value={concelho} disabled={!resumo}>
				<option value="">Todos</option>
				{#each concelhos as nome}
					<option value={nome}>{nome}</option>
				{/each}
			</select>
		</label>
	</div>

	{#if erro}
		<p class="aviso" role="alert">{erro}</p>
	{:else if aCarregar}
		<p class="text-sm text-base-content-muted" role="status">A carregar os preços…</p>
	{/if}

	<MapaPostos {data} {combustivel} />

	<p>
		Mais números (as médias por marca, por grupo de marcas e por concelho, a concorrência e a evolução dos
		preços) no <a href="{BASE}resumo/">resumo</a>.
	</p>

	<footer class="text-sm text-base-content-muted">
		Fonte: Direção-Geral de Energia e Geologia, Preços dos Combustíveis Online
		(<a href="https://precoscombustiveis.dgeg.gov.pt">precoscombustiveis.dgeg.gov.pt</a>). Preços comunicados
		pelos postos; a data e hora de atualização de cada preço está no mapa e na tabela.
		{#if resumo}
			Fotografia de {quando(resumo.snapshot_date)}; última atualização recebida: {quando(resumo.updated_at, true)}.
		{/if}
	</footer>
</main>

<style>
	.topo {
		position: sticky;
		top: 0;
		z-index: 10;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 0.25rem 1rem;
		padding: 0.75rem 1rem;
		background: var(--cabecalho);
		border-bottom: 1px solid var(--linha);
		backdrop-filter: blur(4px);
	}
	.nome-site {
		font-weight: 700;
		text-decoration: none;
	}
	nav {
		display: flex;
		flex-wrap: wrap;
		gap: 0.25rem 1rem;
		font-size: 0.875rem;
	}
	main {
		max-width: 64rem;
		margin: 0 auto;
		padding: 1rem;
	}
	h1 {
		font-size: 1.5rem;
		line-height: 2rem;
		font-weight: 700;
		margin-bottom: 0.75rem;
	}
	.intro {
		margin-bottom: 0.75rem;
	}
	/* Como na faixa da previsão das páginas do Evidence (pages/+layout.svelte). */
	.previsao-segunda {
		border-left: 4px solid #d97706;
		background: rgba(217, 119, 6, 0.08);
		padding: 0.5rem 0.75rem;
		border-radius: 0.25rem;
		margin: 0.75rem 0;
	}
	.aviso {
		border-left: 4px solid var(--destaque);
		background: rgba(37, 99, 235, 0.08);
		padding: 0.5rem 0.75rem;
		border-radius: 0.25rem;
		margin: 0.75rem 0;
	}
	.filtros {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem 1rem;
		margin: 1rem 0 0.5rem;
	}
	.filtros label {
		display: flex;
		flex-direction: column;
		font-size: 0.875rem;
		font-weight: 600;
	}
	.filtros select {
		min-width: 10rem;
		margin-top: 0.25rem;
		padding: 0.375rem 0.5rem;
		border: 1px solid rgba(127, 127, 127, 0.6);
		border-radius: 0.25rem;
		font-weight: 400;
	}
	footer {
		margin-top: 1.5rem;
		padding-top: 1rem;
		border-top: 1px solid var(--linha);
	}
</style>
