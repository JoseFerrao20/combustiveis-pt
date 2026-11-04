<!--
	A previsão para segunda-feira (antes uma página do Evidence, ADR 0004 e 0008): a próxima, a
	comparação com os postos na própria segunda e como se tem saído desde 2024. Lê
	dados/previsao.json.
-->
<script>
	import { onMount } from 'svelte';
	import Cabecalho from '../../components/Cabecalho.svelte';
	import Rodape from '../../components/Rodape.svelte';
	import GraficoBarras from './GraficoBarras.svelte';
	import { BASE, diaCurto, inteiro, lerJson, pct, quando } from './formatos.js';

	let linhas = null;
	let erro = '';
	onMount(async () => {
		try {
			({ rows: linhas } = await lerJson('previsao.json'));
		} catch {
			erro = 'Não foi possível carregar a previsão. Tente outra vez daqui a pouco.';
		}
	});

	/** "+1,5 cêntimos" ou "−0,4 cêntimos" (de uma mudança em euros). */
	const centimos = (v, unidade = ' cêntimos') => {
		if (v == null) return '–';
		const c = Math.round(v * 1000) / 10;
		return `${c > 0 ? '+' : c < 0 ? '−' : ''}${Math.abs(c).toLocaleString('pt-PT', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}${unidade}`;
	};
	const ordem = (a, b) => (a.product === 'diesel') - (b.product === 'diesel');

	$: semana = linhas?.length ? linhas.reduce((m, r) => (r.target_week > m ? r.target_week : m), '') : null;
	$: proxima = linhas ? linhas.filter((r) => r.target_week === semana).sort(ordem) : [];
	$: naSegunda = linhas ? linhas.filter((r) => r.dgeg_change != null).sort((a, b) => b.target_week.localeCompare(a.target_week) || ordem(a, b)) : [];
	$: conhecidas = linhas ? linhas.filter((r) => r.is_known) : [];
	$: acerto = ['euro95', 'diesel']
		.map((produto) => {
			const r = conhecidas.filter((l) => l.product === produto);
			if (!r.length) return null;
			const media = (f) => r.reduce((s, l) => s + f(l), 0) / r.length;
			const comMudanca = r.filter((l) => l.actual_change !== 0);
			return {
				nome: r[0].product_name,
				semanas: r.length,
				erro: media((l) => Math.abs(l.predicted_change - l.actual_change)),
				semPrevisao: media((l) => Math.abs(l.actual_change)),
				sentido: comMudanca.filter((l) => Math.sign(l.predicted_change) === Math.sign(l.actual_change)).length / (comMudanca.length || 1)
			};
		})
		.filter(Boolean);
	// Os gráficos: os últimos 6 meses de semanas conhecidas.
	$: recentes = conhecidas.slice(-2 * 26);
	function graficos(recentes) {
		return [
			['euro95', 'Gasolina 95', '#d97706'],
			['diesel', 'Gasóleo', '#b45309']
		].map(([produto, nome, cor]) => {
			const r = recentes.filter((l) => l.product === produto).slice(-26);
			return {
				titulo: `${nome}: mudança à segunda-feira, em cêntimos por litro (últimos 6 meses)`,
				categorias: r.map((l) => l.target_week),
				series: [
					{ nome: 'Prevista', cor: '#94a3b8', valores: r.map((l) => l.predicted_change * 100) },
					{ nome: 'Real', cor, valores: r.map((l) => l.actual_change * 100) }
				]
			};
		});
	}
	$: barras = graficos(recentes);
	const um = (v) => (v == null ? '–' : `${v > 0 ? '+' : v < 0 ? '−' : ''}${Math.abs(v).toLocaleString('pt-PT', { maximumFractionDigits: 1 })}`);
</script>

<svelte:head><title>Previsão para segunda-feira | Combustíveis em Portugal</title></svelte:head>

<Cabecalho base={BASE} atual="{BASE}analises/previsao/" />

<main class="pagina">
	<h1>Previsão para segunda-feira</h1>
	<p>
		Em Portugal, os preços mudam sobretudo à segunda-feira e acompanham os mercados internacionais da semana anterior.
		Com as cotações da gasolina e do gasóleo no porto de Nova Iorque e o câmbio do euro, dá para estimar quanto deve mudar
		o preço na próxima segunda. É uma estimativa: os postos decidem os preços, e o Governo pode mudar o ISP.
	</p>

	{#if erro}
		<p class="conclusao" role="alert">{erro}</p>
	{:else if !linhas}
		<p role="status">A carregar…</p>
	{:else if proxima.length}
		<h2>
			Segunda-feira, {quando(semana)}, com as cotações até {diaCurto(proxima[0].last_market_day)} ({Math.min(
				...proxima.map((r) => r.market_days_last_week)
			)} de 5 dias da semana).
		</h2>
		<div class="cartoes">
			{#each proxima as r (r.product)}
				<div class="cartao">
					<span class="cartao-titulo">{r.product_name}</span>
					<span class="cartao-numero {r.predicted_change < 0 ? 'seta-baixo' : r.predicted_change > 0 ? 'seta-cima' : ''}"
						>{centimos(r.predicted_change)}</span
					>
				</div>
			{/each}
		</div>
		<p>
			Mudança prevista no preço por litro, com IVA, sem contar com uma eventual mudança do ISP. Com menos de 5 dias de
			cotações, a previsão ainda pode mudar até ao fim da semana.
		</p>

		<h2>Na própria segunda-feira, segundo os postos</h2>
		<p>
			O boletim europeu só sai à quinta-feira. Mas a fotografia da DGEG de segunda de manhã já tem os preços novos de cada
			posto. Por isso, a previsão compara-se também com a mudança média dos postos, no próprio dia (só os postos com o preço
			atualizado nas duas fotografias; ISP incluído).
		</p>
		{#if naSegunda.length}
			<div class="rolar">
				<table class="tabela">
					<thead>
						<tr><th>Segunda-feira</th><th>Combustível</th><th class="num">Prevista (cêntimos)</th><th class="num">Nos postos (cêntimos)</th><th class="num">Diferença</th><th class="num">Postos</th><th class="num">Mudaram de preço</th></tr>
					</thead>
					<tbody>
						{#each naSegunda as r (r.target_week + r.product)}
							<tr>
								<td>{quando(r.target_week)}</td>
								<td>{r.product_name}</td>
								<td class="num">{centimos(r.predicted_change, '')}</td>
								<td class="num">{centimos(r.dgeg_change, '')}</td>
								<td class="num">{centimos(r.predicted_change - r.dgeg_change, '')}</td>
								<td class="num">{inteiro(r.dgeg_stations)}</td>
								<td class="num">{pct(r.dgeg_share_changed, 0)}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{:else}
			<p>A primeira comparação é a de segunda-feira, 2/11/2026: as fotografias da DGEG começaram a 28/10.</p>
		{/if}

		<h2>Como se tem saído</h2>
		{#if acerto.length}
			<div class="rolar">
				<table class="tabela">
					<thead>
						<tr><th>Combustível</th><th class="num">Semanas</th><th class="num">Erro médio (cêntimos)</th><th class="num">Erro a dizer "fica igual"</th><th class="num">Acerta se sobe ou desce</th></tr>
					</thead>
					<tbody>
						{#each acerto as a (a.nome)}
							<tr>
								<td>{a.nome}</td>
								<td class="num">{inteiro(a.semanas)}</td>
								<td class="num">{(a.erro * 100).toLocaleString('pt-PT', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}</td>
								<td class="num">{(a.semPrevisao * 100).toLocaleString('pt-PT', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}</td>
								<td class="num">{pct(a.sentido, 0)}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{:else}
			<p>Ainda não há semanas para comparar.</p>
		{/if}
		<p>
			A previsão compara-se com a mudança do preço com impostos que o boletim europeu publicou para Portugal, ISP incluído.
			Os coeficientes foram ajustados com as semanas de 2012 a 2023; as semanas acima são todas posteriores, por isso o erro
			é o de uma previsão a sério.
		</p>
		{#each barras.filter((b) => b.categorias.length) as b (b.titulo)}
			<GraficoBarras titulo={b.titulo} categorias={b.categorias} series={b.series} formato={um} />
		{/each}

		<h2>Como se calcula</h2>
		<p>
			Para cada combustível, a mudança do preço sem impostos à segunda-feira é uma parte da mudança da cotação média em Nova
			Iorque na semana anterior, mais uma parte da mudança da semana antes dessa. As duas partes ajustam-se com os dados de
			2012 a 2023 (mínimos quadrados), e o IVA junta-se no fim. As cotações estão em dólares por galão e passam a euros por
			1000 L com o câmbio do dia.
		</p>
		<ul>
			<li>
				<strong>Porque não o Brent:</strong> testou-se também com o preço do petróleo, e o erro é maior. A gasolina e o gasóleo
				já refinados acompanham melhor os preços em Portugal.
			</li>
			<li>
				<strong>Limites:</strong> os preços de Portugal seguem as cotações do noroeste da Europa, e não as de Nova Iorque, que
				são as que estão disponíveis de graça; o FRED publica-as com uns dias de atraso; e o ISP pode mudar à segunda-feira, o
				que a previsão não tenta adivinhar.
			</li>
		</ul>
		<p class="fonte">
			Fontes: cotações e câmbio do FRED, Federal Reserve Bank of St. Louis (U.S. Energy Information Administration e Federal
			Reserve); preços de Portugal do Weekly Oil Bulletin da Comissão Europeia.
		</p>
	{/if}

	<Rodape />
</main>
