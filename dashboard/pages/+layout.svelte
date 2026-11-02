<script>
	import '@evidence-dev/tailwind/fonts.css';
	import '../app.css';
	import { EvidenceDefaultLayout } from '@evidence-dev/core-components';
	import { page } from '$app/stores';
	import Cabecalho from '../components/Cabecalho.svelte';
	import Rodape from '../components/Rodape.svelte';
	export let data;
</script>

<!-- O cabeçalho e o rodapé são os mesmos da página inicial (components/): o cabeçalho e a
     barra lateral do Evidence ficam escondidos, e os links das páginas estão no cabeçalho. -->
<Cabecalho atual={$page.url.pathname} />

<EvidenceDefaultLayout
	{data}
	title="Combustíveis em Portugal"
	homePageName="Início"
	githubRepo="https://github.com/JoseFerrao20/combustiveis-pt"
	hideHeader={true}
	hideSidebar={true}
	builtWithEvidence={false}
	maxWidth={1120}
	hideTOC={true}
	hideBreadcrumbs={true}
	neverShowQueries={true}
>
	<div slot="content" class="conteudo">
		<slot />
		<Rodape evidence />
	</div>
</EvidenceDefaultLayout>

<style>
	/* A barra lateral do Evidence põe cada palavra com maiúscula ("Portugal E A Europa"),
	   com a classe capitalize do Tailwind: os títulos das páginas já vêm escritos como devem
	   aparecer. O painel não usa os outros componentes com essa classe (mapas). */
	:global(.capitalize) {
		text-transform: none;
	}
	/* Escala de cores das tabelas (contentType=colorscale): no tema escuro, o Evidence leva o
	   máximo a um vermelho escuro (#bb0001), e o texto cinzento claro fica abaixo de 4,5:1. */
	:global([data-theme='dark'] td[style*='background-color']) {
		color: #ffffff !important;
	}
	/* A previsão de segunda-feira, no topo da página inicial. */
	:global(.previsao-segunda) {
		border-left: 4px solid #d97706;
		background: rgba(217, 119, 6, 0.08);
		padding: 0.5rem 0.75rem;
		border-radius: 0.25rem;
		margin: 0.75rem 0;
	}
	/* Cartões (resumo, postos acompanhados e análises): números grandes, com o rótulo por cima. */
	:global(.cartoes) {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(9.5rem, 1fr));
		gap: 0.75rem;
		margin: 0.75rem 0 1.25rem;
	}
	:global(.cartao) {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		padding: 0.9rem 1rem;
		border: 1px solid rgba(127, 127, 127, 0.3);
		border-radius: 0.75rem;
		background: rgba(127, 127, 127, 0.05);
		color: inherit;
		text-decoration: none;
	}
	:global(a.cartao:hover),
	:global(a.cartao:focus-visible) {
		border-color: #2563eb;
		background: rgba(37, 99, 235, 0.06);
	}
	:global(.cartao-titulo) {
		font-size: 0.85rem;
		font-weight: 600;
		opacity: 0.85;
	}
	:global(.cartao-numero) {
		font-size: 1.75rem;
		line-height: 2.1rem;
		font-weight: 700;
		font-variant-numeric: tabular-nums;
	}
	:global(.cartao-texto) {
		font-size: 0.875rem;
	}
	:global(.cartao .seta-baixo) {
		color: #15803d;
	}
	:global(.cartao .seta-cima) {
		color: #b91c1c;
	}
	:global([data-theme='dark'] .cartao .seta-baixo) {
		color: #4ade80;
	}
	:global([data-theme='dark'] .cartao .seta-cima) {
		color: #f87171;
	}
	/* Uma conclusão em destaque, antes dos gráficos. */
	:global(.conclusao) {
		border-left: 4px solid #2563eb;
		background: rgba(37, 99, 235, 0.06);
		padding: 0.5rem 0.75rem;
		border-radius: 0.25rem;
		margin: 0.75rem 0;
	}
	/* Linhas de texto com uma largura que se lê bem. */
	:global(.conteudo article p),
	:global(.conteudo article li) {
		max-width: 75ch;
	}
	:global(.conteudo article h2) {
		margin-top: 2.25rem;
	}
</style>
