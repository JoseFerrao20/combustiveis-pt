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
	import { onDestroy, onMount, tick } from 'svelte';
	import 'leaflet/dist/leaflet.css';

	/** Resultado de uma consulta do Evidence (um store com as linhas). */
	export let data;
	export let height = 520;
	/** Linhas da tabela de cada vez; "Mostrar mais" junta outras tantas. */
	export let pageSize = 15;
	/** O combustível escolhido no filtro da página, para o guardar e voltar a escolhê-lo. */
	export let combustivel = undefined;
	/** Quantos filtros da zona (distrito, concelho) a página tem escolhidos, para o "Filtros". */
	export let zoneFilters = 0;
	/** O id da DGEG do posto a mostrar ao abrir (de um link partilhado, `?posto=`). */
	export let postoInicial = null;
	/** O nome do combustível escolhido, para o texto da partilha. */
	export let nomeCombustivel = '';
	let postoInicialVisto = false;
	let postoNaoEncontrado = false;

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
	/** Marca no browser que a pessoa já usou "Perto de mim", para a página abrir logo ali. */
	const LOCATION_KEY = 'combustiveis-pt:localizacao';
	let remembersLocation = false;
	let triedAutoLocate = false;

	/**
	 * Ao abrir, usa logo a localização se o browser já a deu a este site (ou, sem essa
	 * informação, se a pessoa a usou da última vez). Nunca pergunta a quem disse que não.
	 */
	async function autoLocate() {
		if (!canLocate) return;
		try {
			remembersLocation = localStorage.getItem(LOCATION_KEY) === '1';
		} catch {
			remembersLocation = false;
		}
		let state = 'unknown';
		try {
			state = (await navigator.permissions?.query({ name: 'geolocation' }))?.state ?? 'unknown';
		} catch {
			// Sem a API das permissões: conta só a escolha guardada.
		}
		if (state === 'granted' || (state !== 'denied' && remembersLocation)) locate();
	}

	function forgetLocation() {
		remembersLocation = false;
		try {
			localStorage.removeItem(LOCATION_KEY);
		} catch {
			// Nada a esquecer.
		}
	}

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

	/** O dia de hoje em Lisboa (AAAA-MM-DD): as horas dos preços são de Lisboa. */
	const today = new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Lisbon' }).format(new Date());

	/** Quantos dias passaram desde a atualização do preço (pela data de Lisboa). */
	function ageDays(value) {
		if (value == null) return null;
		const date = value instanceof Date ? value : new Date(value);
		if (Number.isNaN(date.getTime())) return null;
		return Math.round((Date.parse(today) - Date.parse(date.toISOString().slice(0, 10))) / 86400000);
	}

	/** "hoje, 12:25", "ontem, 08:10" ou "28/10, 08:35": a data e a hora, curtas. */
	function whenShort(value) {
		if (value == null) return '';
		const date = value instanceof Date ? value : new Date(value);
		const pad = (n) => String(n).padStart(2, '0');
		const time = `${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())}`;
		const age = ageDays(value);
		if (age === 0) return `hoje, ${time}`;
		if (age === 1) return `ontem, ${time}`;
		return `${pad(date.getUTCDate())}/${pad(date.getUTCMonth() + 1)}, ${time}`;
	}

	/** Um preço com mais de uma semana pode já não estar em vigor. */
	const isOld = (value) => (ageDays(value) ?? 0) > 7;

	// Os nomes vêm da DGEG muitas vezes só em maiúsculas: passam a maiúscula só no início de
	// cada palavra, com as siglas (BP, DPP) e os números romanos como estão.
	const SMALL_WORDS = new Set(['de', 'da', 'do', 'das', 'dos', 'e', 'a', 'o', 'em', 'na', 'no']);
	const ROMAN = /^(i{1,3}|iv|v|vi{1,3}|ix|x)$/;
	function tidy(text) {
		if (!text) return '';
		const allCaps = !/[a-zà-ÿ]/.test(text);
		let first = true;
		return text.replace(/[^\s.\-/()]+/g, (original) => {
			const isFirst = first;
			first = false;
			// Num nome misto ("AUCHAN Gondomar"), só mudam as palavras longas em maiúsculas.
			if (!allCaps && (/[a-zà-ÿ]/.test(original) || original.length < 4)) return original;
			const word = original.toLowerCase();
			if (!isFirst && SMALL_WORDS.has(word)) return word;
			if (ROMAN.test(word) || (word.length <= 3 && !/[aeiouáéíóúâêôãõà]/.test(word))) {
				return word.toUpperCase();
			}
			return word[0].toUpperCase() + word.slice(1);
		});
	}
	const nameOf = (row) => tidy(row.station_name);
	/** O nome de uma marca como aparece: "Genérico" (assim na DGEG) é "Sem marca". */
	const brandLabel = (name) => (name === 'Genérico' ? 'Sem marca' : tidy(name));
	const brandOf = (row) => brandLabel(row.brand);
	/** A marca, só se não estiver já no nome do posto (e sem "Genérico"). */
	const brandIfNew = (row) =>
		row.brand === 'Genérico' || plain(row.station_name).includes(plain(row.brand)) ? '' : brandOf(row);

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
				remembersLocation = true;
				try {
					localStorage.setItem(LOCATION_KEY, '1');
				} catch {
					// Não fica lembrada, mas funciona.
				}
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

	/** "▼ 2,0 c", com a unidade (cêntimos), ou "=". */
	function changeShort(row) {
		const text = change(row);
		return text && text !== '=' ? `${text} c` : text;
	}

	$: activeFilters = zoneFilters + (brand ? 1 : 0) + (noMotorway ? 1 : 0);

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
		return `<strong>${escape(nameOf(row))}</strong><br>${escape(brandOf(row))} · ${escape(row.municipality)}<br>${euros(row.price)}${change(row) && change(row) !== '=' ? ` (${changeLabel(row)})` : ''}<br><small>Atualizado: ${when(row.updated_at)}</small>${row.recent_history ? `<br><small>Últimas fotografias: ${escape(row.recent_history)}</small>` : ''}${dateOrNull(row.last_change_date) ? `<br><small>Última mudança de preço: ${day(dateOrNull(row.last_change_date))}</small>` : ''}<br><a href="${directions(row)}" target="_blank" rel="noopener">Ir até lá (Google Maps)</a> · <button type="button" class="partilhar-posto" data-key="${row.key}">Partilhar</button>`;
	}

	let fitted = null;

	/** O link deste posto (abre a página já nele, com o mesmo combustível). */
	function linkDoPosto(row) {
		const url = new URL(window.location.pathname, window.location.origin);
		url.searchParams.set('posto', row.station_id);
		if (combustivel) url.searchParams.set('combustivel', combustivel);
		return url.href;
	}

	/** Partilha o link (no telemóvel, com o menu de partilha) ou copia-o. */
	async function partilhar(row, botao) {
		const url = linkDoPosto(row);
		const texto = `${nameOf(row)} (${row.municipality}): ${euros(row.price)}${nomeCombustivel ? ` (${nomeCombustivel})` : ''}`;
		try {
			if (navigator.share) {
				await navigator.share({ title: nameOf(row), text: texto, url });
				return;
			}
			await navigator.clipboard.writeText(url);
			if (botao) botao.textContent = 'Link copiado';
		} catch (error) {
			// Cancelar o menu de partilha não é um erro; sem área de transferência, mostra o link.
			if (error?.name !== 'AbortError' && botao) botao.replaceWith(Object.assign(document.createElement('span'), { textContent: url }));
		}
	}

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
		// Um link partilhado abre no posto (e não na localização da pessoa).
		if (postoInicial && !postoInicialVisto && allRows.length) {
			postoInicialVisto = true;
			triedAutoLocate = true;
			const row = allRows.find((r) => String(r.station_id) === String(postoInicial));
			if (row) focus(row);
			else postoNaoEncontrado = true;
		}
		if (!triedAutoLocate && rows.length) {
			triedAutoLocate = true;
			autoLocate();
		}
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
		if (order === 'distancia' && here) {
			return list.sort((a, b) => distanceKm(here, a) - distanceKm(here, b) || byPrice(a, b));
		}
		return list.sort(byPrice);
	}

	// Ao mudar a ordem, o depósito ou o consumo, a tabela reordena-se sem mexer no mapa.
	$: if (map) {
		order, savings, here;
		visible = sortRows([...visible]);
	}

	/** No telemóvel (até 640 px), a lista e o mapa são separadores; no computador, os dois. */
	let narrow = false;
	let view = 'lista';
	$: showList = !narrow || view === 'lista';
	$: showMap = !narrow || view === 'mapa';

	async function focus(row) {
		if (narrow && view !== 'mapa') {
			view = 'mapa';
			await tick();
		}
		// Sem animação, o mapa redesenha-se logo com os postos soltos (zoom 14), e o balão abre.
		map.setView([row.latitude, row.longitude], Math.max(map.getZoom(), 14), { animate: false });
		markers.get(row.key)?.openPopup();
		element.scrollIntoView?.({ block: 'nearest', behavior: 'smooth' });
	}

	onMount(async () => {
		L = (await import('leaflet')).default;
		map = L.map(element, { preferCanvas: true, scrollWheelZoom: false });
		L.tileLayer(TILES, { attribution: ATTRIBUTION, maxZoom: 18 }).addTo(map);
		layer = L.layerGroup().addTo(map);
		map.setView([39.6, -8.0], 7);
		map.on('moveend', update);
		map.on('popupopen', (event) => {
			const botao = event.popup.getElement()?.querySelector('.partilhar-posto');
			const row = allRows.find((r) => String(r.key) === botao?.dataset.key);
			if (botao && row) botao.addEventListener('click', () => partilhar(row, botao));
		});
		map.on('zoomend', () => {
			if (drawn !== null) drawMarkers();
		});
		loadSettings();
		loadFavorites();
		loadFilters();
		const media = window.matchMedia('(max-width: 640px)');
		const onMedia = () => (narrow = media.matches);
		onMedia();
		media.addEventListener('change', onMedia);
	});

	onDestroy(() => map?.remove());
</script>

<div class="mapa-postos my-4" data-postos={drawn === null ? undefined : rows.length}>
	<!-- O primeiro ecrã: o combustível (da página) e "Perto de mim", a procura e os filtros. -->
	<div class="topo-postos">
		<slot name="combustivel" />
		{#if canLocate}
			<button type="button" class="perto-botao" on:click={locate} disabled={locating || !map}>
				<span aria-hidden="true">◎</span>
				{locating ? 'A procurar…' : 'Perto de mim'}
			</button>
		{/if}
	</div>
	{#if locationError}<p class="text-sm" role="alert">{locationError}</p>{/if}
	{#if postoNaoEncontrado}
		<p class="text-sm" role="status">
			O posto do link não tem preço atualizado deste combustível. Experimente outro combustível.
		</p>
	{/if}
	{#if here && remembersLocation}
		<p class="text-sm text-base-content-muted lembrar">
			A página abre já aqui da próxima vez (a localização não sai do telemóvel).
			<button type="button" class="ligacao" on:click={forgetLocation}>Não abrir aqui</button>
		</p>
	{/if}

	<div class="procurar">
		<label for="procurar-postos" class="sr-only">Procurar uma localidade ou um posto</label>
		<input
			id="procurar-postos"
			type="search"
			bind:value={query}
			placeholder="Procurar uma localidade ou um posto"
			autocomplete="off"
			disabled={!map}
		/>
		{#if results.length}
			<ul class="resultados" aria-label="Resultados da procura">
				{#each results as result (result.id)}
					<li>
						<button type="button" on:click={() => choose(result)}>
							<span>{result.kind === 'posto' ? nameOf(result.row) : result.name}</span>
							<span class="text-sm text-base-content-muted">
								{#if result.kind === 'posto'}
									posto · {brandOf(result.row)} · {result.row.municipality} · {euros(result.row.price)}
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

	<details class="filtros-postos text-sm">
		<summary>
			Filtros{#if activeFilters}<span class="contagem">
					· {activeFilters} {activeFilters === 1 ? 'escolhido' : 'escolhidos'}</span
				>{/if}
		</summary>
		<div class="filtros-corpo">
			<slot name="zona" />
			<label>
				Marca
				<select bind:value={brand} on:change={saveFilters}>
					<option value="">Todas</option>
					{#each brands as option (option.name)}
						<option value={option.name}>{brandLabel(option.name)} ({option.count})</option>
					{/each}
				</select>
			</label>
			<label class="caixa">
				<input type="checkbox" bind:checked={noMotorway} on:change={saveFilters} />
				Sem postos de autoestrada
			</label>
			{#if here}
				<!-- Para a coluna "Poupa": o depósito e o consumo (com a distância em linha reta × 1,3). -->
				<label>
					Depósito (L)
					<input type="number" min="5" max="200" step="1" bind:value={tank} on:change={saveSettings} />
				</label>
				<label>
					Consumo (L/100 km)
					<input
						type="number"
						min="2"
						max="30"
						step="0.1"
						bind:value={consumption}
						on:change={saveSettings}
					/>
				</label>
			{/if}
		</div>
	</details>

	{#if favoriteRows.length}
		<section class="meus-postos" aria-labelledby="meus-postos-titulo">
			<h2 id="meus-postos-titulo" class="text-lg font-semibold">Os meus postos</h2>
			<ul>
				{#each favoriteRows as row (row.key)}
					<li>
						<button type="button" class="nome" on:click={() => focus(row)} title="Ver no mapa">
							<span class="cor" style="background: {color(row.price)}" />
							{nameOf(row)}
						</button>
						<span class="text-sm text-base-content-muted marca">{brandOf(row)} · {row.municipality}</span>
						<span class="preco">{euros(row.price)}</span>
						<span class="variacao {changeClass(row)}">
							<span aria-hidden="true">{changeShort(row)}</span>
							<span class="sr-only">{changeLabel(row)}</span>
						</span>
						<a
							class="ir"
							href={directions(row)}
							target="_blank"
							rel="noopener"
							aria-label="Ir até {nameOf(row)} (Google Maps)">Ir</a
						>
						<button
							type="button"
							class="estrela"
							aria-pressed="true"
							on:click={() => toggleFavorite(row)}
							><span aria-hidden="true">★</span><span class="sr-only"
								>Tirar {nameOf(row)} dos meus postos</span
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
										on:click={() => focus(info.cheapest.row)}>{nameOf(info.cheapest.row)}</button
									>, a {km(info.cheapest.distance)}).
								{:else if info.position === 1}
									<strong>Um dos mais baratos</strong> dos {info.count + 1} postos a {NEAR_KM} km: o mesmo
									preço que <button type="button" class="ligacao" on:click={() => focus(info.cheapest.row)}
										>{nameOf(info.cheapest.row)}</button
									>, a {km(info.cheapest.distance)}.
								{:else}
									<strong>{info.position}.º</strong> mais barato dos {info.count + 1} postos a {NEAR_KM} km.
									O mais barato é
									<button type="button" class="ligacao" on:click={() => focus(info.cheapest.row)}
										>{nameOf(info.cheapest.row)}</button
									>, a {km(info.cheapest.distance)}: menos {cents(row.price - info.cheapest.row.price)}.
								{/if}
							</p>
						{/if}
					</li>
				{/each}
			</ul>
			{#if missingFavorites > 0}
				<p class="text-sm text-base-content-muted">
					{missingFavorites === 1 ? 'Um dos seus postos não aparece' : `${missingFavorites} dos seus postos não aparecem`}
					com o combustível, o distrito e o concelho escolhidos (ou não têm o preço atualizado).
				</p>
			{/if}
		</section>
	{/if}

	<!-- No telemóvel, a lista e o mapa são separadores. O mapa escondido continua desenhado (fora
	     do ecrã, com o mesmo tamanho), porque a lista são os postos da parte do mapa que se vê. -->
	<div class="vistas" role="group" aria-label="Ver os postos">
		<button type="button" aria-pressed={view === 'lista'} on:click={() => (view = 'lista')}>Lista</button>
		<button type="button" aria-pressed={view === 'mapa'} on:click={() => (view = 'mapa')}>Mapa</button>
	</div>

	<!-- No computador largo, o mapa (fixo) à esquerda e a lista à direita. -->
	<div class="corpo">
	<div class="painel-mapa" class:fora={!showMap} inert={!showMap}>
		<div bind:this={element} style="--altura: min({height}px, 60vh)" class="mapa rounded border border-base-300" />
		{#if breaks.length}
			<p class="legenda text-sm">
				<span>Mais barato</span>
				{#each COLORS as fill}<span class="cor" style="background: {fill}" />{/each}
				<span>Mais caro</span>
				<span class="text-base-content-muted">
					({euros(Math.min(...rows.map((r) => r.price)))} a {euros(Math.max(...rows.map((r) => r.price)))}).
					Os círculos com números juntam postos próximos: toque para aproximar.
				</span>
			</p>
		{/if}
	</div>

	<div class="painel-lista" class:escondida={!showList}>
		<p class="text-sm" aria-live="polite">
			{#if visible.length}
				{visible.length.toLocaleString('pt-PT')}
				{visible.length === 1 ? 'posto' : 'postos'}
				{here ? 'à volta' : 'na zona do mapa'}{#if brand || noMotorway}
					({[brand && `só ${brandLabel(brand)}`, noMotorway && 'sem autoestradas'].filter(Boolean).join(', ')})
				{/if}.
			{:else}
				Nenhum posto na parte do mapa que se vê.
			{/if}
			{#if subiram + desceram > 0}
				Desde {previousDay ? `a fotografia de ${previousDay}` : 'a fotografia anterior'}, {subiram.toLocaleString('pt-PT')} {subiram === 1 ? 'subiu' : 'subiram'} e
				{desceram.toLocaleString('pt-PT')} {desceram === 1 ? 'desceu' : 'desceram'} de preço.
			{/if}
		</p>

		{#if here}
			<p class="poupanca text-sm">
				<label>
					Ordenar por
					<select bind:value={order}>
						<option value="preco">preço</option>
						<option value="distancia">distância</option>
						<option value="poupanca">poupança</option>
					</select>
				</label>
			</p>
			{#if nearest && validSettings}
				<p class="text-sm text-base-content-muted">
					"Poupa": um depósito de {tank.toLocaleString('pt-PT')} L face ao posto mais perto
					({nameOf(nearest)}), já com a ida e volta. O depósito e o consumo mudam-se em "Filtros".
				</p>
			{/if}
		{/if}

		{#if visible.length}
			<table class="tabela-postos text-sm">
				<thead>
					<tr>
						<th class="num larga">#</th>
						<th><span class="sr-only">Os meus postos</span></th>
						<th>Posto</th>
						<th class="larga">Marca</th>
						<th class="larga">Concelho</th>
						<th class="num">Preço (€/L)</th>
						<th class="num media" title="Em cêntimos por litro">Na semana</th>
						{#if here}<th class="num media">Distância</th>{/if}
						{#if nearest && validSettings}<th class="num">Poupa</th>{/if}
						<th class="larga">Atualizado</th>
						<th><span class="sr-only">Caminho</span></th>
					</tr>
				</thead>
				<tbody>
					{#each visible.slice(0, shown) as row, index (row.key)}
						<tr>
							<td class="num larga">{index + 1}</td>
							<td>
								<button
									type="button"
									class="estrela"
									aria-pressed={favorites.includes(Number(row.station_id))}
									on:click={() => toggleFavorite(row)}
									><span aria-hidden="true"
										>{favorites.includes(Number(row.station_id)) ? '★' : '☆'}</span
									><span class="sr-only">Guardar {nameOf(row)} nos meus postos</span></button
								>
							</td>
							<td>
								<button type="button" on:click={() => focus(row)} title="Ver no mapa">
									<span class="cor" style="background: {color(row.price)}" />
									<span class="nome-posto">{nameOf(row)}</span>
								</button>
								<!-- No telemóvel, a marca (se não estiver no nome), o concelho, a distância e a
								     data vão aqui, em vez de colunas. -->
								<span class="estreita"
									>{[brandIfNew(row), row.municipality].filter(Boolean).join(' · ')}{#if here}<span
											class="so-telemovel"> · {km(distanceKm(here, row))}</span
										>{/if} · {whenShort(row.updated_at)}{#if isOld(row.updated_at)}<span class="antigo">
											· há mais de uma semana</span
										>{/if}</span
								>
							</td>
							<td class="larga">{brandOf(row)}</td>
							<td class="larga">{row.municipality}</td>
							<td class="num preco-celula">
								{euros(row.price).replace(' €', '')}
								<!-- No telemóvel, a variação vai debaixo do preço. -->
								<span class="estreita so-telemovel variacao {changeClass(row)}">
									<span aria-hidden="true">{changeShort(row)}</span>
									<span class="sr-only">{changeLabel(row)}</span>
								</span>
							</td>
							<td class="num media variacao {changeClass(row)}">
								<span aria-hidden="true">{changeShort(row)}</span>
								<span class="sr-only">{changeLabel(row)}</span>
							</td>
							{#if here}<td class="num media distancia">{km(distanceKm(here, row))}</td>{/if}
							{#if nearest && validSettings}<td class="num poupa {savingClass(row)}">{saving(row)}</td>{/if}
							<td class="larga"
								>{whenShort(row.updated_at)}{#if isOld(row.updated_at)}<span class="antigo">
										(há mais de uma semana)</span
									>{/if}</td
							>
							<td>
								<a
									class="ir"
									href={directions(row)}
									target="_blank"
									rel="noopener"
									aria-label="Ir até {nameOf(row)} (Google Maps)">Ir</a
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
			{#if !favorites.length}
				<p class="text-sm text-base-content-muted dica">
					Toque na estrela (☆) de um posto para o ter sempre no topo da página. A lista fica só neste
					telemóvel ou computador.
				</p>
			{/if}
		{/if}
	</div>
	</div>
</div>

<style>
	/* Os painéis do Leaflet têm z-index até 1000: sem um contexto próprio, o mapa passava por
	   cima do cabeçalho fixo da página ao fazer scroll. */
	.mapa-postos {
		position: relative;
		isolation: isolate;
		z-index: 0;
	}
	/* O combustível (da página, pelo slot) e "Perto de mim", lado a lado no topo. */
	.topo-postos {
		display: flex;
		align-items: flex-end;
		gap: 0.5rem 0.75rem;
		flex-wrap: wrap;
		margin-bottom: 0.75rem;
	}
	.perto-botao {
		min-height: 2.75rem;
		padding: 0.5rem 1.25rem;
		border-radius: 0.5rem;
		background: #2563eb;
		color: #ffffff;
		font-weight: 600;
		font-size: 1rem;
	}
	.lembrar {
		margin: -0.25rem 0 0.75rem;
	}
	/* Os separadores "Lista" e "Mapa": só no telemóvel. */
	.vistas {
		display: none;
	}
	.antigo {
		color: #92400e;
	}
	:global([data-theme='dark']) .antigo {
		color: #fbbf24;
	}
	.painel-mapa.fora {
		/* Fora do ecrã, mas com o tamanho de sempre: a lista são os postos que o mapa mostra. */
		position: absolute;
		left: -10000px;
		top: 0;
		width: calc(100vw - 2rem);
	}
	.painel-lista.escondida {
		display: none;
	}
	.mapa {
		height: var(--altura);
	}
	/* No computador largo: o mapa fixo à esquerda (quase da altura do ecrã) e a lista à direita,
	   com a marca, o concelho e a data por baixo do nome, como no telemóvel. */
	@media (min-width: 1024px) {
		.corpo {
			display: grid;
			grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr);
			gap: 1.25rem;
			align-items: start;
		}
		.painel-mapa {
			position: sticky;
			top: 4rem;
		}
		.mapa {
			height: calc(100vh - 8rem);
			min-height: 22rem;
		}
		.tabela-postos .larga,
		.so-telemovel {
			display: none;
		}
		.estreita {
			display: block;
			font-size: 0.75rem;
			opacity: 0.75;
		}
	}
	.dica {
		margin-top: 0.75rem;
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
		.tabela-postos .media {
			display: none;
		}
		/* Nomes de empresas muito compridos: duas linhas no máximo (o nome todo está no balão). */
		.tabela-postos td > button[title] {
			display: flex;
			align-items: baseline;
			gap: 0.3rem;
			text-align: left;
		}
		.tabela-postos td > button[title] .cor {
			flex: none;
		}
		.nome-posto {
			display: -webkit-box;
			-webkit-line-clamp: 2;
			-webkit-box-orient: vertical;
			overflow: hidden;
		}
		.vistas {
			display: flex;
			margin: 0.75rem 0;
			border: 1px solid rgba(127, 127, 127, 0.5);
			border-radius: 0.5rem;
			overflow: hidden;
		}
		.vistas button {
			flex: 1;
			min-height: 2.5rem;
			font-weight: 600;
		}
		.vistas button[aria-pressed='true'] {
			background: #2563eb;
			color: #ffffff;
		}
		.perto-botao {
			flex: 1;
		}
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
	.procurar input {
		width: 100%;
		max-width: 28rem;
		min-height: 2.75rem;
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
		margin: 0 0 0.75rem;
	}
	.filtros-postos summary {
		cursor: pointer;
		font-weight: 600;
		padding: 0.25rem 0;
	}
	.filtros-postos .contagem {
		font-weight: 400;
	}
	/* Os filtros: os da zona (da página, pelo slot), a marca e as autoestradas. */
	.filtros-corpo {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-end;
		gap: 0.5rem 1rem;
		padding: 0.5rem 0 0.25rem;
	}
	.filtros-corpo label,
	.filtros-corpo :global(label) {
		display: flex;
		flex-direction: column;
		font-weight: 600;
	}
	.filtros-corpo label.caixa {
		flex-direction: row;
		align-items: center;
		gap: 0.35rem;
		font-weight: 400;
		min-height: 2.25rem;
	}
	.filtros-corpo input[type='number'] {
		margin-top: 0.25rem;
		width: 8rem;
		padding: 0.375rem 0.5rem;
		border: 1px solid rgba(127, 127, 127, 0.6);
		border-radius: 0.25rem;
		background: transparent;
		color: inherit;
		font-weight: 400;
	}
	.filtros-corpo select,
	.filtros-corpo :global(select) {
		margin-top: 0.25rem;
		min-width: 10rem;
		max-width: 16rem;
		padding: 0.375rem 0.5rem;
		border: 1px solid rgba(127, 127, 127, 0.6);
		border-radius: 0.25rem;
		background: transparent;
		color: inherit;
		font-weight: 400;
	}
	.sr-only {
		position: absolute;
		width: 1px;
		height: 1px;
		overflow: hidden;
		clip: rect(0, 0, 0, 0);
		white-space: nowrap;
	}
	/* O botão "Partilhar" do balão (HTML do Leaflet, fora do componente). */
	.mapa-postos :global(.partilhar-posto) {
		color: #1d4ed8;
		text-decoration: underline;
		background: none;
		border: 0;
		padding: 0;
		font: inherit;
		cursor: pointer;
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
