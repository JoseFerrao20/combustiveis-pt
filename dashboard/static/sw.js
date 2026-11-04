// O service worker do site, registado pela página inicial (app/src/main.js) e pelas páginas do
// Evidence (patch ao EvidenceDefaultLayout, que registava o fix-tprotocol-service-worker.js no
// mesmo âmbito: dois service workers no mesmo âmbito substituíam-se um ao outro).
//
// 1. Pouca rede: as páginas leves (a inicial, o resumo, os postos acompanhados e a dos Açores e
//    da Madeira) e os preços (dados/*.json) guardam-se no telemóvel, depois de abertas uma vez. Pede-se
//    sempre à rede primeiro; se a rede falhar, ou não responder em 4 segundos, usa-se o que
//    ficou guardado (e a resposta da rede, se chegar depois, fica para a próxima vez). As
//    respostas guardadas levam o cabeçalho x-combustiveis-guardado, para a página o dizer.
// 2. A correção do Evidence para os .parquet no Windows (o que fazia o
//    fix-tprotocol-service-worker.js): sem cache, para o DuckDB-WASM não falhar.
//
// Os mosaicos do mapa não se guardam: vêm de outro domínio, e o browser reserva muito espaço
// por cada resposta opaca. Sem rede, o mapa aparece sem fundo, mas com os postos e a tabela.

const CACHE = 'combustiveis-pt-1';
const BASE = new URL('./', self.location).pathname; // /combustiveis-pt/
const NETWORK_TIMEOUT_MS = 4000;
// As páginas leves, fora do Evidence (ADR 0005 a 0007), além da inicial.
const LIGHT_PAGES = ['resumo/', 'acompanhados/', 'ilhas/'].map((page) => BASE + page);

self.addEventListener('install', (event) => {
	self.skipWaiting();
	// A página inicial e os ficheiros que ela carrega (com o hash do Vite no nome).
	event.waitUntil(
		(async () => {
			const cache = await caches.open(CACHE);
			const response = await fetch(BASE, { cache: 'no-cache' });
			if (!response.ok) return;
			const html = await response.clone().text();
			await cache.put(BASE, response);
			const files = [...html.matchAll(/(?:src|href)="([^"]*\/inicio\/[^"]+)"/g)].map((m) => m[1]);
			await cache.addAll(files);
		})().catch(() => {
			// Sem rede na instalação: fica guardado na próxima visita.
		})
	);
});

self.addEventListener('activate', (event) => {
	event.waitUntil(
		(async () => {
			for (const key of await caches.keys()) {
				if (key !== CACHE) await caches.delete(key);
			}
			await self.clients.claim();
		})()
	);
});

/** Uma cópia da resposta guardada, com o cabeçalho que diz à página que não veio da rede. */
function marked(response) {
	const headers = new Headers(response.headers);
	headers.set('x-combustiveis-guardado', 'sim');
	return new Response(response.body, { status: response.status, statusText: response.statusText, headers });
}

/** A rede primeiro; o que ficou guardado se a rede falhar ou demorar mais de 4 segundos. */
async function networkFirst(event, key) {
	const cache = await caches.open(CACHE);
	// Sem a cache HTTP do browser: senão, sem rede, a resposta podia vir de lá (velha, e sem a
	// página saber). Com rede, custa só a confirmação de que não mudou (304).
	const network = fetch(event.request.url, { cache: 'no-cache', credentials: 'same-origin' }).then((response) => {
		if (response.ok) {
			const copy = response.clone();
			event.waitUntil(cache.put(key, copy));
		}
		return response;
	});
	const cached = await cache.match(key);
	if (!cached) return network;
	const timeout = new Promise((resolve) => setTimeout(() => resolve(null), NETWORK_TIMEOUT_MS));
	try {
		const response = await Promise.race([network, timeout]);
		if (response && response.ok) return response;
	} catch {
		// Sem rede: o que ficou guardado.
	}
	event.waitUntil(network.catch(() => null));
	return marked(cached);
}

/** Os ficheiros do Vite têm o hash no nome: o que ficou guardado nunca fica velho. */
async function cacheFirst(event) {
	const cache = await caches.open(CACHE);
	const cached = await cache.match(event.request);
	if (cached) return cached;
	const response = await fetch(event.request);
	if (response.ok) event.waitUntil(cache.put(event.request, response.clone()));
	return response;
}

self.addEventListener('fetch', (event) => {
	const { request } = event;
	if (request.method !== 'GET') return;
	const url = new URL(request.url);
	if (url.origin !== self.location.origin) return;

	if (url.pathname === BASE || url.pathname === `${BASE}index.html`) {
		event.respondWith(networkFirst(event, BASE));
	} else if (LIGHT_PAGES.includes(url.pathname.replace(/index\.html$/, ''))) {
		event.respondWith(networkFirst(event, url.pathname.replace(/index\.html$/, '')));
	} else if (url.pathname.startsWith(`${BASE}dados/`)) {
		event.respondWith(networkFirst(event, url.pathname));
	} else if (url.pathname.startsWith(`${BASE}inicio/`)) {
		event.respondWith(cacheFirst(event));
	} else if (url.pathname.endsWith('.parquet') && self.navigator.userAgent.includes('Windows')) {
		const headers = new Headers(request.headers);
		headers.set('Cache-Control', 'no-cache');
		headers.set('X-Evidence-Windows-Cache-Disable', 'true');
		event.respondWith(fetch(new Request(request.url, { headers })));
	}
});
