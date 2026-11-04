// O site todo (ADR 0005, 0006 e 0008): páginas estáticas feitas com o Vite e o Svelte, uma por
// entrada, com o código comum em build/inicio/. app/public/ (ícones, manifesto, service worker,
// e os JSON e páginas que o `combustiveis site` escreve) vai tal e qual para a raiz do build/.
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';

const PAGINAS = [
	'index.html',
	'resumo/index.html',
	'acompanhados/index.html',
	'ilhas/index.html',
	'analises/index.html',
	'analises/impostos/index.html',
	'analises/previsao/index.html',
	'analises/comparacao/index.html',
	'analises/metodo/index.html'
];

export default defineConfig({
	root: fileURLToPath(new URL('.', import.meta.url)),
	base: '/combustiveis-pt/',
	plugins: [svelte()],
	build: {
		outDir: '../build',
		emptyOutDir: true,
		assetsDir: 'inicio',
		rollupOptions: {
			input: Object.fromEntries(
				PAGINAS.map((pagina) => [
					pagina === 'index.html' ? 'inicio' : pagina.replace('/index.html', '').replace('/', '-'),
					fileURLToPath(new URL(pagina, import.meta.url))
				])
			)
		}
	}
});
