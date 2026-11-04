// As páginas leves do site, fora do Evidence (ADR 0005 e 0006): a inicial, o resumo e os
// postos acompanhados. Corre depois do build do Evidence e escreve no mesmo build/: o index.html
// da raiz, resumo/, acompanhados/ e os ficheiros em build/inicio/.
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';

export default defineConfig({
	root: fileURLToPath(new URL('.', import.meta.url)),
	base: '/combustiveis-pt/',
	plugins: [svelte()],
	build: {
		outDir: '../build',
		// O build do Evidence já lá está: só se junta o index.html e a pasta inicio/.
		emptyOutDir: false,
		assetsDir: 'inicio',
		rollupOptions: {
			input: {
				inicio: fileURLToPath(new URL('index.html', import.meta.url)),
				resumo: fileURLToPath(new URL('resumo/index.html', import.meta.url)),
				acompanhados: fileURLToPath(new URL('acompanhados/index.html', import.meta.url)),
				ilhas: fileURLToPath(new URL('ilhas/index.html', import.meta.url))
			}
		}
	}
});
