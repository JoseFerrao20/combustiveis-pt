<!--
	Os preços máximos dos Açores e da Madeira (ADR 0007): a DGEG só tem os postos do continente, e
	nas regiões autónomas o governo regional fixa um preço máximo, em despachos publicados em PDF
	(mensais nos Açores, semanais na Madeira). Lê dados/ilhas.json (`combustiveis site`).
-->
<script>
	import { onMount } from 'svelte';
	import Cabecalho from '../../components/Cabecalho.svelte';
	import Rodape from '../../components/Rodape.svelte';
	import Grafico from './Grafico.svelte';
	import { BASE, combustivelGuardado, euros, guardarCombustivel, lerJson, quando, seta } from './formatos.js';

	const COMBUSTIVEIS = [
		['gasolina_95', 'Gasolina 95'],
		['gasoleo', 'Gasóleo']
	];
	const REGIOES = [
		['madeira', 'Madeira', 'semanal (JORAM, à sexta-feira, em vigor na segunda)'],
		['acores', 'Açores', 'mensal (Jornal Oficial, em vigor no dia 1)']
	];
	const CORES = { madeira: '#2563eb', acores: '#d97706', continente: '#64748b' };

	let dados = null;
	let erro = '';
	const guardado = combustivelGuardado();
	let combustivel = COMBUSTIVEIS.some(([id]) => id === guardado) ? guardado : 'gasolina_95';
	$: guardarCombustivel(combustivel);

	onMount(async () => {
		try {
			dados = await lerJson('ilhas.json');
		} catch {
			erro = 'Não foi possível carregar os preços das regiões autónomas. Tente outra vez daqui a pouco.';
		}
	});

	const hoje = new Date().toISOString().slice(0, 10);
	$: linhas = dados ? dados.rows.filter((r) => r.fuel === combustivel) : [];
	/** O preço em vigor hoje e o seguinte, se já foi publicado (a Madeira publica à sexta). */
	function estado(linhas, regiao) {
		const daRegiao = linhas.filter((r) => r.region === regiao);
		const vigor = daRegiao.filter((r) => r.valid_from <= hoje).at(-1);
		const seguinte = daRegiao.find((r) => r.valid_from > hoje);
		const anterior = vigor ? daRegiao[daRegiao.indexOf(vigor) - 1] : undefined;
		return { vigor, seguinte, anterior };
	}
	$: regioes = REGIOES.map(([id, nome, ritmo]) => ({ id, nome, ritmo, ...estado(linhas, id) }));
	// O preço médio dos postos do continente: o da fotografia mais recente que os dados têm.
	$: continente = linhas
		.filter((r) => r.continent_avg_price != null)
		.sort((a, b) => a.continent_snapshot.localeCompare(b.continent_snapshot))
		.at(-1);
	$: nomeCombustivel = COMBUSTIVEIS.find(([id]) => id === combustivel)[1];
	$: artigo = combustivel === 'gasoleo' ? 'o' : 'a';

	// O gráfico: no máximo os últimos 12 meses, para os pontos semanais da Madeira se verem.
	const inicio = new Date(Date.now() - 365 * 86400000).toISOString().slice(0, 10);
	$: recentes = linhas.filter((r) => r.valid_from >= inicio);
	$: series = [
		...REGIOES.map(([id, nome]) => ({
			nome,
			cor: CORES[id],
			pontos: recentes.filter((r) => r.region === id).map((r) => ({ x: r.valid_from, y: r.price }))
		})),
		{
			nome: 'Média dos postos do continente',
			cor: CORES.continente,
			pontos: [
				...new Map(
					recentes
						.filter((r) => r.region === 'madeira' && r.continent_avg_price != null)
						.map((r) => [r.valid_from, { x: r.valid_from, y: r.continent_avg_price }])
				).values()
			]
		}
	].filter((s) => s.pontos.length);
	$: historico = [...linhas].sort((a, b) => b.valid_from.localeCompare(a.valid_from) || a.region.localeCompare(b.region));
	let mostrar = 12;
</script>

<svelte:head><title>Açores e Madeira | Combustíveis em Portugal</title></svelte:head>

<Cabecalho base={BASE} atual="{BASE}ilhas/" />

<main class="pagina">
	<h1>Açores e Madeira</h1>
	<p>
		Nas regiões autónomas, o governo regional fixa o <strong>preço máximo</strong> da gasolina 95 e do gasóleo. Os postos
		podem vender mais barato, mas quase todos vendem ao máximo. A DGEG só tem os postos do continente: os preços desta
		página vêm dos despachos publicados nos jornais oficiais das regiões.
	</p>

	{#if erro}
		<p class="conclusao" role="alert">{erro}</p>
	{:else if !dados}
		<p role="status">A carregar…</p>
	{:else if !dados.rows.length}
		<p>Ainda não há preços das regiões autónomas.</p>
	{:else}
		<div class="filtros-pagina">
			<label>
				Combustível
				<select bind:value={combustivel}>
					{#each COMBUSTIVEIS as [id, nome] (id)}<option value={id}>{nome}</option>{/each}
				</select>
			</label>
		</div>

		<h2>Preço máximo em vigor</h2>
		<div class="cartoes">
			{#each regioes as regiao (regiao.id)}
				<div class="cartao">
					<span class="cartao-titulo">{regiao.nome}</span>
					<span class="cartao-numero">{euros(regiao.vigor?.price)}</span>
					<span class="cartao-texto">
						{#if regiao.vigor}
							desde {quando(regiao.vigor.valid_from)}{#if regiao.anterior}
								{' '}(<span class={seta(regiao.vigor.price - regiao.anterior.price).classe}
									>{seta(regiao.vigor.price - regiao.anterior.price).texto}</span
								>){/if}
						{:else}
							sem preço em vigor
						{/if}
					</span>
					{#if regiao.seguinte}
						<span class="cartao-texto"
							>A partir de {quando(regiao.seguinte.valid_from)}: <strong>{euros(regiao.seguinte.price)}</strong></span
						>
					{/if}
				</div>
			{/each}
			{#if continente}
				<div class="cartao">
					<span class="cartao-titulo">Continente (média dos postos)</span>
					<span class="cartao-numero">{euros(continente.continent_avg_price)}</span>
					<span class="cartao-texto">fotografia da DGEG de {quando(continente.continent_snapshot)}</span>
				</div>
			{/if}
		</div>

		{#if continente}
			<p class="conclusao">
				{#each regioes.filter((r) => r.vigor) as regiao, i (regiao.id)}
					{@const diferenca = regiao.vigor.price - continente.continent_avg_price}
					{i ? ' ' : ''}{regiao.nome === 'Açores' ? 'Nos Açores' : 'Na Madeira'}, {artigo} {nomeCombustivel.toLowerCase()} pode custar
					no máximo <strong>{euros(regiao.vigor.price)}</strong>,
					<span class={seta(diferenca).classe}>{seta(diferenca).texto.replace('▼ ', '').replace('▲ ', '')}</span>
					{diferenca < 0 ? 'abaixo' : 'acima'} da média dos postos do continente.
				{/each}
			</p>
		{/if}
		<p>
			O preço máximo muda com as cotações internacionais, como no continente, mas com outro ritmo:
			{#each REGIOES as [id, nome, ritmo], i (id)}{i ? '; ' : ''}{nome}, {ritmo}{/each}. Os impostos (ISP e IVA) também são
			mais baixos nas regiões autónomas.
		</p>

		<h2>Ao longo do tempo</h2>
		{#if series.length}
			<Grafico titulo="{nomeCombustivel}: preço máximo nas regiões autónomas e preço médio no continente" {series} />
			<p class="text-sm text-base-content-muted">
				A média do continente só existe desde que o projeto tira fotografias aos preços dos postos (outubro de 2026).
			</p>
		{/if}

		<details class="mais-detalhes">
			<summary>Ver todos os despachos ({historico.length})</summary>
			<div class="rolar">
				<table class="tabela">
					<thead>
						<tr><th>Em vigor desde</th><th>Região</th><th class="num">Preço máximo</th><th>Despacho</th><th>Publicado</th></tr>
					</thead>
					<tbody>
						{#each historico.slice(0, mostrar) as r (r.region + r.valid_from)}
							<tr>
								<td>{quando(r.valid_from)}</td>
								<td>{r.region_name}</td>
								<td class="num">{euros(r.price)}</td>
								<td><a href={r.source_url}>{r.act}</a></td>
								<td>{quando(r.published)}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
			{#if historico.length > mostrar}
				<button type="button" class="botao-secundario" on:click={() => (mostrar = historico.length)}
					>Mostrar os {historico.length} despachos</button
				>
			{/if}
		</details>
		<p>
			Os dados também estão nos <a href="{BASE}dados-abertos/" rel="external">dados abertos</a>, em CSV.
		</p>
	{/if}

	<Rodape>
		<p>
			Fontes: Jornal Oficial da Região Autónoma dos Açores (I série, despachos normativos) e Jornal Oficial da Região
			Autónoma da Madeira (II série, despachos conjuntos), lidos dos PDFs publicados; Direção-Geral de Energia e Geologia
			(preços dos postos do continente).
		</p>
	</Rodape>
</main>
