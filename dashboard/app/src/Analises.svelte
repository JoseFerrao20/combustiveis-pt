<!--
	As análises (antes páginas do Evidence, ADR 0008): um cartão por análise, com o número
	principal. Lê dados/boletim.json, dados/previsao.json e dados/resumo.json.
-->
<script>
	import { onMount } from 'svelte';
	import Cabecalho from '../../components/Cabecalho.svelte';
	import Rodape from '../../components/Rodape.svelte';
	import { BASE, diaCurto, inteiro, lerJson, pct, quando, seta, tabela } from './formatos.js';

	let boletim = null;
	let previsao = [];
	let resumo = null;
	let erro = '';
	onMount(async () => {
		try {
			[boletim, { rows: previsao }, resumo] = await Promise.all([
				lerJson('boletim.json'),
				lerJson('previsao.json'),
				lerJson('resumo.json')
			]);
		} catch {
			erro = 'Não foi possível carregar as análises. Tente outra vez daqui a pouco.';
		}
	});

	$: portugal = boletim ? tabela(boletim.portugal).filter((r) => r.product === 'euro95') : [];
	$: ultima = portugal.at(-1);
	$: espanha = boletim
		? tabela(boletim.neighbours).find((r) => r.product === 'euro95' && r.country_code === 'ES' && r.week === ultima?.week)
		: null;
	$: faceEspanha = ultima && espanha ? ultima.price - espanha.price : null;
	$: proxima = previsao.filter((r) => r.product === 'euro95').at(-1);
	$: conhecidas = previsao.filter((r) => r.is_known);
	$: erroMedio = conhecidas.length
		? (conhecidas.reduce((soma, r) => soma + Math.abs(r.predicted_change - r.actual_change), 0) / conhecidas.length) * 100
		: null;
	const cent = (c) => c.toLocaleString('pt-PT', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
</script>

<svelte:head><title>Análises | Combustíveis em Portugal</title></svelte:head>

<Cabecalho base={BASE} atual="{BASE}analises/" />

<main class="pagina">
	<h1>Análises</h1>
	<p>Para quem quer ir além do posto mais barato. Cada cartão abre uma análise.</p>

	{#if erro}
		<p class="conclusao" role="alert">{erro}</p>
	{:else if !boletim}
		<p role="status">A carregar…</p>
	{:else}
		<div class="cartoes">
			<a class="cartao" href="{BASE}analises/impostos/">
				<span class="cartao-titulo">Quanto do preço é imposto?</span>
				<span class="cartao-numero">{pct(ultima?.tax_share, 0)}</span>
				<span class="cartao-texto"
					>do preço da gasolina 95 é ISP e IVA (semana de {quando(ultima?.week)}). Semana a semana desde
					{boletim.first_week.slice(0, 4)}.</span
				>
			</a>
			<a class="cartao" href="{BASE}analises/previsao/">
				<span class="cartao-titulo">Previsão para segunda-feira</span>
				<span class="cartao-numero">{proxima ? seta(proxima.predicted_change).texto : '–'}</span>
				<span class="cartao-texto"
					>na gasolina 95{#if proxima}, a {diaCurto(proxima.target_week)}{/if}, a partir dos mercados. {erroMedio == null
						? 'Ainda sem semanas para comparar.'
						: `Erro médio de ${cent(erroMedio)} cêntimos nas semanas desde 2024.`}</span
				>
			</a>
			<a class="cartao" href="{BASE}analises/comparacao/">
				<span class="cartao-titulo">Portugal e a Europa</span>
				<span class="cartao-numero"
					>{faceEspanha == null ? '–' : `${faceEspanha > 0 ? '+' : '−'}${cent(Math.abs(faceEspanha * 100))} c`}</span
				>
				<span class="cartao-texto"
					>por litro: a gasolina 95 em Portugal, {faceEspanha > 0 ? 'mais cara' : 'mais barata'} do que em Espanha. Com a
					média da União Europeia.</span
				>
			</a>
			<a class="cartao" href="{BASE}analises/metodo/">
				<span class="cartao-titulo">Como se calcula</span>
				<span class="cartao-numero">{inteiro(boletim.weeks)} semanas</span>
				<span class="cartao-texto"
					>do boletim europeu desde {boletim.first_week.slice(0, 4)}{#if resumo?.stations_total}, e {inteiro(
							resumo.stations_total
						)} postos em Portugal{/if}. De onde vêm os dados, as contas e os limites.</span
				>
			</a>
		</div>
	{/if}

	<Rodape />
</main>
