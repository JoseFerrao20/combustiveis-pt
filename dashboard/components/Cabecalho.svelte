<!--
	O cabeçalho de todas as páginas (app/): uma linha com o ícone, o nome do site e os links; no
	telemóvel, os links ficam num "Menu". As páginas por concelho e os dados abertos (HTML
	estático do `combustiveis site`) têm uma cópia simples em src/combustiveis/pages.py.

	`atual` é o caminho da página aberta (para marcar o link com aria-current).

	O botão do tema troca o claro e o escuro: muda o data-theme do <html> e guarda a escolha em
	`evidence-theme` (a chave do tempo do Evidence, mantida para quem já a tinha), lida por
	app/src/arranque.js e pelas páginas por concelho. Sem escolha, segue o sistema.
-->
<script>
	import { onMount } from 'svelte';

	export let base = '/combustiveis-pt/';
	export let atual = '';

	let tema = 'light';
	onMount(() => {
		tema = document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light';
		// O tema pode mudar depois (o do sistema): o botão acompanha.
		const observador = new MutationObserver(() => {
			tema = document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light';
		});
		observador.observe(document.documentElement, { attributeFilter: ['data-theme'] });
		return () => observador.disconnect();
	});

	function trocarTema() {
		tema = tema === 'dark' ? 'light' : 'dark';
		document.documentElement.setAttribute('data-theme', tema);
		try {
			localStorage.setItem('evidence-theme', tema);
		} catch {
			// Muda na mesma, só não fica guardado.
		}
	}

	const REPOSITORY = 'https://github.com/JoseFerrao20/combustiveis-pt';
	let aberto = false;

	$: links = [
		{ href: base, nome: 'Início' },
		{ href: `${base}resumo/`, nome: 'Resumo' },
		{ href: `${base}acompanhados/`, nome: 'Postos acompanhados' },
		{ href: `${base}ilhas/`, nome: 'Açores e Madeira' },
		{ href: `${base}analises/`, nome: 'Análises' }
	];
	const limpo = (caminho) => caminho.replace(/\/+$/, '');
	/** A página aberta, ou a secção dela (as análises ficam marcadas em "Análises"). */
	function marcado(href) {
		const aqui = limpo(atual);
		const link = limpo(href);
		if (link === limpo(base)) return aqui === link;
		return aqui === link || aqui.startsWith(`${link}/`);
	}
</script>

<header class="cabecalho">
	<a class="marca" href={base}>
		<img src="{base}icon.svg" alt="" width="24" height="24" />
		<span>Combustíveis em Portugal</span>
	</a>
	<div class="direita">
	<button
		type="button"
		class="tema-botao"
		aria-label={tema === 'dark' ? 'Mudar para o tema claro' : 'Mudar para o tema escuro'}
		title={tema === 'dark' ? 'Tema claro' : 'Tema escuro'}
		on:click={trocarTema}><span aria-hidden="true">{tema === 'dark' ? '☀' : '☾'}</span></button
	>
	<nav aria-label="Páginas do site">
		<button
			type="button"
			class="menu-botao"
			aria-expanded={aberto}
			aria-controls="menu-paginas"
			on:click={() => (aberto = !aberto)}>Menu</button
		>
		<ul id="menu-paginas" class:aberto>
			{#each links as link (link.href)}
				<li>
					<a
						href={link.href}
						aria-current={marcado(link.href) ? 'page' : undefined}
						on:click={() => (aberto = false)}>{link.nome}</a
					>
				</li>
			{/each}
			<li><a href={REPOSITORY} class="github">Código no GitHub</a></li>
		</ul>
	</nav>
	</div>
</header>

<style>
	.cabecalho {
		position: sticky;
		top: 0;
		z-index: 50;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		min-height: 3.25rem;
		padding: 0.5rem 1rem;
		background: rgba(255, 255, 255, 0.92);
		border-bottom: 1px solid rgba(127, 127, 127, 0.25);
		backdrop-filter: blur(6px);
		font-family: inherit;
	}
	:global([data-theme='dark']) .cabecalho {
		background: rgba(9, 9, 11, 0.92);
	}
	.marca {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-weight: 700;
		text-decoration: none;
		color: inherit;
	}
	.direita {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}
	.tema-botao {
		width: 2.25rem;
		height: 2.25rem;
		border: 1px solid rgba(127, 127, 127, 0.45);
		border-radius: 0.375rem;
		background: none;
		color: inherit;
		font-size: 1.1rem;
		line-height: 1;
		cursor: pointer;
	}
	nav {
		position: relative;
		font-size: 0.9rem;
	}
	ul {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		list-style: none;
		margin: 0;
		padding: 0;
	}
	ul a {
		display: block;
		padding: 0.4rem 0.7rem;
		border-radius: 0.375rem;
		text-decoration: none;
		color: inherit;
	}
	ul a:hover {
		background: rgba(127, 127, 127, 0.12);
	}
	ul a[aria-current='page'] {
		background: rgba(37, 99, 235, 0.12);
		color: #1d4ed8;
		font-weight: 600;
	}
	:global([data-theme='dark']) ul a[aria-current='page'] {
		color: #93c5fd;
	}
	.github {
		opacity: 0.85;
	}
	.menu-botao {
		display: none;
		min-height: 2.25rem;
		padding: 0.25rem 0.75rem;
		border: 1px solid rgba(127, 127, 127, 0.6);
		border-radius: 0.375rem;
		background: none;
		color: inherit;
		font: inherit;
		font-weight: 600;
		cursor: pointer;
	}
	@media (max-width: 760px) {
		.menu-botao {
			display: block;
		}
		ul {
			display: none;
			position: absolute;
			right: 0;
			top: calc(100% + 0.5rem);
			flex-direction: column;
			align-items: stretch;
			min-width: 14rem;
			padding: 0.25rem;
			background: #ffffff;
			border: 1px solid rgba(127, 127, 127, 0.3);
			border-radius: 0.5rem;
			box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
		}
		:global([data-theme='dark']) ul {
			background: #09090b;
		}
		ul.aberto {
			display: flex;
		}
		ul a {
			padding: 0.7rem 0.9rem;
		}
	}
</style>
