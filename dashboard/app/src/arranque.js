// O arranque comum de todas as páginas: o tema e
// o service worker. Cada página importa este ficheiro antes de montar o seu componente.
import './base.css';

// O tema: o que se escolheu no botão do cabeçalho (a chave `evidence-theme`, do tempo do
// Evidence, mantida para quem já a tinha), ou o do sistema.
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

// Com pouca rede (ou nenhuma), as páginas abrem com os últimos dados guardados (app/public/sw.js).
if ('serviceWorker' in navigator) {
	navigator.serviceWorker.register(`${import.meta.env.BASE_URL}sw.js`, { scope: import.meta.env.BASE_URL }).catch(() => {
		// Sem service worker, a página funciona na mesma, só não fica guardada.
	});
}
