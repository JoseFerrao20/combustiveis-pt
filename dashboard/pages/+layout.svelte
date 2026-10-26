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
>
	<slot slot="content" />
</EvidenceDefaultLayout>
