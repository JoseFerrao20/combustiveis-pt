import App from './App.svelte';
import './base.css';

// O tema: o que se escolheu nas páginas do Evidence ("Aspeto"), ou o do sistema.
const root = document.documentElement;
const media = window.matchMedia('(prefers-color-scheme: dark)');
function applyTheme() {
	let chosen = 'system';
	try {
		chosen = localStorage.getItem('evidence-theme') ?? 'system';
	} catch {
		// Sem acesso ao armazenamento: o do sistema.
	}
	root.dataset.theme = chosen === 'light' || chosen === 'dark' ? chosen : media.matches ? 'dark' : 'light';
}
applyTheme();
media.addEventListener('change', applyTheme);

// Com pouca rede (ou nenhuma), a página abre com os últimos preços guardados (static/sw.js).
if ('serviceWorker' in navigator) {
	navigator.serviceWorker.register(`${import.meta.env.BASE_URL}sw.js`, { scope: import.meta.env.BASE_URL }).catch(() => {
		// Sem service worker, a página funciona na mesma, só não fica guardada.
	});
}

export default new App({ target: document.getElementById('app') });
