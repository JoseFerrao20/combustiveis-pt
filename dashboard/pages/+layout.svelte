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
</style>
