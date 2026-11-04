<!--
	Os postos acompanhados (antes uma página do Evidence, ADR 0006): cada posto do
	seed tracked_stations, fotografia a fotografia, face aos concorrentes a 5 km e à média do
	concelho. Lê dados/acompanhados.json (`combustiveis site`). ADR 0006.
-->
<script>
	import { onDestroy, onMount, tick } from 'svelte';
	import 'leaflet/dist/leaflet.css';
	import Cabecalho from '../../components/Cabecalho.svelte';
	import Rodape from '../../components/Rodape.svelte';
	import Grafico from './Grafico.svelte';
	import { BASE, combustivelGuardado, euros, inteiro, lerJson, quando, seta } from './formatos.js';

	let dados = null;
	let erro = '';
	let posto = null;
	let combustivel = combustivelGuardado();

	onMount(async () => {
		try {
			dados = await lerJson('acompanhados.json');
			posto = dados.history[0]?.station_id ?? null;
		} catch {
			erro = 'Não foi possível carregar os postos acompanhados. Tente outra vez daqui a pouco.';
		}
	});

	$: postos = dados ? [...new Map(dados.history.map((r) => [r.station_id, r.label]))] : [];
	$: combustiveis = dados
		? [...new Map(dados.history.filter((r) => r.station_id === posto).map((r) => [r.fuel, r.fuel_name]))]
		: [];
	$: if (combustiveis.length && !combustiveis.some(([f]) => f === combustivel)) combustivel = combustiveis[0][0];
	$: historico = dados
		? dados.history
				.filter((r) => r.station_id === posto && r.fuel === combustivel)
				.sort((a, b) => a.snapshot_date.localeCompare(b.snapshot_date))
		: [];
	$: hoje = historico[historico.length - 1];
	$: vsConcorrentes = hoje && hoje.competitors_avg_price != null ? seta(hoje.price - hoje.competitors_avg_price) : null;
	$: vsConcelho = hoje && hoje.municipality_avg_price != null ? seta(hoje.price - hoje.municipality_avg_price) : null;
	$: concorrentes = dados ? dados.competitors.filter((r) => r.station_id === posto && r.fuel === combustivel) : [];
	$: series = [
		{ nome: 'Este posto', cor: '#b91c1c', pontos: historico.map((r) => ({ x: r.snapshot_date, y: r.price })) },
		{ nome: 'Mais barato a 5 km', cor: '#d97706', pontos: historico.map((r) => ({ x: r.snapshot_date, y: r.competitors_min_price })) },
		{ nome: 'Média a 5 km', cor: '#2563eb', pontos: historico.map((r) => ({ x: r.snapshot_date, y: r.competitors_avg_price })) },
		{ nome: 'Média do concelho', cor: '#64748b', pontos: historico.map((r) => ({ x: r.snapshot_date, y: r.municipality_avg_price })) }
	];

	// O mapa: o posto a vermelho e os concorrentes com a cor do preço (do mais barato ao mais caro).
	const COLORS = ['#1a9850', '#91cf60', '#fee08b', '#fc8d59', '#d73027'];
	let elemento;
	let L;
	let mapa;
	let camada;
	function cor(preco, precos) {
		const ordenados = [...precos].sort((a, b) => a - b);
		const limites = [0.2, 0.4, 0.6, 0.8].map((q) => ordenados[Math.floor(q * (ordenados.length - 1))]);
		const i = limites.findIndex((limite) => preco <= limite);
		return COLORS[i === -1 ? COLORS.length - 1 : i];
	}
	async function desenhar() {
		await tick();
		if (!elemento || !hoje) return;
		if (!L) L = (await import('leaflet')).default;
		if (!mapa) {
			mapa = L.map(elemento, { scrollWheelZoom: false });
			L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
				attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
				maxZoom: 18
			}).addTo(mapa);
			camada = L.layerGroup().addTo(mapa);
		}
		camada.clearLayers();
		const precos = concorrentes.map((r) => r.price);
		const pontos = [[hoje.latitude, hoje.longitude]];
		for (const r of concorrentes) {
			if (r.latitude == null) continue;
			pontos.push([r.latitude, r.longitude]);
			L.circleMarker([r.latitude, r.longitude], { radius: 6, weight: 1, color: '#ffffff', fillColor: cor(r.price, precos), fillOpacity: 0.9 })
				.bindTooltip(`${r.station_name}: ${euros(r.price)} (${r.distance_km.toLocaleString('pt-PT')} km)`)
				.addTo(camada);
		}
		L.circleMarker([hoje.latitude, hoje.longitude], { radius: 9, weight: 2, color: '#ffffff', fillColor: '#b91c1c', fillOpacity: 1 })
			.bindTooltip(`${hoje.station_name}: ${euros(hoje.price)}`)
			.addTo(camada);
		mapa.fitBounds(L.latLngBounds(pontos), { padding: [20, 20], maxZoom: 14 });
	}
	$: if (hoje && concorrentes) desenhar();
	onDestroy(() => mapa?.remove());
</script>

<svelte:head><title>Postos acompanhados | Combustíveis em Portugal</title></svelte:head>

<Cabecalho base={BASE} atual="{BASE}acompanhados/" />

<main class="pagina">
	<h1>Postos acompanhados</h1>
	<p>Alguns postos seguidos semana a semana, comparados com os concorrentes a 5 km e com a média do concelho.</p>

	{#if erro}
		<p class="conclusao" role="alert">{erro}</p>
	{:else if !dados}
		<p role="status">A carregar…</p>
	{:else}
		<div class="filtros-pagina">
			<label>
				Posto
				<select bind:value={posto}>
					{#each postos as [id, nome] (id)}<option value={id}>{nome}</option>{/each}
				</select>
			</label>
			<label>
				Combustível
				<select bind:value={combustivel}>
					{#each combustiveis as [id, nome] (id)}<option value={id}>{nome}</option>{/each}
				</select>
			</label>
		</div>

		{#if hoje}
			<h2>{hoje.station_name}</h2>
			<p>
				{hoje.location}, concelho de {hoje.municipality}. Preço atualizado a {quando(hoje.updated_at, true)}, na
				fotografia de {quando(hoje.snapshot_date)}.
			</p>
			<div class="cartoes">
				<div class="cartao"><span class="cartao-titulo">Preço</span><span class="cartao-numero">{euros(hoje.price)}</span></div>
				<div class="cartao">
					<span class="cartao-titulo">Posição entre os postos a 5 km</span>
					<span class="cartao-numero">{hoje.rank_5km ?? '–'}º de {inteiro((hoje.competitors ?? 0) + 1)}</span>
					<span class="cartao-texto">1º é o mais barato</span>
				</div>
				{#if vsConcorrentes}
					<div class="cartao">
						<span class="cartao-titulo">Face à média a 5 km</span>
						<span class="cartao-numero {vsConcorrentes.classe}">{vsConcorrentes.texto}</span>
						<span class="cartao-texto">por litro</span>
					</div>
				{/if}
				{#if vsConcelho}
					<div class="cartao">
						<span class="cartao-titulo">Face à média do concelho</span>
						<span class="cartao-numero {vsConcelho.classe}">{vsConcelho.texto}</span>
						<span class="cartao-texto">por litro</span>
					</div>
				{/if}
			</div>

			<h2>Ao longo do tempo</h2>
			{#if historico.length >= 2}
				<Grafico titulo="Preço por litro" {series} />
			{:else}
				<p>O gráfico aparece quando houver mais fotografias.</p>
			{/if}
			<details class="mais-detalhes">
				<summary>Ver os preços de cada fotografia</summary>
				<div class="rolar">
					<table class="tabela">
						<thead>
							<tr><th>Fotografia</th><th class="num">Preço</th><th class="num">Posição a 5 km</th><th class="num">Mais barato a 5 km</th><th class="num">Média a 5 km</th><th class="num">Média do concelho</th><th>Atualizado</th></tr>
						</thead>
						<tbody>
							{#each [...historico].reverse() as r (r.snapshot_date)}
								<tr>
									<td>{quando(r.snapshot_date)}</td>
									<td class="num">{euros(r.price)}</td>
									<td class="num">{r.rank_5km ?? '–'}</td>
									<td class="num">{euros(r.competitors_min_price)}</td>
									<td class="num">{euros(r.competitors_avg_price)}</td>
									<td class="num">{euros(r.municipality_avg_price)}</td>
									<td>{quando(r.updated_at, true)}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			</details>

			<h2>Os concorrentes a 5 km</h2>
			<p>O posto acompanhado é o ponto vermelho; os concorrentes têm a cor do preço, do verde (mais barato) ao vermelho.</p>
			<div bind:this={elemento} class="mapa-acompanhados" aria-label="Mapa do posto e dos concorrentes" role="region" />
			{#if concorrentes.length}
				<div class="rolar">
					<table class="tabela">
						<thead><tr><th>Posto</th><th>Marca</th><th class="num">Distância</th><th class="num">Preço</th><th>Atualizado</th></tr></thead>
						<tbody>
							{#each concorrentes as r (r.competitor_id)}
								<tr>
									<td>{r.station_name}</td>
									<td>{r.brand}</td>
									<td class="num">{r.distance_km.toLocaleString('pt-PT', { maximumFractionDigits: 1 })} km</td>
									<td class="num">{euros(r.price)}</td>
									<td>{quando(r.updated_at, true)}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{:else}
				<p>Nenhum concorrente a 5 km com este combustível.</p>
			{/if}
			<p>
				Distâncias em linha reta. A posição conta os concorrentes a 5 km com o mesmo combustível e o preço atualizado nos
				últimos 30 dias; um empate não conta como mais barato.
			</p>
		{:else}
			<p>Este posto não tem preço deste combustível.</p>
		{/if}
	{/if}

	<Rodape>
		<p>
			Fonte: Direção-Geral de Energia e Geologia, Preços dos Combustíveis Online. Preços comunicados pelos postos, com a
			data e hora de atualização de cada um. Para acompanhar outro posto, basta juntá-lo ao seed
			<code>tracked_stations</code> do projeto.
		</p>
	</Rodape>
</main>

<style>
	.mapa-acompanhados {
		height: min(450px, 60vh);
		border: 1px solid var(--linha);
		border-radius: 0.25rem;
		margin: 0.5rem 0 1rem;
		isolation: isolate;
		z-index: 0;
	}
</style>
