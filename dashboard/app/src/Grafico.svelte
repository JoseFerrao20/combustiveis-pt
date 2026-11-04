<!--
	Um gráfico de linhas em SVG, sem bibliotecas: as séries partilham o eixo das datas (as
	fotografias) e o dos preços. Para os leitores de ecrã, o desenho fica escondido e os valores
	estão numa tabela (sr-only) com as mesmas séries.

	`series`: [{ nome, cor, pontos: [{ x: 'AAAA-MM-DD', y: número }] }]
-->
<script>
	import { diaCurto, euros } from './formatos.js';

	export let titulo;
	export let series = [];
	export let formato = euros;

	/** A largura do ecrã (medida), para o texto ficar sempre do mesmo tamanho. */
	let LARGURA = 720;
	const ALTURA = 260;
	const M = { cima: 12, baixo: 28, esquerda: 64, direita: 12 };

	$: datas = [...new Set(series.flatMap((s) => s.pontos.map((p) => p.x)))].sort();
	$: valores = series.flatMap((s) => s.pontos.map((p) => p.y)).filter((v) => v != null);
	$: min = Math.min(...valores);
	$: max = Math.max(...valores);
	$: folga = (max - min) * 0.08 || 0.01;
	$: y0 = min - folga;
	$: y1 = max + folga;
	$: x = (data) =>
		M.esquerda + (datas.length < 2 ? 0.5 : datas.indexOf(data) / (datas.length - 1)) * (LARGURA - M.esquerda - M.direita);
	$: y = (valor) => M.cima + (1 - (valor - y0) / (y1 - y0)) * (ALTURA - M.cima - M.baixo);
	$: marcas = [0, 0.5, 1].map((t) => y0 + t * (y1 - y0));
	// No máximo uns 6 rótulos de datas, para não se atropelarem (nem com o último).
	$: passo = Math.max(1, Math.ceil(datas.length / 6));
</script>

<figure class="grafico" bind:clientWidth={LARGURA}>
	<figcaption class="grafico-titulo">{titulo}</figcaption>
	<svg width={LARGURA} height={ALTURA} viewBox="0 0 {LARGURA} {ALTURA}" aria-hidden="true">
		{#each marcas as marca}
			<line x1={M.esquerda} x2={LARGURA - M.direita} y1={y(marca)} y2={y(marca)} class="grelha" />
			<text x={M.esquerda - 6} y={y(marca) + 4} text-anchor="end" class="eixo">{formato(marca)}</text>
		{/each}
		{#each datas as data, i}
			{#if i === datas.length - 1 || (i % passo === 0 && datas.length - 1 - i >= passo / 2)}
				<text x={x(data)} y={ALTURA - 8} text-anchor="middle" class="eixo">{diaCurto(data)}</text>
			{/if}
		{/each}
		{#each series as serie (serie.nome)}
			{@const pontos = serie.pontos.filter((p) => p.y != null)}
			<polyline
				points={pontos.map((p) => `${x(p.x)},${y(p.y)}`).join(' ')}
				fill="none"
				stroke={serie.cor}
				stroke-width="2.5"
				vector-effect="non-scaling-stroke"
			/>
			{#each pontos as p}
				<circle cx={x(p.x)} cy={y(p.y)} r="3" fill={serie.cor} />
			{/each}
		{/each}
	</svg>
	<ul class="legenda-grafico" aria-hidden="true">
		{#each series as serie (serie.nome)}
			<li><span class="cor" style="background: {serie.cor}" />{serie.nome}</li>
		{/each}
	</ul>
	<!-- A classe na div, não na tabela: uma tabela não encolhe para 1 px e alargava a página. -->
	<div class="sr-only"><table>
		<caption>{titulo}</caption>
		<thead>
			<tr>
				<th>Dia</th>
				{#each series as serie (serie.nome)}<th>{serie.nome}</th>{/each}
			</tr>
		</thead>
		<tbody>
			{#each datas as data}
				<tr>
					<td>{diaCurto(data)}</td>
					{#each series as serie (serie.nome)}
						<td>{formato(serie.pontos.find((p) => p.x === data)?.y)}</td>
					{/each}
				</tr>
			{/each}
		</tbody>
	</table></div>
</figure>

<style>
	.grafico {
		margin: 0.75rem 0 1.25rem;
	}
	.grafico-titulo {
		font-weight: 600;
		font-size: 0.9rem;
		margin-bottom: 0.25rem;
	}
	svg {
		display: block;
		overflow: visible;
	}
	.grelha {
		stroke: var(--linha);
		stroke-width: 1;
	}
	.eixo {
		fill: var(--suave);
		font-size: 12px;
	}
	.legenda-grafico {
		display: flex;
		flex-wrap: wrap;
		gap: 0.25rem 1rem;
		list-style: none;
		padding: 0;
		font-size: 0.85rem;
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
