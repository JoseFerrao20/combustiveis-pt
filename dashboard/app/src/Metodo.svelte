<!--
	Como se calcula (antes uma página do Evidence, ADR 0008): de onde vêm os dados, a divisão do
	preço e os limites. Lê dados/boletim.json só para o número de semanas.
-->
<script>
	import { onMount } from 'svelte';
	import Cabecalho from '../../components/Cabecalho.svelte';
	import Rodape from '../../components/Rodape.svelte';
	import { BASE, inteiro, lerJson, quando } from './formatos.js';

	const ANALISES = 'https://github.com/JoseFerrao20/combustiveis-pt/blob/main/docs/analises/';
	let boletim = null;
	onMount(async () => {
		try {
			boletim = await lerJson('boletim.json');
		} catch {
			// A página lê-se na mesma, só sem o número de semanas.
		}
	});
</script>

<svelte:head><title>Como se calcula | Combustíveis em Portugal</title></svelte:head>

<Cabecalho base={BASE} atual="{BASE}analises/metodo/" />

<main class="pagina">
	<h1>Como se calcula</h1>

	<h2>Os dados</h2>
	<p>
		O <a href="https://energy.ec.europa.eu/data-and-analysis/weekly-oil-bulletin_en">Weekly Oil Bulletin</a> publica, todas
		as semanas e para cada país da UE, o preço médio de venda ao público de cada combustível, com e sem impostos, e as
		tabelas de IVA, ISP e outros impostos. O preço de cada posto vem do portal da DGEG (uma fotografia por semana), e os
		preços máximos dos Açores e da Madeira dos jornais oficiais das regiões. O código está em
		<a href="https://github.com/JoseFerrao20/combustiveis-pt">JoseFerrao20/combustiveis-pt</a>: ingestão em Python, transformação
		com o dbt e o DuckDB, e este site em páginas estáticas.
	</p>
	{#if boletim}
		<p>
			O site tem {inteiro(boletim.weeks)} semanas de dados do boletim, de {quando(boletim.first_week)} a {quando(boletim.last_week)}.
		</p>
	{/if}

	<h2>A divisão do preço</h2>
	<p>Para cada semana, país e combustível:</p>
	<ul>
		<li><strong>IVA</strong> = preço − preço ÷ (1 + taxa de IVA em vigor nessa semana);</li>
		<li><strong>ISP e outros impostos</strong> = preço ÷ (1 + taxa de IVA) − preço sem impostos;</li>
		<li><strong>produto</strong> = preço sem impostos (petróleo, refinação, distribuição e margens).</li>
	</ul>
	<p>As três partes somam sempre o preço publicado. As tabelas de ISP e de outros impostos do boletim servem só para verificar a conta.</p>

	<h2>Limitações</h2>
	<ul>
		<li>
			Em Portugal, as tabelas de ISP e de outros impostos do boletim batem certo com o preço ao cêntimo na maior parte dos
			anos. Nos outros há erros nas próprias tabelas: a contribuição de serviço rodoviário em falta de 2008 a 2011, valores com
			um algarismo a menos (12,15 em vez de 102,15) e dois valores do ISP trocados em 2025. A divisão acima não depende dessas
			tabelas, por isso não é afetada. A <a href="{ANALISES}impostos-portugal.md">análise</a> mostra cada caso.
		</li>
		<li>
			Na Lituânia (2015–2024) e nos Países Baixos (2011–2023), as tabelas de impostos do boletim ficaram com valores antigos ou
			incompletos; os preços batem certo com as taxas de cada país. A análise está em
			<a href="{ANALISES}impostos-lituania-paises-baixos.md">docs/analises</a>.
		</li>
		<li>
			Na Eslováquia, a tabela de outros impostos não regista uma subida de 10 € de 2017 a 2024. Em Espanha, falta a parte
			regional do "céntimo sanitario" até 2008, e o preço da semana parece ser uma média diária: nas semanas em que o imposto
			muda, só mostra parte da mudança. A <a href="{ANALISES}impostos-semanas-eslovaquia-espanha.md">análise</a> tem cada caso.
		</li>
		<li>
			Há erros de uma semana no próprio boletim (por exemplo, nos fuelóleos da Irlanda e da Bélgica). Estão listados no
			projeto, com a explicação, e os testes de dados ignoram essas semanas.
		</li>
		<li>As médias da UE e da zona euro são ponderadas pelo consumo de cada país.</li>
	</ul>
	<p class="fonte">Dados: © União Europeia, reprodução autorizada com indicação da fonte.</p>

	<Rodape />
</main>
