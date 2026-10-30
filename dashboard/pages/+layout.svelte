<script>
	import '@evidence-dev/tailwind/fonts.css';
	import '../app.css';
	import { EvidenceDefaultLayout } from '@evidence-dev/core-components';
	export let data;
</script>

<EvidenceDefaultLayout
	{data}
	title="Combustíveis em Portugal"
	homePageName="Início"
	githubRepo="https://github.com/JoseFerrao20/combustiveis-pt"
	hideTOC={true}
	hideBreadcrumbs={true}
	neverShowQueries={true}
>
	<slot slot="content" />
</EvidenceDefaultLayout>

<style>
	/* A barra lateral do Evidence põe cada palavra com maiúscula ("Portugal E A Europa"),
	   com a classe capitalize do Tailwind: os títulos das páginas já vêm escritos como devem
	   aparecer. O painel não usa os outros componentes com essa classe (mapas). */
	:global(.capitalize) {
		text-transform: none;
	}
	/* A previsão de segunda-feira, no topo da página inicial. */
	:global(.previsao-segunda) {
		border-left: 4px solid #d97706;
		background: rgba(217, 119, 6, 0.08);
		padding: 0.5rem 0.75rem;
		border-radius: 0.25rem;
		margin: 0.75rem 0;
	}
</style>
