<!--
	Portugal e a Europa (antes uma página do Evidence, ADR 0008): o preço em Portugal, em Espanha e
	na média da UE desde 2005, e todos os países na última semana, divididos em produto e impostos.
	Lê dados/boletim.json.
-->
<script>
	import { onMount } from 'svelte';
	import Cabecalho from '../../components/Cabecalho.svelte';
	import Rodape from '../../components/Rodape.svelte';
	import Grafico from './Grafico.svelte';
	import { BASE, euros, euros2, guardarProduto, lerJson, pct, produtoGuardado, quando, tabela } from './formatos.js';

	let boletim = null;
	let erro = '';
	let produto = produtoGuardado();
	$: guardarProduto(produto);
	onMount(async () => {
		try {
			boletim = await lerJson('boletim.json');
			if (!boletim.products.some((p) => p.product === produto)) produto = boletim.products[0].product;
		} catch {
			erro = 'Não foi possível carregar o boletim. Tente outra vez daqui a pouco.';
		}
	});

	const CORES = { PT: '#15803d', ES: '#d97706', EU: '#2563eb' };
	$: portugal = boletim ? tabela(boletim.portugal).filter((r) => r.product === produto) : [];
	$: vizinhos = boletim ? tabela(boletim.neighbours).filter((r) => r.product === produto) : [];
	$: series = boletim
		? [
				{ nome: boletim.countries.PT, cor: CORES.PT, pontos: portugal.map((r) => ({ x: r.week, y: r.price })) },
				...['ES', 'EU'].map((codigo) => ({
					nome: boletim.countries[codigo],
					cor: CORES[codigo],
					pontos: vizinhos.filter((r) => r.country_code === codigo).map((r) => ({ x: r.week, y: r.price }))
				}))
			]
		: [];
	$: paises = boletim ? tabela(boletim.latest).filter((r) => r.product === produto) : [];
	$: semana = paises[0]?.week;
	$: maximo = Math.max(...paises.map((r) => r.price), 0.01);
	$: posicao = paises.findIndex((r) => r.country_code === 'PT') + 1;
</script>

<svelte:head><title>Portugal e a Europa | Combustíveis em Portugal</title></svelte:head>

<Cabecalho base={BASE} atual="{BASE}analises/comparacao/" />

<main class="pagina">
	<h1>Portugal e a Europa</h1>
	<p>O preço dos combustíveis em Portugal comparado com Espanha e com a média da União Europeia, a partir do Weekly Oil Bulletin da Comissão Europeia.</p>

	{#if erro}
		<p class="conclusao" role="alert">{erro}</p>
	{:else if !boletim}
		<p role="status">A carregar…</p>
	{:else}
		<div class="filtros-pagina">
			<label>
				Combustível
				<select bind:value={produto}>
					{#each boletim.products as p (p.product)}<option value={p.product}>{p.name}</option>{/each}
				</select>
			</label>
		</div>

		<Grafico titulo="Preço por litro: Portugal, Espanha e a média da UE" {series} formato={euros2} />

		{#if semana}
			<h2>Na semana de {quando(semana)}</h2>
			{#if posicao}
				<p class="conclusao">Portugal é o {posicao}.º mais caro de {paises.length} países.</p>
			{/if}
			<figure class="paises">
				<figcaption class="grafico-titulo">Preço por litro em cada país, dividido em produto e impostos</figcaption>
				<ul class="legenda-paises" aria-hidden="true">
					<li><span class="cor" style="background: #64748b" />Produto</li>
					<li><span class="cor" style="background: #d97706" />Impostos</li>
				</ul>
				<ol aria-hidden="true">
					{#each paises as r (r.country_code)}
						<li class:portugal={r.country_code === 'PT'}>
							<span class="nome">{r.country}</span>
							<span class="barra">
								<span style="width: {(r.price_without_tax / maximo) * 100}%; background: #64748b" />
								<span style="width: {(r.taxes_total / maximo) * 100}%; background: #d97706" />
							</span>
							<span class="valor">{euros(r.price)}</span>
						</li>
					{/each}
				</ol>
			</figure>
			<div class="rolar">
				<table class="tabela">
					<caption class="sr-only">Preço por litro em cada país na semana de {quando(semana)}</caption>
					<thead>
						<tr><th>País</th><th class="num">Preço (€/L)</th><th class="num">Produto (€/L)</th><th class="num">Impostos (€/L)</th><th class="num">Parte do preço</th></tr>
					</thead>
					<tbody>
						{#each paises as r (r.country_code)}
							<tr class:portugal={r.country_code === 'PT'}>
								<td>{r.country}</td>
								<td class="num">{euros(r.price)}</td>
								<td class="num">{euros(r.price_without_tax)}</td>
								<td class="num">{euros(r.taxes_total)}</td>
								<td class="num">{pct(r.tax_share)}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
			<p>O preço antes de impostos também muda de país para país (logística, concorrência e margens), não só os impostos.</p>
		{/if}
	{/if}

	<Rodape />
</main>

<style>
	.paises {
		margin: 0.75rem 0 1.25rem;
	}
	.grafico-titulo {
		font-weight: 600;
		font-size: 0.9rem;
	}
	.paises ol {
		list-style: none;
		padding: 0;
		margin: 0.5rem 0 0;
	}
	.paises li {
		display: grid;
		grid-template-columns: minmax(6rem, 9rem) 1fr 4.5rem;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.85rem;
		padding: 1px 0;
	}
	.barra {
		display: flex;
		height: 0.9rem;
	}
	.valor {
		text-align: right;
		font-variant-numeric: tabular-nums;
	}
	.portugal {
		font-weight: 700;
	}
	.legenda-paises {
		display: flex;
		gap: 1rem;
		list-style: none;
		padding: 0;
		margin: 0.25rem 0 0;
		font-size: 0.85rem;
	}
	.paises .legenda-paises li {
		display: list-item;
	}
	.cor {
		display: inline-block;
		width: 0.8rem;
		height: 0.8rem;
		border-radius: 999px;
		margin-right: 0.35rem;
		vertical-align: -0.1rem;
	}
</style>
