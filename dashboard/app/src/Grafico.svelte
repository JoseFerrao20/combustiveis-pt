<!--
	Um gráfico de linhas (ou de áreas empilhadas) em SVG, sem bibliotecas: as séries partilham o
	eixo das datas e o dos valores. Para os leitores de ecrã, o desenho fica escondido e os valores
	estão numa tabela (sr-only) com as mesmas séries: com muitas datas (o boletim tem semanas desde
	2005), a tabela tem a média de cada ano.

	`series`: [{ nome, cor, pontos: [{ x: 'AAAA-MM-DD', y: número }] }]
	`empilhado`: as séries somam-se (áreas), pela ordem dada, de baixo para cima.
	`minimo`: o valor de baixo do eixo (por omissão, um pouco abaixo do mínimo dos dados).
-->
<script>
	import { diaCurto, euros } from './formatos.js';

	export let titulo;
	export let series = [];
	export let formato = euros;
	export let empilhado = false;
	export let minimo = null;

	/** A largura do ecrã (medida), para o texto ficar sempre do mesmo tamanho. */
	let LARGURA = 720;
	const ALTURA = 260;
	const M = { cima: 12, baixo: 28, esquerda: 64, direita: 12 };
	/** A partir daqui, sem um círculo em cada ponto, rótulos por ano e a tabela por ano. */
	const MUITAS = 60;

	$: datas = [...new Set(series.flatMap((s) => s.pontos.map((p) => p.x)))].sort();
	$: indice = new Map(datas.map((data, i) => [data, i]));
	$: longa = datas.length > MUITAS;
	// Nas áreas empilhadas, cada série começa onde acaba a de baixo.
	$: camadas = empilhar(series, datas, empilhado);
	function empilhar(series, datas, empilhado) {
		if (!empilhado) return series.map((s) => ({ ...s, base: null }));
		const soma = new Map(datas.map((d) => [d, 0]));
		return series.map((s) => {
			const valores = new Map(s.pontos.map((p) => [p.x, p.y ?? 0]));
			const base = datas.map((d) => soma.get(d));
			const pontos = datas.map((d) => {
				soma.set(d, soma.get(d) + (valores.get(d) ?? 0));
				return { x: d, y: soma.get(d) };
			});
			return { ...s, base, pontos };
		});
	}
	$: valores = camadas.flatMap((s) => s.pontos.map((p) => p.y)).filter((v) => v != null);
	$: min = empilhado ? 0 : Math.min(...valores);
	$: max = Math.max(...valores);
	$: folga = (max - min) * 0.08 || 0.01;
	$: y0 = minimo ?? (empilhado ? 0 : min - folga);
	$: y1 = max + folga;
	$: x = (data) =>
		M.esquerda + (datas.length < 2 ? 0.5 : indice.get(data) / (datas.length - 1)) * (LARGURA - M.esquerda - M.direita);
	$: y = (valor) => M.cima + (1 - (valor - y0) / (y1 - y0)) * (ALTURA - M.cima - M.baixo);
	$: marcas = [0, 0.5, 1].map((t) => y0 + t * (y1 - y0));
	// Os rótulos das datas: uns 6, sem se atropelarem (nem com o último); numa série longa, o
	// ano, na primeira data de cada ano.
	$: rotulos = longa ? rotulosPorAno(datas) : rotulosPorPasso(datas);
	function rotulosPorPasso(datas) {
		const passo = Math.max(1, Math.ceil(datas.length / 6));
		return datas
			.map((data, i) => ({ data, texto: diaCurto(data), i }))
			.filter(({ i }) => i === datas.length - 1 || (i % passo === 0 && datas.length - 1 - i >= passo / 2));
	}
	function rotulosPorAno(datas) {
		const anos = [];
		for (const data of datas) {
			const ano = data.slice(0, 4);
			if (anos.at(-1)?.texto !== ano) anos.push({ data, texto: ano });
		}
		const passo = Math.max(1, Math.ceil(anos.length / 6));
		return anos.filter((_, i) => i % passo === 0);
	}
	// x e y vão como argumentos: assim, o desenho segue a largura medida (o Svelte só repete o que
	// depende do que está escrito no próprio template).
	function caminho(pontos, x, y) {
		return pontos.map((p) => `${x(p.x)},${y(p.y)}`).join(' ');
	}
	function area(camada, x, y) {
		const cima = camada.pontos.map((p) => `${x(p.x)},${y(p.y)}`);
		const baixo = datas.map((d, i) => `${x(d)},${y(camada.base[i])}`).reverse();
		return [...cima, ...baixo].join(' ');
	}

	// A tabela para os leitores de ecrã: cada data, ou a média de cada ano numa série longa.
	$: linhasTabela = longa ? porAno(series) : datas.map((data) => ({ rotulo: diaCurto(data), valores: series.map((s) => s.pontos.find((p) => p.x === data)?.y) }));
	function porAno(series) {
		const anos = [...new Set(datas.map((d) => d.slice(0, 4)))];
		return anos.map((ano) => ({
			rotulo: ano,
			valores: series.map((s) => {
				const doAno = s.pontos.filter((p) => p.x.startsWith(ano) && p.y != null).map((p) => p.y);
				return doAno.length ? doAno.reduce((a, b) => a + b, 0) / doAno.length : null;
			})
		}));
	}
</script>

<figure class="grafico" bind:clientWidth={LARGURA}>
	<figcaption class="grafico-titulo">{titulo}</figcaption>
	<svg width={LARGURA} height={ALTURA} viewBox="0 0 {LARGURA} {ALTURA}" aria-hidden="true">
		{#each marcas as marca}
			<line x1={M.esquerda} x2={LARGURA - M.direita} y1={y(marca)} y2={y(marca)} class="grelha" />
			<text x={M.esquerda - 6} y={y(marca) + 4} text-anchor="end" class="eixo">{formato(marca)}</text>
		{/each}
		{#each rotulos as rotulo (rotulo.data)}
			<text x={x(rotulo.data)} y={ALTURA - 8} text-anchor={longa ? 'start' : 'middle'} class="eixo">{rotulo.texto}</text>
		{/each}
		{#if empilhado}
			{#each camadas as camada (camada.nome)}
				<polygon points={area(camada, x, y)} fill={camada.cor} fill-opacity="0.85" />
			{/each}
		{:else}
			<!-- Ao contrário, para a primeira série (a principal) ficar por cima quando coincidem. -->
			{#each [...camadas].reverse() as serie (serie.nome)}
				{@const pontos = serie.pontos.filter((p) => p.y != null)}
				<polyline
					points={caminho(pontos, x, y)}
					fill="none"
					stroke={serie.cor}
					stroke-width={longa ? 1.75 : 2.5}
					stroke-linejoin="round"
					vector-effect="non-scaling-stroke"
				/>
				{#if !longa}
					{#each pontos as p}
						<circle cx={x(p.x)} cy={y(p.y)} r="3" fill={serie.cor} />
					{/each}
				{/if}
			{/each}
		{/if}
	</svg>
	<ul class="legenda-grafico" aria-hidden="true">
		{#each series as serie (serie.nome)}
			<li><span class="cor" style="background: {serie.cor}" />{serie.nome}</li>
		{/each}
	</ul>
	<!-- A classe na div, não na tabela: uma tabela não encolhe para 1 px e alargava a página. -->
	<div class="sr-only"><table>
		<caption>{titulo}{longa ? ' (média de cada ano)' : ''}</caption>
		<thead>
			<tr>
				<th>{longa ? 'Ano' : 'Dia'}</th>
				{#each series as serie (serie.nome)}<th>{serie.nome}</th>{/each}
			</tr>
		</thead>
		<tbody>
			{#each linhasTabela as linha (linha.rotulo)}
				<tr>
					<td>{linha.rotulo}</td>
					{#each linha.valores as valor}<td>{formato(valor)}</td>{/each}
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
