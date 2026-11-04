<!--
	Quanto do preço é imposto (antes uma página do Evidence, ADR 0008): o preço de Portugal no
	Weekly Oil Bulletin, dividido em produto, ISP e outros impostos e IVA, semana a semana desde
	2005. Lê dados/boletim.json.
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

	$: linhas = boletim ? tabela(boletim.portugal).filter((r) => r.product === produto) : [];
	$: ultima = linhas.at(-1);
	$: series = [
		{ nome: 'Produto', cor: '#64748b', pontos: linhas.map((r) => ({ x: r.week, y: r.price_without_tax })) },
		{ nome: 'ISP e outros impostos', cor: '#d97706', pontos: linhas.map((r) => ({ x: r.week, y: r.excise_and_other_taxes })) },
		{ nome: 'IVA', cor: '#b91c1c', pontos: linhas.map((r) => ({ x: r.week, y: r.vat_amount })) }
	];
	$: peso = [{ nome: 'Parte do preço que é imposto', cor: '#b45309', pontos: linhas.map((r) => ({ x: r.week, y: r.tax_share })) }];
</script>

<svelte:head><title>Quanto do preço é imposto? | Combustíveis em Portugal</title></svelte:head>

<Cabecalho base={BASE} atual="{BASE}analises/impostos/" />

<main class="pagina">
	<h1>Quanto do preço é imposto?</h1>
	<p>
		Preços semanais dos combustíveis em Portugal desde 2005, a partir do
		<a href="https://energy.ec.europa.eu/data-and-analysis/weekly-oil-bulletin_en">Weekly Oil Bulletin</a> da Comissão
		Europeia. Os valores são médias nacionais em euros por litro, não os preços de um posto.
	</p>

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

		{#if ultima}
			<h2>Semana de {quando(ultima.week)}</h2>
			<div class="cartoes">
				<div class="cartao"><span class="cartao-titulo">Preço por litro</span><span class="cartao-numero">{euros(ultima.price)}</span></div>
				<div class="cartao"><span class="cartao-titulo">Impostos</span><span class="cartao-numero">{euros(ultima.taxes_total)}</span></div>
				<div class="cartao"><span class="cartao-titulo">Parte do preço</span><span class="cartao-numero">{pct(ultima.tax_share)}</span></div>
			</div>
			<div class="rolar">
				<table class="tabela tabela-estreita">
					<thead><tr><th>Parte do preço</th><th class="num">€ por litro</th></tr></thead>
					<tbody>
						<tr><td>Produto (antes de impostos)</td><td class="num">{euros(ultima.price_without_tax)}</td></tr>
						<tr><td>ISP e outros impostos</td><td class="num">{euros(ultima.excise_and_other_taxes)}</td></tr>
						<tr><td>IVA</td><td class="num">{euros(ultima.vat_amount)}</td></tr>
					</tbody>
					<tfoot><tr><th>Preço</th><th class="num">{euros(ultima.price)}</th></tr></tfoot>
				</table>
			</div>
		{/if}

		<h2>Desde 2005</h2>
		<Grafico titulo="Preço por litro, dividido em produto e impostos" {series} empilhado formato={euros2} />
		<Grafico titulo="Parte do preço que é imposto" series={peso} minimo={0} formato={(v) => pct(v, 0)} />
		<p>
			Quando o petróleo fica mais barato, os impostos pesam mais, porque o ISP é um valor fixo por litro e não uma
			percentagem. As descidas do ISP de 2022 notam-se no gráfico de cima.
		</p>
		{#if boletim.downloaded_at}
			<p class="fonte">Última descarga do boletim: {quando(boletim.downloaded_at)}. O site atualiza-se todos os dias.</p>
		{/if}
	{/if}

	<Rodape />
</main>

<style>
	.tabela-estreita {
		max-width: 28rem;
	}
	.tabela-estreita tfoot th {
		border-top: 2px solid var(--linha);
	}
</style>
