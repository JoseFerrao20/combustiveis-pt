// O arranque comum das páginas leves (a inicial, o resumo e os postos acompanhados): o tema e
// o service worker. Cada página importa este ficheiro antes de montar o seu componente.
import './base.css';

// O tema: o que se escolheu no botão do cabeçalho (chave do Evidence), ou o do sistema.
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

// Com pouca rede (ou nenhuma), a página inicial abre com os últimos preços guardados (static/sw.js).
if ('serviceWorker' in navigator) {
	navigator.serviceWorker.register(`${import.meta.env.BASE_URL}sw.js`, { scope: import.meta.env.BASE_URL }).catch(() => {
		// Sem service worker, a página funciona na mesma, só não fica guardada.
	});
}
