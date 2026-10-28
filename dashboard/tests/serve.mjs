// Serve o build do Evidence (build/) em /combustiveis-pt/, como o GitHub Pages, para os testes
// do Playwright. Só ficheiros estáticos; as páginas são pastas com um index.html.
import { createReadStream, existsSync, statSync } from 'node:fs';
import { createServer } from 'node:http';
import { extname, join, normalize } from 'node:path';

const BASE = '/combustiveis-pt';
const ROOT = new URL('../build/', import.meta.url).pathname;
const PORT = Number(process.env.PORT ?? 4173);
const TYPES = {
	'.html': 'text/html; charset=utf-8',
	'.js': 'text/javascript',
	'.css': 'text/css',
	'.json': 'application/json',
	'.svg': 'image/svg+xml',
	'.png': 'image/png',
	'.wasm': 'application/wasm',
	'.parquet': 'application/octet-stream',
	'.arrow': 'application/octet-stream'
};

createServer((request, response) => {
	const url = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
	if (!url.startsWith(BASE)) {
		response.writeHead(404).end();
		return;
	}
	let file = normalize(join(ROOT, url.slice(BASE.length)));
	if (!file.startsWith(ROOT)) {
		response.writeHead(403).end();
		return;
	}
	if (existsSync(file) && statSync(file).isDirectory()) file = join(file, 'index.html');
	if (!existsSync(file)) {
		response.writeHead(404).end();
		return;
	}
	response.writeHead(200, { 'Content-Type': TYPES[extname(file)] ?? 'application/octet-stream' });
	createReadStream(file).pipe(response);
}).listen(PORT, () => console.log(`Painel em http://localhost:${PORT}${BASE}/`));
