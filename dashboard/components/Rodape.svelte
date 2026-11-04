<!--
	O rodapé de todas as páginas: o texto da página (slot) e, por baixo, as fontes e o código.
-->
<footer class="rodape">
	<slot />
	<p>
		Dados: Direção-Geral de Energia e Geologia (preços dos postos), Comissão Europeia (Weekly Oil
		Bulletin) e FRED (cotações). ·
		<a href="/combustiveis-pt/concelho/">Preços por concelho</a> ·
		<a href="/combustiveis-pt/dados-abertos/">Dados abertos</a> ·
		<a href="https://github.com/JoseFerrao20/combustiveis-pt">Código no GitHub</a>
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
