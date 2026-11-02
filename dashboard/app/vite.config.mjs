// A página inicial do site, fora do Evidence (ADR 0005). Corre depois do build do
// Evidence e escreve no mesmo build/: o index.html da raiz e os ficheiros em build/inicio/.
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
		assetsDir: 'inicio'
	}
});
