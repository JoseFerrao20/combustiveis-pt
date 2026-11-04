<!--
	Barras agrupadas em SVG (a previsão contra a mudança real, semana a semana), com valores
	positivos e negativos à volta do zero. Os valores ficam também numa tabela para os leitores de
	ecrã.

	`categorias`: ['AAAA-MM-DD', …]; `series`: [{ nome, cor, valores: [número | null, …] }]
	(um valor por categoria, pela mesma ordem).
-->
<script>
	import { diaCurto } from './formatos.js';

	export let titulo;
	export let categorias = [];
	export let series = [];
	export let formato = (v) => (v == null ? '–' : v.toLocaleString('pt-PT', { maximumFractionDigits: 1 }));

	let LARGURA = 720;
	const ALTURA = 240;
	const M = { cima: 12, baixo: 28, esquerda: 48, direita: 8 };

	$: valores = series.flatMap((s) => s.valores).filter((v) => v != null);
	$: alto = Math.max(0.5, ...valores);
	$: baixo = Math.min(-0.5, ...valores);
	$: y = (v) => M.cima + ((alto - v) / (alto - baixo)) * (ALTURA - M.cima - M.baixo);
	$: largo = (LARGURA - M.esquerda - M.direita) / Math.max(1, categorias.length);
	$: barra = Math.max(1, (largo * 0.8) / Math.max(1, series.length));
	$: passo = Math.max(1, Math.ceil(categorias.length / 6));
	$: marcas = [baixo, 0, alto];
</script>

<figure class="grafico" bind:clientWidth={LARGURA}>
	<figcaption class="grafico-titulo">{titulo}</figcaption>
	<svg width={LARGURA} height={ALTURA} viewBox="0 0 {LARGURA} {ALTURA}" aria-hidden="true">
		{#each marcas as marca}
			<line x1={M.esquerda} x2={LARGURA - M.direita} y1={y(marca)} y2={y(marca)} class:zero={marca === 0} class="grelha" />
			<text x={M.esquerda - 6} y={y(marca) + 4} text-anchor="end" class="eixo">{formato(marca)}</text>
		{/each}
		{#each categorias as categoria, i (categoria)}
			{@const inicio = M.esquerda + i * largo + largo * 0.1}
			{#each series as serie, j (serie.nome)}
				{@const v = serie.valores[i]}
				{#if v != null}
					<rect
						x={inicio + j * barra}
						y={Math.min(y(v), y(0))}
						width={Math.max(1, barra - 1)}
						height={Math.max(1, Math.abs(y(v) - y(0)))}
						fill={serie.cor}
					/>
				{/if}
			{/each}
			{#if i % passo === 0}
				<text x={inicio} y={ALTURA - 8} class="eixo">{diaCurto(categoria)}</text>
			{/if}
		{/each}
	</svg>
	<ul class="legenda-grafico" aria-hidden="true">
		{#each series as serie (serie.nome)}
			<li><span class="cor" style="background: {serie.cor}" />{serie.nome}</li>
		{/each}
	</ul>
	<div class="sr-only"><table>
		<caption>{titulo}</caption>
		<thead><tr><th>Semana</th>{#each series as serie (serie.nome)}<th>{serie.nome}</th>{/each}</tr></thead>
		<tbody>
			{#each categorias as categoria, i (categoria)}
				<tr><td>{diaCurto(categoria)}</td>{#each series as serie (serie.nome)}<td>{formato(serie.valores[i])}</td>{/each}</tr>
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
	.grelha.zero {
		stroke: var(--suave);
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
