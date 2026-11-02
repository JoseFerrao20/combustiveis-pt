---
title: Combustível mais barato
description: O preço de cada posto de combustível em Portugal, do mais barato para o mais caro, com um mapa e a opção de ver os mais baratos perto de si.
---

<!--
    A página inicial do site não é do Evidence: é a de dashboard/app/ (mais leve), que o build
    escreve por cima do index.html desta. Esta só existe para os links das páginas do Evidence
    ("Início", o título no topo), que mudam de página sem a carregar: sem ela, mostravam a página
    de boas-vindas do Evidence. Ao abrir, pede a página ao servidor.
-->

<script>
    onMount(() => {
        // Se o documento já foi carregado nesta morada, o servidor deu esta página e não a nova:
        // carregar outra vez não mudava nada (e repetia-se sem fim).
        const loaded = performance.getEntriesByType('navigation')[0]?.name;
        if (loaded && new URL(loaded).pathname === window.location.pathname) return;
        window.location.replace(window.location.href);
    });
</script>

```sql fotografia
select max(snapshot_date) as dia from combustiveis.postos
```

A abrir a página inicial, com os preços de <Value data={fotografia} column=dia fmt="dd/mm/yyyy" />. Se não abrir, atualize a página.
