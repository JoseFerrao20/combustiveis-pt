<!--
	Mapa dos postos com a tabela dos que se veem, do mais barato para o mais caro. A tabela
	acompanha o mapa: ao aproximar ou arrastar, fica só com os postos dentro do mapa. Os
	componentes de mapa do Evidence não dão os limites do mapa à página, por isso este usa o
	Leaflet diretamente (já vem com o Evidence), com os mosaicos do OpenStreetMap.

	"Perto de mim" usa a localização do browser (só depois de a pessoa autorizar; a posição
	fica no telemóvel) para centrar o mapa e mostrar a distância de cada posto. "Ir" abre o
	caminho até ao posto no Google Maps (no telemóvel, na aplicação).

	A coluna "Desde ontem" compara com a fotografia anterior da DGEG (▲ subiu, ▼ desceu, em
	cêntimos); o balão do mapa mostra os preços dos últimos 7 dias.

	Com a localização, a coluna "Poupa" diz quanto se poupa num depósito em cada posto, face ao
	posto mais perto, já descontando o combustível da ida e volta (distância em linha reta × 1,3,
	uma aproximação da distância por estrada). O depósito e o consumo ficam no browser.

	Colunas de `data`: station_name, brand, municipality, price, updated_at, latitude, longitude,
	e, se houver histórico, change_since_previous, last_change_date e history_7d.
-->
<script>
	import { onDestroy, onMount } from 'svelte';
	import 'leaflet/dist/leaflet.css';

	/** Resultado de uma consulta do Evidence (um store com as linhas). */
	export let data;
	export let height = 520;
	/** Linhas da tabela de cada vez; "Mostrar mais" junta outras tantas. */
	export let pageSize = 15;

	// Do mais barato para o mais caro (5 classes, pelos quintis dos preços da zona escolhida).
	const COLORS = ['#1a9850', '#91cf60', '#fee08b', '#fc8d59', '#d73027'];
	const TILES = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
	const ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

	let element;
	let L;
	let map;
	let layer;
	let markers = new Map();
	let rows = [];
	let visible = [];
	let shown = pageSize;
	let breaks = [];
	let drawn = null;
	/** A posição da pessoa, depois de carregar em "Perto de mim". */
	let here = null;
	let hereMarker;
	let locating = false;
	let locationError = '';
	const canLocate = typeof navigator !== 'undefined' && 'geolocation' in navigator;

	/** A distância por estrada é, em média, cerca de 1,3 vezes a distância em linha reta. */
	const ROAD_FACTOR = 1.3;
	const SETTINGS_KEY = 'combustiveis-pt:poupanca';
	let tank = 50;
	let consumption = 6.5;
	let order = 'preco';

	function loadSettings() {
		try {
			const saved = JSON.parse(localStorage.getItem(SETTINGS_KEY) ?? '{}');
			if (saved.tank > 0) tank = saved.tank;
			if (saved.consumption > 0) consumption = saved.consumption;
		} catch {
			// Sem acesso ao armazenamento do browser: ficam os valores por omissão.
		}
	}

	function saveSettings() {
		try {
			localStorage.setItem(SETTINGS_KEY, JSON.stringify({ tank, consumption }));
		} catch {
			// Idem: a poupança calcula-se na mesma, só não fica guardada.
		}
	}

	/** O custo de um depósito no posto, mais o combustível da ida e volta até lá. */
	function totalCost(row) {
		const trip = 2 * distanceKm(here, row) * ROAD_FACTOR * (consumption / 100) * row.price;
		return tank * row.price + trip;
	}

	$: nearest = here
		? rows.reduce(
				(best, row) => (!best || distanceKm(here, row) < distanceKm(here, best) ? row : best),
				null
			)
		: null;
	$: validSettings = tank > 0 && consumption > 0;
	$: savings = new Map(
		nearest && validSettings
			? rows.map((row) => [row.key, totalCost(nearest) - totalCost(row)])
			: []
	);

	function saving(row) {
		if (!nearest || !savings.has(row.key)) return '';
		if (row.key === nearest.key) return 'o mais perto';
		const value = savings.get(row.key);
		const text = Math.abs(value).toLocaleString('pt-PT', {
			minimumFractionDigits: 2,
			maximumFractionDigits: 2
		});
		return `${value >= 0 ? '+' : '−'}${text} €`;
	}

	const savingClass = (row) =>
		!nearest || row.key === nearest.key ? '' : savings.get(row.key) >= 0 ? 'desceu' : 'subiu';

	$: data?.fetch?.();
	$: rows = ($data ?? [])
		.filter((row) => row.latitude != null && row.longitude != null && row.price != null)
		.map((row, index) => ({ ...row, key: index }));
	$: breaks = quantiles(rows.map((row) => row.price));
	// O store da consulta pode emitir as mesmas linhas mais de uma vez: só se redesenha (e
	// reenquadra o mapa) quando mudam, senão o mapa voltava atrás depois de o utilizador mexer.
	$: signature = rows.map((row) => `${row.latitude},${row.longitude},${row.price}`).join(';');
	$: if (map && L && signature !== drawn) draw(rows, signature);

	function quantiles(prices) {
		const sorted = [...prices].sort((a, b) => a - b);
		if (!sorted.length) return [];
		return [0.2, 0.4, 0.6, 0.8].map((q) => sorted[Math.floor(q * (sorted.length - 1))]);
	}

	function color(price) {
		const index = breaks.findIndex((limit) => price <= limit);
		return COLORS[index === -1 ? COLORS.length - 1 : index];
	}

	const euros = (value) =>
		value.toLocaleString('pt-PT', { minimumFractionDigits: 3, maximumFractionDigits: 3 }) + ' €';

	function when(value) {
		if (value == null) return '';
		const date = value instanceof Date ? value : new Date(value);
		const pad = (n) => String(n).padStart(2, '0');
		return `${pad(date.getUTCDate())}/${pad(date.getUTCMonth() + 1)}/${date.getUTCFullYear()} ${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())}`;
	}

	/** Distância em linha reta, em km (haversine, como no dbt). */
	function distanceKm(a, b) {
		const rad = (deg) => (deg * Math.PI) / 180;
		const h =
			Math.sin(rad(b.latitude - a.latitude) / 2) ** 2 +
			Math.cos(rad(a.latitude)) * Math.cos(rad(b.latitude)) * Math.sin(rad(b.longitude - a.longitude) / 2) ** 2;
		return 2 * 6371 * Math.asin(Math.sqrt(h));
	}

	const km = (value) =>
		value.toLocaleString('pt-PT', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + ' km';

	/** O caminho até ao posto no Google Maps (abre a aplicação no telemóvel). */
	const directions = (row) =>
		`https://www.google.com/maps/dir/?api=1&destination=${row.latitude},${row.longitude}`;

	$: subiram = visible.filter((row) => row.change_since_previous > 0).length;
	$: desceram = visible.filter((row) => row.change_since_previous < 0).length;

	function locate() {
		locating = true;
		locationError = '';
		navigator.geolocation.getCurrentPosition(
			(position) => {
				locating = false;
				here = { latitude: position.coords.latitude, longitude: position.coords.longitude };
				hereMarker?.remove();
				hereMarker = L.circleMarker([here.latitude, here.longitude], {
					radius: 8,
					weight: 3,
					color: '#ffffff',
					fillColor: '#2563eb',
					fillOpacity: 1
				})
					.bindTooltip('Está aqui')
					.addTo(map);
				// Uns 5 km à volta: chega para ver os postos de uma cidade.
				map.setView([here.latitude, here.longitude], 13);
			},
			(error) => {
				locating = false;
				locationError =
					error.code === error.PERMISSION_DENIED
						? 'O browser não deu acesso à localização. Pode autorizar nas definições do browser, ou aproximar o mapa à mão.'
						: 'Não foi possível saber a localização. Tente outra vez, ou aproxime o mapa à mão.';
			},
			{ enableHighAccuracy: false, timeout: 15000, maximumAge: 300000 }
		);
	}

	/** "▲ 2,0" ou "▼ 0,5" (cêntimos), ou "=" se não mudou; vazio sem fotografia anterior. */
	function change(row) {
		const value = row.change_since_previous;
		if (value == null) return '';
		const cents = Math.round(value * 1000) / 10;
		if (cents === 0) return '=';
		const text = Math.abs(cents).toLocaleString('pt-PT', {
			minimumFractionDigits: 1,
			maximumFractionDigits: 1
		});
		return `${cents > 0 ? '▲' : '▼'} ${text}`;
	}

	const changeClass = (row) =>
		row.change_since_previous > 0 ? 'subiu' : row.change_since_previous < 0 ? 'desceu' : '';

	function changeLabel(row) {
		const text = change(row);
		if (!text) return 'sem fotografia anterior';
		if (text === '=') return 'o mesmo preço de ontem';
		return `${row.change_since_previous > 0 ? 'subiu' : 'desceu'} ${text.slice(2)} cêntimos desde ontem`;
	}

	/** Uma data, ou null: o Evidence pode dar uma data vazia como 1/1/1970. */
	function dateOrNull(value) {
		if (value == null) return null;
		const date = value instanceof Date ? value : new Date(value);
		return Number.isNaN(date.getTime()) || date.getUTCFullYear() < 2000 ? null : date;
	}

	function day(date) {
		const pad = (n) => String(n).padStart(2, '0');
		return `${pad(date.getUTCDate())}/${pad(date.getUTCMonth() + 1)}`;
	}

	function escape(text) {
		return String(text ?? '').replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
	}

	function popup(row) {
		return `<strong>${escape(row.station_name)}</strong><br>${escape(row.brand)} · ${escape(row.municipality)}<br>${euros(row.price)}${change(row) && change(row) !== '=' ? ` (${changeLabel(row)})` : ''}<br><small>Atualizado: ${when(row.updated_at)}</small>${row.history_7d ? `<br><small>Últimos dias: ${escape(row.history_7d)}</small>` : ''}${dateOrNull(row.last_change_date) ? `<br><small>Última mudança de preço: ${day(dateOrNull(row.last_change_date))}</small>` : ''}<br><a href="${directions(row)}" target="_blank" rel="noopener">Ir até lá (Google Maps)</a>`;
	}

	function draw(rows, signature) {
		drawn = signature;
		layer.clearLayers();
		markers = new Map();
		// Os mais caros primeiro, para os mais baratos ficarem por cima quando se sobrepõem.
		for (const row of [...rows].sort((a, b) => b.price - a.price)) {
			const marker = L.circleMarker([row.latitude, row.longitude], {
				radius: 5,
				weight: 1,
				color: '#ffffff',
				fillColor: color(row.price),
				fillOpacity: 0.9
			}).bindPopup(popup(row));
			marker.addTo(layer);
			markers.set(row.key, marker);
		}
		if (rows.length) {
			map.fitBounds(L.latLngBounds(rows.map((row) => [row.latitude, row.longitude])), {
				padding: [20, 20],
				maxZoom: 14,
				animate: false
			});
		}
		update();
	}

	function update() {
		const bounds = map.getBounds();
		visible = sortRows(rows.filter((row) => bounds.contains([row.latitude, row.longitude])));
		shown = pageSize;
	}

	function sortRows(list) {
		const byPrice = (a, b) => a.price - b.price || a.station_name.localeCompare(b.station_name);
		if (order === 'poupanca' && savings.size) {
			return list.sort((a, b) => savings.get(b.key) - savings.get(a.key) || byPrice(a, b));
		}
		return list.sort(byPrice);
	}

	// Ao mudar a ordem, o depósito ou o consumo, a tabela reordena-se sem mexer no mapa.
	$: if (map) {
		order, savings;
		visible = sortRows([...visible]);
	}

	function focus(row) {
		map.setView([row.latitude, row.longitude], Math.max(map.getZoom(), 14));
		markers.get(row.key)?.openPopup();
	}

	onMount(async () => {
		L = (await import('leaflet')).default;
		map = L.map(element, { preferCanvas: true, scrollWheelZoom: false });
		L.tileLayer(TILES, { attribution: ATTRIBUTION, maxZoom: 18 }).addTo(map);
		layer = L.layerGroup().addTo(map);
		map.setView([39.6, -8.0], 7);
		map.on('moveend', update);
		loadSettings();
	});

	onDestroy(() => map?.remove());
</script>

<div class="mapa-postos my-4" data-postos={drawn === null ? undefined : rows.length}>
	{#if canLocate}
		<p class="perto">
			<button type="button" class="perto-botao" on:click={locate} disabled={locating || !map}>
				{locating ? 'A procurar…' : here ? 'Atualizar a minha localização' : 'Perto de mim'}
			</button>
			<span class="text-sm text-base-content-muted">
				Centra o mapa onde está, para ver os postos mais baratos à volta. A localização não sai
				do seu telemóvel.
			</span>
		</p>
		{#if locationError}<p class="text-sm" role="alert">{locationError}</p>{/if}
		{#if here}
			<fieldset class="poupanca text-sm">
				<legend class="sr-only">Contas da poupança</legend>
				<label>
					Depósito
					<input type="number" min="5" max="200" step="1" bind:value={tank} on:change={saveSettings} />
					L
				</label>
				<label>
					Consumo
					<input
						type="number"
						min="2"
						max="30"
						step="0.1"
						bind:value={consumption}
						on:change={saveSettings}
					/>
					L/100 km
				</label>
				<label>
					Ordenar por
					<select bind:value={order}>
						<option value="preco">preço</option>
						<option value="poupanca">poupança</option>
					</select>
				</label>
			</fieldset>
			{#if nearest && validSettings}
				<p class="text-sm text-base-content-muted">
					"Poupa" compara um depósito de {tank.toLocaleString('pt-PT')} L em cada posto com o
					posto mais perto ({nearest.station_name}), já descontando o combustível da ida e volta
					(a distância em linha reta × 1,3, com {consumption.toLocaleString('pt-PT')} L/100 km).
				</p>
			{/if}
		{/if}
	{/if}
	<div bind:this={element} style="height: min({height}px, 60vh)" class="rounded border border-base-300" />
	{#if breaks.length}
		<p class="legenda text-sm">
			<span>Mais barato</span>
			{#each COLORS as fill}<span class="cor" style="background: {fill}" />{/each}
			<span>Mais caro</span>
			<span class="text-base-content-muted">
				({euros(Math.min(...rows.map((r) => r.price)))} a {euros(Math.max(...rows.map((r) => r.price)))})
			</span>
		</p>
	{/if}

	<p class="text-sm" aria-live="polite">
		{#if visible.length}
			{visible.length.toLocaleString('pt-PT')}
			{visible.length === 1 ? 'posto' : 'postos'} na parte do mapa que se vê, do mais barato
			para o mais caro. Aproxime ou arraste o mapa para ver só os de uma zona.
		{:else}
			Nenhum posto na parte do mapa que se vê.
		{/if}
		{#if subiram + desceram > 0}
			Desde ontem, {subiram.toLocaleString('pt-PT')} {subiram === 1 ? 'subiu' : 'subiram'} e
			{desceram.toLocaleString('pt-PT')} {desceram === 1 ? 'desceu' : 'desceram'} de preço.
		{/if}
	</p>

	{#if visible.length}
		<table class="tabela-postos text-sm">
			<thead>
				<tr>
					<th class="num">#</th>
					<th>Posto</th>
					<th class="larga">Marca</th>
					<th class="larga">Concelho</th>
					<th class="num">Preço (€/L)</th>
					<th class="num larga">Desde ontem</th>
					{#if here}<th class="num larga">Distância</th>{/if}
					{#if nearest && validSettings}<th class="num">Poupa</th>{/if}
					<th class="larga">Atualizado</th>
					<th><span class="sr-only">Caminho</span></th>
				</tr>
			</thead>
			<tbody>
				{#each visible.slice(0, shown) as row, index (row.key)}
					<tr>
						<td class="num">{index + 1}</td>
						<td>
							<button type="button" on:click={() => focus(row)} title="Ver no mapa">
								<span class="cor" style="background: {color(row.price)}" />
								{row.station_name}
							</button>
							<!-- No telemóvel, a marca, o concelho e a data vão aqui, em vez de colunas. -->
							<span class="estreita"
								>{row.brand} · {row.municipality}{here ? ` · ${km(distanceKm(here, row))}` : ''} ·
								{when(row.updated_at)}</span
							>
						</td>
						<td class="larga">{row.brand}</td>
						<td class="larga">{row.municipality}</td>
						<td class="num">
							{euros(row.price).replace(' €', '')}
							<!-- No telemóvel, a variação vai debaixo do preço. -->
							<span class="estreita variacao {changeClass(row)}">
								<span aria-hidden="true">{change(row)}</span>
								<span class="sr-only">{changeLabel(row)}</span>
							</span>
						</td>
						<td class="num larga variacao {changeClass(row)}">
							<span aria-hidden="true">{change(row)}</span>
							<span class="sr-only">{changeLabel(row)}</span>
						</td>
						{#if here}<td class="num larga">{km(distanceKm(here, row))}</td>{/if}
						{#if nearest && validSettings}<td class="num poupa {savingClass(row)}">{saving(row)}</td>{/if}
						<td class="larga">{when(row.updated_at)}</td>
						<td>
							<a
								class="ir"
								href={directions(row)}
								target="_blank"
								rel="noopener"
								aria-label="Ir até {row.station_name} (Google Maps)">Ir</a
							>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
		{#if visible.length > shown}
			<button type="button" class="mais text-sm" on:click={() => (shown += pageSize)}>
				Mostrar mais ({(visible.length - shown).toLocaleString('pt-PT')} por mostrar)
			</button>
		{/if}
	{/if}
</div>

<style>
	/* Os painéis do Leaflet têm z-index até 1000: sem um contexto próprio, o mapa passava por
	   cima do cabeçalho fixo da página ao fazer scroll. */
	.mapa-postos {
		position: relative;
		isolation: isolate;
		z-index: 0;
	}
	.perto {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		flex-wrap: wrap;
		margin-bottom: 0.75rem;
	}
	.perto-botao {
		padding: 0.5rem 1rem;
		border-radius: 0.375rem;
		background: #2563eb;
		color: #ffffff;
		font-weight: 600;
	}
	.perto-botao:disabled {
		opacity: 0.7;
	}
	.ir {
		display: inline-block;
		padding: 0.1rem 0.6rem;
		border: 1px solid #2563eb;
		border-radius: 999px;
		color: #2563eb;
		font-weight: 600;
		text-decoration: none;
	}
	.estreita {
		display: none;
	}
	.poupanca {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem 1.25rem;
		margin: 0 0 0.5rem;
	}
	.poupanca input,
	.poupanca select {
		width: 4.5rem;
		margin: 0 0.25rem;
		padding: 0.15rem 0.35rem;
		border: 1px solid rgba(127, 127, 127, 0.5);
		border-radius: 0.25rem;
		background: transparent;
		color: inherit;
	}
	.poupanca select {
		width: auto;
	}
	.poupa {
		white-space: nowrap;
	}
	.variacao {
		white-space: nowrap;
	}
	/* Vermelho a subir, verde a descer; a seta diz o mesmo para quem não distingue as cores. */
	.subiu {
		color: #b91c1c;
	}
	.desceu {
		color: #15803d;
	}
	:global([data-theme='dark']) .subiu {
		color: #f87171;
	}
	:global([data-theme='dark']) .desceu {
		color: #4ade80;
	}
	@media (max-width: 640px) {
		.tabela-postos .larga {
			display: none;
		}
		.estreita {
			display: block;
			font-size: 0.75rem;
			opacity: 0.75;
		}
		.tabela-postos td,
		.tabela-postos th {
			padding: 0.35rem 0.25rem;
		}
	}
	.sr-only {
		position: absolute;
		width: 1px;
		height: 1px;
		overflow: hidden;
		clip: rect(0, 0, 0, 0);
		white-space: nowrap;
	}
	.legenda {
		display: flex;
		align-items: center;
		gap: 0.35rem;
		flex-wrap: wrap;
		margin: 0.5rem 0;
	}
	.cor {
		display: inline-block;
		width: 0.8rem;
		height: 0.8rem;
		border-radius: 999px;
		vertical-align: middle;
	}
	.tabela-postos {
		width: 100%;
		border-collapse: collapse;
		margin-top: 0.5rem;
	}
	.tabela-postos th {
		text-align: left;
		font-weight: 600;
		border-bottom: 1px solid currentColor;
		padding: 0.25rem 0.5rem;
	}
	.tabela-postos td {
		padding: 0.25rem 0.5rem;
		border-bottom: 1px solid rgba(127, 127, 127, 0.25);
	}
	.tabela-postos .num {
		text-align: right;
		font-variant-numeric: tabular-nums;
	}
	.tabela-postos button {
		text-align: left;
		cursor: pointer;
	}
	.tabela-postos button:hover {
		text-decoration: underline;
	}
	.mais {
		margin-top: 0.5rem;
		padding: 0.25rem 0.75rem;
		border: 1px solid rgba(127, 127, 127, 0.5);
		border-radius: 0.25rem;
	}
</style>
