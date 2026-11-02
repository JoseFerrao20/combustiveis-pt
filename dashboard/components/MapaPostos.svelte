<!--
	Mapa dos postos com a tabela dos que se veem, do mais barato para o mais caro. A tabela
	acompanha o mapa: ao aproximar ou arrastar, fica só com os postos dentro do mapa. Os
	componentes de mapa do Evidence não dão os limites do mapa à página, por isso este usa o
	Leaflet diretamente (já vem com o Evidence), com os mosaicos do OpenStreetMap.

	"Perto de mim" usa a localização do browser (só depois de a pessoa autorizar; a posição
	fica no telemóvel) para centrar o mapa e mostrar a distância de cada posto. "Ir" abre o
	caminho até ao posto no Google Maps (no telemóvel, na aplicação).

	A coluna "Na semana" compara com a fotografia anterior da DGEG, a de segunda-feira passada
	(▲ subiu, ▼ desceu, em cêntimos); o balão do mapa mostra os preços das últimas fotografias.

	Com a localização, a coluna "Poupa" diz quanto se poupa num depósito em cada posto, face ao
	posto mais perto, já descontando o combustível da ida e volta (distância em linha reta × 1,3,
	uma aproximação da distância por estrada). O depósito e o consumo ficam no browser.

	A estrela de cada posto guarda-o em "Os meus postos" (lista no topo, com o preço de hoje e a
	mudança na semana). Os favoritos ficam no browser, pelo id da DGEG. Cada um diz a posição
	entre os postos a 5 km (com o mesmo combustível, na zona escolhida) e qual é o mais barato.

	Com o mapa afastado (até ao zoom 11), os postos próximos juntam-se num grupo, com o número de
	postos e a cor do preço mediano; tocar no grupo aproxima o mapa.

	Por cima do mapa: procurar um concelho, uma localidade ou um posto (só nos dados da página, sem
	enviar o que se escreve a ninguém), escolher a marca e esconder os postos de autoestrada. A
	marca, as autoestradas e o combustível escolhido (`combustivel`) ficam guardados no browser.

	Colunas de `data`: station_id, locality, station_type, station_name, brand, municipality, price, updated_at, latitude, longitude,
	e, se houver histórico, change_since_previous, previous_snapshot_date, last_change_date e recent_history.
-->
<script>
	import { onDestroy, onMount } from 'svelte';
	import 'leaflet/dist/leaflet.css';

	/** Resultado de uma consulta do Evidence (um store com as linhas). */
	export let data;
	export let height = 520;
	/** Linhas da tabela de cada vez; "Mostrar mais" junta outras tantas. */
	export let pageSize = 15;
	/** O combustível escolhido no filtro da página, para o guardar e voltar a escolhê-lo. */
	export let combustivel = undefined;

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
	const FAVORITES_KEY = 'combustiveis-pt:favoritos';
	/** Os ids da DGEG dos postos guardados, pela ordem em que foram guardados. */
	let favorites = [];

	function loadFavorites() {
		try {
			const saved = JSON.parse(localStorage.getItem(FAVORITES_KEY) ?? '[]');
			if (Array.isArray(saved)) favorites = saved.map(Number).filter(Number.isFinite);
		} catch {
			// Sem acesso ao armazenamento do browser: a lista começa vazia.
		}
	}

	function toggleFavorite(row) {
		const id = Number(row.station_id);
		favorites = favorites.includes(id) ? favorites.filter((f) => f !== id) : [...favorites, id];
		try {
			localStorage.setItem(FAVORITES_KEY, JSON.stringify(favorites));
		} catch {
			// Idem: a estrela funciona até fechar a página, só não fica guardada.
		}
	}

	$: favoriteRows = favorites
		.map((id) => allRows.find((row) => Number(row.station_id) === id))
		.filter(Boolean);
	$: missingFavorites = favorites.length - favoriteRows.length;

	/** O raio dos concorrentes de cada posto guardado (em linha reta, como nos postos acompanhados). */
	const NEAR_KM = 5;

	/**
	 * Os concorrentes de um posto guardado: quantos há a 5 km com o mesmo combustível, a posição
	 * do posto (1 é o mais barato; um empate não conta como mais barato) e o mais barato dos outros.
	 */
	function competition(row, list) {
		const near = [];
		for (const other of list) {
			if (other.key === row.key) continue;
			const distance = distanceKm(row, other);
			if (distance <= NEAR_KM) near.push({ row: other, distance });
		}
		const cheapest = near.reduce(
			(best, item) =>
				!best || item.row.price < best.row.price || (item.row.price === best.row.price && item.distance < best.distance)
					? item
					: best,
			null
		);
		return {
			count: near.length,
			position: near.filter((item) => item.row.price < row.price).length + 1,
			cheapest
		};
	}

	$: competitors = new Map(favoriteRows.map((row) => [row.key, competition(row, allRows)]));

	/** "1,5 cêntimos" (sem sinal). */
	const cents = (value) =>
		`${(Math.round(Math.abs(value) * 1000) / 10).toLocaleString('pt-PT', {
			minimumFractionDigits: 1,
			maximumFractionDigits: 1
		})} cêntimos`;
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

	const FUEL_KEY = 'combustiveis-pt:combustivel';
	const FILTERS_KEY = 'combustiveis-pt:filtros';
	/** A marca escolhida ('' = todas) e se os postos de autoestrada ficam de fora. */
	let brand = '';
	let noMotorway = false;

	$: if (combustivel) {
		try {
			localStorage.setItem(FUEL_KEY, combustivel);
		} catch {
			// Sem acesso ao armazenamento do browser: o combustível não fica guardado.
		}
	}

	function loadFilters() {
		try {
			const saved = JSON.parse(localStorage.getItem(FILTERS_KEY) ?? '{}');
			if (typeof saved.brand === 'string') brand = saved.brand;
			if (typeof saved.noMotorway === 'boolean') noMotorway = saved.noMotorway;
		} catch {
			// Idem: ficam os filtros por omissão.
		}
	}

	function saveFilters() {
		try {
			localStorage.setItem(FILTERS_KEY, JSON.stringify({ brand, noMotorway }));
		} catch {
			// Idem: os filtros valem até fechar a página.
		}
	}

	$: data?.fetch?.();
	$: allRows = ($data ?? [])
		.filter((row) => row.latitude != null && row.longitude != null && row.price != null)
		.map((row, index) => ({ ...row, key: index }));
	$: rows = allRows.filter(
		(row) =>
			(!brand || row.brand === brand) && !(noMotorway && row.station_type === 'Auto-estrada')
	);
	// As marcas da zona, da que tem mais postos para a que tem menos (e a escolhida, mesmo que
	// não exista na zona, para o filtro não ficar com um valor escondido).
	$: brands = [...allRows.reduce((m, r) => m.set(r.brand, (m.get(r.brand) ?? 0) + 1), new Map())]
		.sort((a, b) => b[1] - a[1] || String(a[0]).localeCompare(String(b[0])))
		.map(([name, count]) => ({ name, count }))
		.concat(brand && !allRows.some((r) => r.brand === brand) ? [{ name: brand, count: 0 }] : []);

	/** Para procurar sem contar com maiúsculas nem acentos ("Agueda" encontra "Águeda"). */
	const plain = (text) =>
		String(text ?? '')
			.normalize('NFD')
			.replace(/[\u0300-\u036f]/g, '')
			.toLowerCase();

	let query = '';
	$: results = search(query, allRows, rows);

	function search(text, allRows, rows) {
		const q = plain(text).trim();
		if (q.length < 2) return [];
		const places = new Map();
		for (const row of allRows) {
			for (const [kind, name] of [
				['concelho', row.municipality],
				['localidade', row.locality]
			]) {
				if (!name || !plain(name).includes(q)) continue;
				const id = `${kind}:${plain(name)}`;
				if (!places.has(id)) places.set(id, { id, kind, name, rows: [] });
				places.get(id).rows.push(row);
			}
		}
		const starts = (name) => (plain(name).startsWith(q) ? 0 : 1);
		const placeResults = [...places.values()]
			.sort((a, b) => starts(a.name) - starts(b.name) || b.rows.length - a.rows.length)
			.slice(0, 5);
		const stationResults = rows
			.filter((row) => plain(`${row.brand} ${row.station_name}`).includes(q))
			.sort((a, b) => starts(a.station_name) - starts(b.station_name) || a.price - b.price)
			.slice(0, 5)
			.map((row) => ({ id: `posto:${row.key}`, kind: 'posto', name: row.station_name, row }));
		return [...placeResults, ...stationResults];
	}

	function choose(result) {
		if (result.kind === 'posto') {
			focus(result.row);
		} else {
			map.fitBounds(L.latLngBounds(result.rows.map((row) => [row.latitude, row.longitude])), {
				padding: [30, 30],
				maxZoom: 14
			});
		}
		query = '';
	}
	$: breaks = quantiles(rows.map((row) => row.price));
	// O store da consulta pode emitir as mesmas linhas mais de uma vez: só se redesenha (e
	// reenquadra o mapa) quando mudam, senão o mapa voltava atrás depois de o utilizador mexer.
	// Os filtros de marca e de autoestrada redesenham os pontos, mas não mexem no enquadramento;
	// só uma mudança dos dados (combustível, distrito, concelho) reenquadra o mapa.
	$: dataSignature = allRows.map((row) => `${row.latitude},${row.longitude},${row.price}`).join(';');
	$: signature = `${dataSignature}|${brand}|${noMotorway}`;
	$: if (map && L && signature !== drawn) draw(rows, signature, dataSignature !== fitted);

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
	// O dia da fotografia anterior (a mesma em todas as linhas), para dizer "desde quando".
	$: previousDay = (() => {
		const since = dateOrNull(visible.find((row) => row.previous_snapshot_date)?.previous_snapshot_date);
		return since ? day(since) : null;
	})();
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
		const since = dateOrNull(row.previous_snapshot_date);
		if (text === '=') return since ? `o mesmo preço que a ${day(since)}` : 'o mesmo preço';
		const verb = row.change_since_previous > 0 ? 'subiu' : 'desceu';
		return `${verb} ${text.slice(2)} cêntimos${since ? ` desde ${day(since)}` : ''}`;
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
		return `<strong>${escape(row.station_name)}</strong><br>${escape(row.brand)} · ${escape(row.municipality)}<br>${euros(row.price)}${change(row) && change(row) !== '=' ? ` (${changeLabel(row)})` : ''}<br><small>Atualizado: ${when(row.updated_at)}</small>${row.recent_history ? `<br><small>Últimas fotografias: ${escape(row.recent_history)}</small>` : ''}${dateOrNull(row.last_change_date) ? `<br><small>Última mudança de preço: ${day(dateOrNull(row.last_change_date))}</small>` : ''}<br><a href="${directions(row)}" target="_blank" rel="noopener">Ir até lá (Google Maps)</a>`;
	}

	let fitted = null;

	/** Até este zoom, os postos próximos juntam-se num grupo (o país tem mais de 3000 postos). */
	const GROUP_UNTIL_ZOOM = 11;
	/** O lado de cada quadrado da grelha que junta os postos, em píxeis do ecrã. */
	const GROUP_CELL_PX = 56;

	function draw(rows, signature, refit) {
		drawn = signature;
		if (refit && rows.length) {
			fitted = dataSignature;
			map.fitBounds(L.latLngBounds(rows.map((row) => [row.latitude, row.longitude])), {
				padding: [20, 20],
				maxZoom: 14,
				animate: false
			});
		}
		drawMarkers();
		update();
	}

	/**
	 * Os pontos do mapa. Com o mapa afastado, os postos de cada quadrado da grelha juntam-se num
	 * círculo com o número de postos e a cor do preço mediano; tocar nele aproxima o mapa. Volta
	 * a desenhar-se a cada zoom.
	 */
	function drawMarkers() {
		layer.clearLayers();
		markers = new Map();
		const zoom = map.getZoom();
		// Os mais caros primeiro, para os mais baratos ficarem por cima quando se sobrepõem.
		const sorted = [...rows].sort((a, b) => b.price - a.price);
		if (zoom > GROUP_UNTIL_ZOOM) {
			sorted.forEach(addStation);
			return;
		}
		const cells = new Map();
		for (const row of sorted) {
			const point = map.project([row.latitude, row.longitude], zoom);
			const x = Math.floor(point.x / GROUP_CELL_PX);
			const y = Math.floor(point.y / GROUP_CELL_PX);
			const key = `${x}:${y}`;
			if (!cells.has(key)) cells.set(key, { x, y, rows: [] });
			cells.get(key).rows.push(row);
		}
		for (const cell of cells.values()) {
			if (cell.rows.length === 1) addStation(cell.rows[0]);
			else {
				// No centro do quadrado (e não na média dos postos), para os círculos nunca se
				// sobreporem: o maior tem 42 px, e os centros ficam a 56 px uns dos outros (WCAG 2.5.8).
				const center = map.unproject([(cell.x + 0.5) * GROUP_CELL_PX, (cell.y + 0.5) * GROUP_CELL_PX], zoom);
				addGroup(cell.rows, center);
			}
		}
	}

	function addStation(row) {
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

	/** Preto ou branco, o que tiver mais contraste com a cor de fundo (WCAG). */
	function ink(hex) {
		const channel = (i) => {
			const c = parseInt(hex.slice(i, i + 2), 16) / 255;
			return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
		};
		const luminance = 0.2126 * channel(1) + 0.7152 * channel(3) + 0.0722 * channel(5);
		return (luminance + 0.05) / 0.05 >= 1.05 / (luminance + 0.05) ? '#111827' : '#ffffff';
	}

	function addGroup(group, center) {
		const cheapest = group[group.length - 1];
		const size = group.length < 10 ? 28 : group.length < 100 ? 34 : 42;
		// A cor é a do preço mediano do grupo (a do mais barato seria quase sempre verde).
		const fill = color(group[Math.floor(group.length / 2)].price);
		const icon = L.divIcon({
			className: 'grupo-postos',
			iconSize: [size, size],
			html: `<span style="background: ${fill}; color: ${ink(fill)}">${group.length}</span>`
		});
		const marker = L.marker(center, { icon, keyboard: true });
		marker.on('add', () =>
			marker
				.getElement()
				?.setAttribute('aria-label', `${group.length} postos, o mais barato a ${euros(cheapest.price)}: aproximar`)
		);
		marker.on('click', () =>
			map.fitBounds(L.latLngBounds(group.map((row) => [row.latitude, row.longitude])), {
				padding: [40, 40],
				maxZoom: GROUP_UNTIL_ZOOM + 3
			})
		);
		marker.addTo(layer);
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
		// Sem animação, o mapa redesenha-se logo com os postos soltos (zoom 14), e o balão abre.
		map.setView([row.latitude, row.longitude], Math.max(map.getZoom(), 14), { animate: false });
		markers.get(row.key)?.openPopup();
	}

	onMount(async () => {
		L = (await import('leaflet')).default;
		map = L.map(element, { preferCanvas: true, scrollWheelZoom: false });
		L.tileLayer(TILES, { attribution: ATTRIBUTION, maxZoom: 18 }).addTo(map);
		layer = L.layerGroup().addTo(map);
		map.setView([39.6, -8.0], 7);
		map.on('moveend', update);
		map.on('zoomend', () => {
			if (drawn !== null) drawMarkers();
		});
		loadSettings();
		loadFavorites();
		loadFilters();
	});

	onDestroy(() => map?.remove());
</script>

<div class="mapa-postos my-4" data-postos={drawn === null ? undefined : rows.length}>
	<section class="meus-postos" aria-labelledby="meus-postos-titulo">
		<h2 id="meus-postos-titulo" class="text-lg font-semibold">Os meus postos</h2>
		{#if favoriteRows.length}
			<ul>
				{#each favoriteRows as row (row.key)}
					<li>
						<button type="button" class="nome" on:click={() => focus(row)} title="Ver no mapa">
							<span class="cor" style="background: {color(row.price)}" />
							{row.station_name}
						</button>
						<span class="text-sm text-base-content-muted marca">{row.brand} · {row.municipality}</span>
						<span class="preco">{euros(row.price)}</span>
						<span class="variacao {changeClass(row)}">
							<span aria-hidden="true">{change(row)}</span>
							<span class="sr-only">{changeLabel(row)}</span>
						</span>
						<a
							class="ir"
							href={directions(row)}
							target="_blank"
							rel="noopener"
							aria-label="Ir até {row.station_name} (Google Maps)">Ir</a
						>
						<button
							type="button"
							class="estrela"
							aria-pressed="true"
							on:click={() => toggleFavorite(row)}
							><span aria-hidden="true">★</span><span class="sr-only"
								>Tirar {row.station_name} dos meus postos</span
							></button
						>
						{#if competitors.get(row.key)}
							{@const info = competitors.get(row.key)}
							<p class="concorrentes text-sm">
								{#if info.count === 0}
									Nenhum outro posto a {NEAR_KM} km com este combustível.
								{:else if info.position === 1 && info.cheapest.row.price > row.price}
									<strong>O mais barato</strong> dos {info.count + 1} postos a {NEAR_KM} km. O seguinte custa
									mais {cents(info.cheapest.row.price - row.price)} (<button
										type="button"
										class="ligacao"
										on:click={() => focus(info.cheapest.row)}>{info.cheapest.row.station_name}</button
									>, a {km(info.cheapest.distance)}).
								{:else if info.position === 1}
									<strong>Um dos mais baratos</strong> dos {info.count + 1} postos a {NEAR_KM} km: o mesmo
									preço que <button type="button" class="ligacao" on:click={() => focus(info.cheapest.row)}
										>{info.cheapest.row.station_name}</button
									>, a {km(info.cheapest.distance)}.
								{:else}
									<strong>{info.position}.º</strong> mais barato dos {info.count + 1} postos a {NEAR_KM} km.
									O mais barato é
									<button type="button" class="ligacao" on:click={() => focus(info.cheapest.row)}
										>{info.cheapest.row.station_name}</button
									>, a {km(info.cheapest.distance)}: menos {cents(row.price - info.cheapest.row.price)}.
								{/if}
							</p>
						{/if}
					</li>
				{/each}
			</ul>
		{/if}
		<p class="text-sm text-base-content-muted">
			{#if !favorites.length}
				Toque na estrela (☆) de um posto, na tabela por baixo do mapa, para o guardar aqui. A
				lista fica só neste telemóvel ou computador.
			{:else if missingFavorites > 0}
				{missingFavorites === 1 ? 'Um dos seus postos não aparece' : `${missingFavorites} dos seus postos não aparecem`}
				com o combustível, o distrito e o concelho escolhidos (ou não têm o preço atualizado).
			{:else}
				A lista fica só neste telemóvel ou computador.
			{/if}
		</p>
	</section>

	<div class="procurar">
		<label for="procurar-postos" class="text-sm font-semibold"
			>Procurar uma localidade ou um posto</label
		>
		<input
			id="procurar-postos"
			type="search"
			bind:value={query}
			placeholder="Ex.: Rio Tinto, Galp Areeiro"
			autocomplete="off"
			disabled={!map}
		/>
		{#if results.length}
			<ul class="resultados" aria-label="Resultados da procura">
				{#each results as result (result.id)}
					<li>
						<button type="button" on:click={() => choose(result)}>
							<span>{result.name}</span>
							<span class="text-sm text-base-content-muted">
								{#if result.kind === 'posto'}
									posto · {result.row.brand} · {result.row.municipality} · {euros(result.row.price)}
								{:else}
									{result.kind} · {result.rows.length}
									{result.rows.length === 1 ? 'posto' : 'postos'}
								{/if}
							</span>
						</button>
					</li>
				{/each}
			</ul>
		{:else if plain(query).trim().length >= 2}
			<p class="text-sm" role="status">
				Nada encontrado (com o combustível, o distrito e o concelho escolhidos).
			</p>
		{/if}
	</div>

	<fieldset class="filtros-postos text-sm">
		<legend class="sr-only">Que postos mostrar</legend>
		<label>
			Marca
			<select bind:value={brand} on:change={saveFilters}>
				<option value="">Todas</option>
				{#each brands as option (option.name)}
					<option value={option.name}>{option.name} ({option.count})</option>
				{/each}
			</select>
		</label>
		<label>
			<input type="checkbox" bind:checked={noMotorway} on:change={saveFilters} />
			Sem postos de autoestrada
		</label>
	</fieldset>

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
			<span class="text-base-content-muted">
				Com o mapa afastado, os postos próximos juntam-se num círculo maior: o número diz quantos
				são, e a cor é a do preço a meio do grupo (metade é mais barata). Toque nele para aproximar.
			</span>
		</p>
	{/if}

	<p class="text-sm" aria-live="polite">
		{#if visible.length}
			{visible.length.toLocaleString('pt-PT')}
			{visible.length === 1 ? 'posto' : 'postos'} na parte do mapa que se vê, do mais barato
			para o mais caro{#if brand || noMotorway}
				({[brand && `só ${brand}`, noMotorway && 'sem autoestradas'].filter(Boolean).join(', ')})
			{/if}. Aproxime ou arraste o mapa para ver só os de uma zona.
		{:else}
			Nenhum posto na parte do mapa que se vê.
		{/if}
		{#if subiram + desceram > 0}
			Desde {previousDay ? `a fotografia de ${previousDay}` : 'a fotografia anterior'}, {subiram.toLocaleString('pt-PT')} {subiram === 1 ? 'subiu' : 'subiram'} e
			{desceram.toLocaleString('pt-PT')} {desceram === 1 ? 'desceu' : 'desceram'} de preço.
		{/if}
	</p>

	{#if visible.length}
		<table class="tabela-postos text-sm">
			<thead>
				<tr>
					<th class="num">#</th>
					<th><span class="sr-only">Os meus postos</span></th>
					<th>Posto</th>
					<th class="larga">Marca</th>
					<th class="larga">Concelho</th>
					<th class="num">Preço (€/L)</th>
					<th class="num larga">Na semana</th>
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
							<button
								type="button"
								class="estrela"
								aria-pressed={favorites.includes(Number(row.station_id))}
								on:click={() => toggleFavorite(row)}
								><span aria-hidden="true"
									>{favorites.includes(Number(row.station_id)) ? '★' : '☆'}</span
								><span class="sr-only">Guardar {row.station_name} nos meus postos</span></button
							>
						</td>
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
						<td class="num preco-celula">
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
	.meus-postos {
		margin-bottom: 1rem;
	}
	.meus-postos ul {
		list-style: none;
		padding: 0;
		margin: 0.5rem 0;
	}
	/* Duas linhas: o nome em cima; a marca, o preço, a mudança, "Ir" e a estrela em baixo. */
	.meus-postos li {
		display: grid;
		grid-template-columns: 1fr auto auto auto auto;
		grid-template-areas:
			'nome nome nome nome nome'
			'marca preco variacao ir estrela'
			'concorrentes concorrentes concorrentes concorrentes concorrentes';
		align-items: center;
		gap: 0.25rem 0.75rem;
		padding: 0.5rem 0;
		border-bottom: 1px solid rgba(127, 127, 127, 0.25);
	}
	.meus-postos .nome {
		grid-area: nome;
		font-weight: 600;
		text-align: left;
	}
	.meus-postos .marca {
		grid-area: marca;
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.meus-postos .preco {
		grid-area: preco;
		font-weight: 600;
		font-variant-numeric: tabular-nums;
	}
	.meus-postos .variacao {
		grid-area: variacao;
	}
	.meus-postos .ir {
		grid-area: ir;
	}
	.meus-postos .estrela {
		grid-area: estrela;
	}
	.meus-postos .concorrentes {
		grid-area: concorrentes;
		margin: 0;
	}
	.ligacao {
		text-decoration: underline;
		text-align: left;
	}
	.estrela {
		color: #d97706;
		font-size: 1.15rem;
		line-height: 1;
		padding: 0.25rem;
	}
	/* No tema escuro, o azul de "Ir" precisa de ser mais claro para ter contraste. */
	:global([data-theme='dark']) .ir {
		color: #60a5fa;
		border-color: #60a5fa;
	}
	.procurar {
		margin-bottom: 0.75rem;
	}
	.procurar label {
		display: block;
		margin-bottom: 0.25rem;
	}
	.procurar input {
		width: 100%;
		max-width: 28rem;
		padding: 0.5rem 0.75rem;
		border: 1px solid rgba(127, 127, 127, 0.6);
		border-radius: 0.375rem;
		background: transparent;
		color: inherit;
	}
	.resultados {
		list-style: none;
		margin: 0.25rem 0 0;
		padding: 0;
		max-width: 28rem;
		border: 1px solid rgba(127, 127, 127, 0.4);
		border-radius: 0.375rem;
	}
	.resultados li + li {
		border-top: 1px solid rgba(127, 127, 127, 0.25);
	}
	.resultados button {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		width: 100%;
		padding: 0.4rem 0.75rem;
		text-align: left;
	}
	.resultados button:hover,
	.resultados button:focus-visible {
		background: rgba(127, 127, 127, 0.12);
	}
	.filtros-postos {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.5rem 1.25rem;
		margin: 0 0 0.75rem;
	}
	.filtros-postos select {
		margin-left: 0.25rem;
		padding: 0.15rem 0.35rem;
		border: 1px solid rgba(127, 127, 127, 0.5);
		border-radius: 0.25rem;
		background: transparent;
		color: inherit;
		max-width: 14rem;
	}
	.sr-only {
		position: absolute;
		width: 1px;
		height: 1px;
		overflow: hidden;
		clip: rect(0, 0, 0, 0);
		white-space: nowrap;
	}
	/* Os grupos de postos (divIcon do Leaflet, fora do componente). */
	.mapa-postos :global(.grupo-postos span) {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 100%;
		height: 100%;
		border: 2px solid #ffffff;
		border-radius: 999px;
		box-shadow: 0 1px 4px rgba(0, 0, 0, 0.35);
		font-size: 0.75rem;
		font-weight: 700;
		font-variant-numeric: tabular-nums;
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
