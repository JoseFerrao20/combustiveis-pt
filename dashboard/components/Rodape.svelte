<!--
	O rodapé de todas as páginas: o texto da página (slot) e, por baixo, as fontes e o código.
-->
<script>
	export let evidence = false;
</script>

<footer class="rodape">
	<slot />
	<p>
		Dados: Direção-Geral de Energia e Geologia (preços dos postos), Comissão Europeia (Weekly Oil
		Bulletin) e FRED (cotações). ·
		<!-- rel="external": não é uma página do Evidence (o build do Evidence não a procura). -->
		<a href="/combustiveis-pt/concelho/" rel="external">Preços por concelho</a> ·
		<a href="https://github.com/JoseFerrao20/combustiveis-pt">Código no GitHub</a>
		{#if evidence}· <a href="https://www.evidence.dev">Feito com o Evidence</a>{/if}
	</p>
</footer>

<style>
	.rodape {
		margin-top: 2.5rem;
		padding: 1rem 0 2rem;
		border-top: 1px solid rgba(127, 127, 127, 0.25);
		font-size: 0.85rem;
		opacity: 0.85;
	}
	.rodape :global(p + p) {
		margin-top: 0.5rem;
	}
	.rodape a {
		color: inherit;
	}
</style>
