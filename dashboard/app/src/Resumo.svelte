<!--
	O resumo e as estatísticas dos postos (antes uma página do Evidence, pages/resumo.md): as
	contas fazem-se no browser, com o mesmo JSON do combustível da página inicial
	(dados/postos-<combustível>.json) e a evolução (dados/evolucao.json). ADR 0006.
-->
<script>
	import { onMount } from 'svelte';
	import Cabecalho from '../../components/Cabecalho.svelte';
	import Rodape from '../../components/Rodape.svelte';
	import Grafico from './Grafico.svelte';
	import {
		BASE,
		centimos,
		combustivelGuardado,
		doDistrito,
		euros,
		guardarCombustivel,
		inteiro,
		lerJson,
		linhas,
		quando,
		slug
	} from './formatos.js';

	let resumo = null;
	let evolucao = [];
	let combustivel = combustivelGuardado();
	let distrito = '';
	let concelho = '';
	let postos = [];
	let erro = '';
	let concelhosMostrados = 15;

	const media = (lista) => (lista.length ? lista.reduce((s, r) => s + r.price, 0) / lista.length : null);
	const grupoPor = (lista, chave) => {
		const grupos = new Map();
		for (const r of lista) {
			const k = chave(r);
			if (!grupos.has(k)) grupos.set(k, []);
			grupos.get(k).push(r);
		}
		return [...grupos].map(([nome, rs]) => ({ nome, postos: rs.length, media: media(rs), linhas: rs }));
	};

	onMount(async () => {
		try {
			resumo = await lerJson('resumo.json');
			if (!resumo.fuels.some((f) => f.fuel === combustivel)) combustivel = resumo.fuels[0].fuel;
		} catch {
			erro = 'Não foi possível carregar os preços. Tente outra vez daqui a pouco.';
		}
		try {
			evolucao = (await lerJson('evolucao.json')).rows;
		} catch {
			evolucao = [];
		}
	});

	async function carregar(escolhido) {
		try {
			const ficheiro = await lerJson(`postos-${escolhido}.json`);
			if (escolhido === combustivel) postos = linhas(ficheiro);
		} catch {
			erro = 'Não foi possível carregar os preços. Tente outra vez daqui a pouco.';
		}
	}
	$: if (resumo) {
		carregar(combustivel);
		guardarCombustivel(combustivel);
	}
	$: concelhos = resumo
		? distrito
			? (resumo.districts[distrito] ?? [])
			: Object.values(resumo.districts).flat().sort((a, b) => a.localeCompare(b, 'pt'))
		: [];
	$: if (concelho && !concelhos.includes(concelho)) concelho = '';
	$: nomeCombustivel = resumo?.fuels.find((f) => f.fuel === combustivel)?.name ?? '';

	$: zona = postos.filter((r) => (!distrito || r.district === distrito) && (!concelho || r.municipality === concelho));
	$: mediaZona = media(zona);
	$: precos = zona.map((r) => r.price);

	// Grupos de marcas: a diferença para a média da zona, em cêntimos.
	$: grupos = grupoPor(zona, (r) => r.brand_segment ?? 'Outras marcas')
		.map((g) => ({ ...g, diferenca: g.media - mediaZona }))
		.sort((a, b) => a.diferenca - b.diferenca);
	$: maiorDiferenca = Math.max(0.001, ...grupos.map((g) => Math.abs(g.diferenca)));
	$: conclusao =
		grupos.length > 1 && grupos[0].diferenca < 0 && grupos[grupos.length - 1].diferenca > 0
			? `Na zona escolhida, ${grupos[0].nome.toLowerCase()} estão ${centimos(-grupos[0].diferenca, false).replace(' c', ' cêntimos')} abaixo da média, e ${grupos[grupos.length - 1].nome.toLowerCase()} ${centimos(grupos[grupos.length - 1].diferenca, false).replace(' c', ' cêntimos')} acima.`
			: '';
	$: tipos = grupoPor(zona, (r) => r.station_type ?? '–').sort((a, b) => a.media - b.media);
	$: marcas = grupoPor(zona, (r) => (r.brand === 'Genérico' ? 'Sem marca' : r.brand))
		.filter((g) => g.postos >= 3)
		.map((g) => ({ ...g, minimo: Math.min(...g.linhas.map((r) => r.price)), maximo: Math.max(...g.linhas.map((r) => r.price)) }))
		.sort((a, b) => a.media - b.media);
	$: porConcelho = grupoPor(
		postos.filter((r) => !distrito || r.district === distrito),
		(r) => `${r.municipality}|${r.district}`
	)
		.filter((g) => g.postos >= 3)
		.map((g) => {
			const [nome, distritoDoConcelho] = g.nome.split('|');
			return { ...g, nome, distrito: distritoDoConcelho, minimo: Math.min(...g.linhas.map((r) => r.price)) };
		})
		.sort((a, b) => a.media - b.media);
	$: porDistrito = grupoPor(postos, (r) => r.district).sort((a, b) => a.media - b.media);
	$: caros = [...zona].sort((a, b) => b.price - a.price || a.station_name.localeCompare(b.station_name)).slice(0, 10);

	// Concorrência: só os postos "normais" (sem autoestradas nem hipermercados), comparados com a
	// média do próprio concelho, pelo número de concorrentes a 5 km.
	const CLASSES = [
		{ nome: '0', ate: 0 },
		{ nome: '1 a 2', ate: 2 },
		{ nome: '3 a 5', ate: 5 },
		{ nome: '6 a 10', ate: 10 },
		{ nome: '11 ou mais', ate: Infinity }
	];
	$: mediasConcelho = new Map(grupoPor(postos, (r) => r.municipality).map((g) => [g.nome, g.media]));
	$: normais = postos
		.filter((r) => r.station_type === 'Outro' && r.competitors_5km != null)
		.map((r) => ({ ...r, vsConcelho: r.price - mediasConcelho.get(r.municipality) }));
	$: concorrencia = CLASSES.map((c, i) => {
		const desde = i === 0 ? 0 : CLASSES[i - 1].ate + 1;
		const rs = normais.filter((r) => r.competitors_5km >= desde && r.competitors_5km <= c.ate);
		return { nome: c.nome, postos: rs.length, diferenca: rs.length ? rs.reduce((s, r) => s + r.vsConcelho, 0) / rs.length : null };
	});
	$: maiorConcorrencia = Math.max(0.001, ...concorrencia.map((c) => Math.abs(c.diferenca ?? 0)));

	const CORES = ['#2563eb', '#d97706', '#15803d', '#b91c1c', '#7c3aed', '#64748b'];
	$: seriesEvolucao = (() => {
		const rs = evolucao.filter((r) => r.fuel === combustivel);
		const nomes = [...new Set(rs.map((r) => r.label))];
		return nomes.map((nome, i) => ({
			nome,
			cor: CORES[i % CORES.length],
			pontos: rs.filter((r) => r.label === nome).map((r) => ({ x: r.snapshot_date, y: r.avg_price }))
		}));
	})();
	$: fotografias = new Set(evolucao.filter((r) => r.fuel === combustivel).map((r) => r.snapshot_date)).size;
	$: ultimaAtualizacao = zona.reduce((m, r) => (r.updated_at > m ? r.updated_at : m), '');
</script>

<svelte:head><title>Resumo e estatísticas | Combustíveis em Portugal</title></svelte:head>

<Cabecalho base={BASE} atual="{BASE}resumo/" />

<main class="pagina">
	<h1>Resumo e estatísticas</h1>
	<p>
		As médias dos postos de Portugal continental (fotografia de segunda-feira da DGEG) por grupo de marcas,
		marca, distrito e concelho, a concorrência e a evolução. O preço de cada posto está na
		<a href={BASE}>página inicial</a>.
	</p>

	<div class="filtros-pagina">
		<label>
			Combustível
			<select bind:value={combustivel} disabled={!resumo}>
				{#each resumo?.fuels ?? [] as fuel}<option value={fuel.fuel}>{fuel.name}</option>{/each}
			</select>
		</label>
		<label>
			Distrito
			<select bind:value={distrito} disabled={!resumo}>
				<option value="">Todos</option>
				{#each Object.keys(resumo?.districts ?? {}) as nome}<option value={nome}>{nome}</option>{/each}
			</select>
		</label>
		<label>
			Concelho
			<select bind:value={concelho} disabled={!resumo}>
				<option value="">Todos</option>
				{#each concelhos as nome}<option value={nome}>{nome}</option>{/each}
			</select>
		</label>
	</div>

	{#if erro}
		<p class="conclusao" role="alert">{erro}</p>
	{:else if !postos.length}
		<p role="status">A carregar os preços…</p>
	{:else}
		<h2>Resumo de {quando(resumo.snapshot_date)}</h2>
		<div class="cartoes">
			<div class="cartao"><span class="cartao-titulo">Postos</span><span class="cartao-numero">{inteiro(zona.length)}</span></div>
			<div class="cartao"><span class="cartao-titulo">Preço médio</span><span class="cartao-numero">{euros(mediaZona)}</span></div>
			<div class="cartao"><span class="cartao-titulo">Mais barato</span><span class="cartao-numero">{euros(Math.min(...precos))}</span></div>
			<div class="cartao"><span class="cartao-titulo">Mais caro</span><span class="cartao-numero">{euros(Math.max(...precos))}</span></div>
		</div>
		<p>
			Os preços são os que cada posto comunica à Direção-Geral de Energia e Geologia
			(<a href="https://precoscombustiveis.dgeg.gov.pt">precoscombustiveis.dgeg.gov.pt</a>); as médias usam só os
			atualizados nos últimos 30 dias.
		</p>

		<h2>Por grupo de marcas</h2>
		{#if conclusao}<p class="conclusao">{conclusao}</p>{/if}
		<p class="sr-only">Diferença para o preço médio da zona, em cêntimos por litro:</p>
		<ul class="barras" aria-label="Diferença para o preço médio da zona escolhida, em cêntimos por litro">
			{#each grupos as g (g.nome)}
				<li>
					<span class="barra-nome">{g.nome}</span>
					<span class="barra-eixo">
						<span
							class="barra {g.diferenca < 0 ? 'negativa' : 'positiva'}"
							style="width: {(Math.abs(g.diferenca) / maiorDiferenca) * 50}%"
						/>
					</span>
					<span class="barra-valor">{centimos(g.diferenca)}</span>
				</li>
			{/each}
		</ul>
		<details class="mais-detalhes">
			<summary>Ver a tabela dos grupos de marcas</summary>
			<table class="tabela">
				<thead><tr><th>Grupo de marcas</th><th class="num">Postos</th><th class="num">Preço médio</th><th class="num">Diferença</th></tr></thead>
				<tbody>
					{#each grupos as g (g.nome)}
						<tr><td>{g.nome}</td><td class="num">{inteiro(g.postos)}</td><td class="num">{euros(g.media)}</td><td class="num">{centimos(g.diferenca)}</td></tr>
					{/each}
				</tbody>
			</table>
		</details>
		<p>
			Os hiper e supermercados são Intermarché, Pingo Doce, Auchan, E.Leclerc e Recheio. As petrolíferas são Galp,
			Repsol, BP, Cepsa, Moeve, Shell, Esso e Q8. "Sem marca" são os postos que a DGEG regista como "Genérico".
		</p>
		<details class="mais-detalhes">
			<summary>Ver os preços por tipo de posto (autoestrada, hipermercado, outros)</summary>
			<table class="tabela">
				<thead><tr><th>Tipo de posto</th><th class="num">Postos</th><th class="num">Preço médio</th></tr></thead>
				<tbody>
					{#each tipos as t (t.nome)}
						<tr><td>{t.nome}</td><td class="num">{inteiro(t.postos)}</td><td class="num">{euros(t.media)}</td></tr>
					{/each}
				</tbody>
			</table>
		</details>

		<h2>Por marca</h2>
		{#if marcas.length}
			<div class="rolar">
				<table class="tabela">
					<thead><tr><th>Marca</th><th class="num">Postos</th><th class="num">Média</th><th class="num">Mínimo</th><th class="num">Máximo</th></tr></thead>
					<tbody>
						{#each marcas as m (m.nome)}
							<tr><td>{m.nome}</td><td class="num">{inteiro(m.postos)}</td><td class="num">{euros(m.media)}</td><td class="num">{euros(m.minimo)}</td><td class="num">{euros(m.maximo)}</td></tr>
						{/each}
					</tbody>
				</table>
			</div>
			<p>Só as marcas com pelo menos 3 postos na zona escolhida.</p>
		{:else}
			<p>Nenhuma marca com pelo menos 3 postos nesta zona.</p>
		{/if}

		<h2>Por concelho e por distrito</h2>
		<p>
			Os concelhos com pelo menos 3 postos{distrito ? ` do ${doDistrito(distrito)}` : ''}, do mais barato para o mais
			caro. Cada concelho tem uma página com os postos mais baratos.
		</p>
		<div class="rolar">
			<table class="tabela">
				<thead><tr><th>Concelho</th><th>Distrito</th><th class="num">Postos</th><th class="num">Média</th><th class="num">Mais barato</th></tr></thead>
				<tbody>
					{#each porConcelho.slice(0, concelhosMostrados) as c (c.nome + c.distrito)}
						<tr>
							<td><a href="{BASE}concelho/{slug(c.nome)}/">{c.nome}</a></td>
							<td>{c.distrito}</td>
							<td class="num">{inteiro(c.postos)}</td>
							<td class="num">{euros(c.media)}</td>
							<td class="num">{euros(c.minimo)}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
		{#if porConcelho.length > concelhosMostrados}
			<button type="button" class="botao-secundario" on:click={() => (concelhosMostrados = porConcelho.length)}>
				Mostrar os {porConcelho.length} concelhos
			</button>
		{/if}
		<details class="mais-detalhes">
			<summary>Ver os distritos</summary>
			<table class="tabela">
				<thead><tr><th>Distrito</th><th class="num">Postos</th><th class="num">Média</th></tr></thead>
				<tbody>
					{#each porDistrito as d (d.nome)}
						<tr><td>{d.nome}</td><td class="num">{inteiro(d.postos)}</td><td class="num">{euros(d.media)}</td></tr>
					{/each}
				</tbody>
			</table>
		</details>

		<h2>Os mais caros</h2>
		<p>Os mais baratos estão na <a href={BASE}>página inicial</a>.</p>
		<div class="rolar">
			<table class="tabela">
				<thead><tr><th>Posto</th><th>Marca</th><th>Concelho</th><th class="num">Preço</th><th>Atualizado</th></tr></thead>
				<tbody>
					{#each caros as r (r.station_id)}
						<tr><td>{r.station_name}</td><td>{r.brand}</td><td>{r.municipality}</td><td class="num">{euros(r.price)}</td><td>{quando(r.updated_at, true)}</td></tr>
					{/each}
				</tbody>
			</table>
		</div>

		<h2>Concorrência</h2>
		<p>
			Um posto sem concorrentes por perto pode cobrar mais? Para cada posto, conta-se quantos outros há num raio de 5 km
			(em linha reta) e compara-se o preço com a média do próprio concelho. Ficam de fora os postos de autoestrada e de
			hipermercado. Em todo o continente, com {nomeCombustivel.toLowerCase()}.
		</p>
		<ul class="barras" aria-label="Diferença para a média do concelho, em cêntimos por litro, pelo número de concorrentes a 5 km">
			{#each concorrencia as c (c.nome)}
				<li>
					<span class="barra-nome">{c.nome} {c.nome === '0' ? 'concorrentes' : ''}</span>
					<span class="barra-eixo">
						{#if c.diferenca != null}
							<span
								class="barra {c.diferenca < 0 ? 'negativa' : 'positiva'}"
								style="width: {(Math.abs(c.diferenca) / maiorConcorrencia) * 50}%"
							/>
						{/if}
					</span>
					<span class="barra-valor">{centimos(c.diferenca)} <span class="suave">({inteiro(c.postos)})</span></span>
				</li>
			{/each}
		</ul>
		<p>
			É uma fotografia de um dia: a análise com mais pormenor está em
			<a href="https://github.com/JoseFerrao20/combustiveis-pt/blob/main/docs/analises/concorrencia-postos.md">docs/analises</a>.
		</p>

		<h2>Ao longo do tempo</h2>
		{#if fotografias >= 2}
			<Grafico titulo="Preço médio por litro, por grupo de marcas ({nomeCombustivel})" series={seriesEvolucao} />
		{:else}
			<p>O gráfico aparece quando houver mais fotografias.</p>
		{/if}
		<p>
			A DGEG só mostra o preço em vigor: o histórico guarda-se aqui, com uma fotografia por semana, à segunda-feira (de
			28/10 a 2/11/2026, uma por dia). Os dados estão nos <a href="{BASE}dados-abertos/">dados abertos</a>.
		</p>
	{/if}

	<Rodape>
		<p>
			Fonte: Direção-Geral de Energia e Geologia, Preços dos Combustíveis Online. Preços comunicados pelos postos, com a
			data e hora de atualização de cada um.{#if ultimaAtualizacao}
				Última atualização recebida: {quando(ultimaAtualizacao, true)}.{/if}
		</p>
	</Rodape>
</main>

<style>
	.barras {
		list-style: none;
		padding: 0;
		margin: 0.75rem 0;
		max-width: 48rem;
	}
	.barras li {
		display: grid;
		grid-template-columns: minmax(8rem, 12rem) 1fr 6.5rem;
		align-items: center;
		gap: 0.5rem;
		padding: 0.2rem 0;
		font-size: 0.875rem;
	}
	.barra-eixo {
		position: relative;
		height: 1.25rem;
		border-left: 0;
		background: linear-gradient(to right, transparent calc(50% - 0.5px), var(--linha) calc(50% - 0.5px), var(--linha) calc(50% + 0.5px), transparent calc(50% + 0.5px));
	}
	.barra {
		position: absolute;
		top: 0.15rem;
		bottom: 0.15rem;
		border-radius: 0.2rem;
	}
	.barra.negativa {
		right: 50%;
		background: #15803d;
	}
	.barra.positiva {
		left: 50%;
		background: #d97706;
	}
	.barra-valor {
		text-align: right;
		font-variant-numeric: tabular-nums;
	}
	.suave {
		color: var(--suave);
	}
</style>
