// Formatos e utilidades comuns às páginas leves (resumo e postos acompanhados).
export const BASE = import.meta.env.BASE_URL;
const pad = (n) => String(n).padStart(2, '0');

/** Lê um JSON de dados/ (escrito pelo `combustiveis site`). */
export async function lerJson(nome) {
	const response = await fetch(`${BASE}dados/${nome}`);
	if (!response.ok) throw new Error(`HTTP ${response.status}`);
	return response.json();
}

/** As linhas de um postos-<combustível>.json, como objetos. */
export const linhas = (ficheiro) =>
	ficheiro.stations.map((linha) => Object.fromEntries(ficheiro.columns.map((coluna, i) => [coluna, linha[i]])));

/** "2,061 €" */
export const euros = (valor) =>
	valor == null ? '–' : `${valor.toLocaleString('pt-PT', { minimumFractionDigits: 3, maximumFractionDigits: 3 })} €`;

/** "−9,0 c" ou "+2,4 c" (cêntimos, a partir de uma diferença em euros). */
export function centimos(diferenca, comSinal = true) {
	if (diferenca == null) return '–';
	const c = Math.round(diferenca * 1000) / 10;
	const texto = Math.abs(c).toLocaleString('pt-PT', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
	if (!comSinal) return `${texto} c`;
	return `${c > 0 ? '+' : c < 0 ? '−' : ''}${texto} c`;
}

/** "▼ 15,2 c" (mais barato) ou "▲ 1,0 c", e a classe da cor. */
export function seta(diferenca) {
	if (diferenca == null) return { texto: '–', classe: '' };
	const c = Math.round(diferenca * 1000) / 10;
	const texto = Math.abs(c).toLocaleString('pt-PT', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
	if (c < 0) return { texto: `▼ ${texto} c`, classe: 'seta-baixo' };
	if (c > 0) return { texto: `▲ ${texto} c`, classe: 'seta-cima' };
	return { texto: '= 0,0 c', classe: '' };
}

export const inteiro = (n) => (n ?? 0).toLocaleString('pt-PT');

/** "02/11/2026" ou "02/11/2026 07:30" (as horas vêm como a hora de Lisboa, em UTC). */
export function quando(texto, comHora = false) {
	if (!texto) return '';
	const d = new Date(texto);
	const dia = `${pad(d.getUTCDate())}/${pad(d.getUTCMonth() + 1)}/${d.getUTCFullYear()}`;
	return comHora ? `${dia} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}` : dia;
}

/** "02/11" */
export const diaCurto = (texto) => quando(texto).slice(0, 5);

/** 'Vila Nova de Gaia' -> 'vila-nova-de-gaia', como os endereços das páginas por concelho. */
export const slug = (texto) =>
	texto
		.normalize('NFKD')
		.replace(/[̀-ͯ]/g, '')
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, '-')
		.replace(/^-|-$/g, '');

/** 'distrito do Porto', 'distrito da Guarda', 'distrito de Braga'. */
export const doDistrito = (nome) => `distrito ${{ Porto: 'do', Guarda: 'da' }[nome] ?? 'de'} ${nome}`;

/** Lê e guarda o combustível escolhido (a mesma chave da página inicial). */
export function combustivelGuardado() {
	try {
		return localStorage.getItem('combustiveis-pt:combustivel') ?? 'gasolina_95';
	} catch {
		return 'gasolina_95';
	}
}
export function guardarCombustivel(valor) {
	try {
		localStorage.setItem('combustiveis-pt:combustivel', valor);
	} catch {
		// Não fica guardado.
	}
}

/** Um { columns, rows } dos JSON (listas pela ordem das colunas), como objetos. */
export const tabela = ({ columns, rows }) =>
	rows.map((linha) => Object.fromEntries(columns.map((coluna, i) => [coluna, linha[i]])));

/** "46,5 %" (de 0,465). */
export const pct = (valor, casas = 1) =>
	valor == null
		? '–'
		: `${(valor * 100).toLocaleString('pt-PT', { minimumFractionDigits: casas, maximumFractionDigits: casas })} %`;

/** "2,10 €" (duas casas, para os eixos dos gráficos de euros). */
export const euros2 = (valor) =>
	valor == null ? '–' : `${valor.toLocaleString('pt-PT', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €`;

/** Os produtos do boletim que se escolhem nas análises, com o nome; guarda o escolhido. */
export function produtoGuardado() {
	try {
		return localStorage.getItem('combustiveis-pt:produto') ?? 'euro95';
	} catch {
		return 'euro95';
	}
}
export function guardarProduto(valor) {
	try {
		localStorage.setItem('combustiveis-pt:produto', valor);
	} catch {
		// Não fica guardado.
	}
}
