# Concorrência e preço nos postos de Portugal continental

- **Data:** 2026-10-28
- **Dados:** a fotografia da DGEG de 28/10/2026 (preços atualizados nos últimos 30 dias)
- **Postos:** 3032 postos com coordenadas, sem os de autoestrada nem os de hipermercado

## A pergunta

Um posto sem concorrentes por perto cobra mais?

## Como se calculou

- **Concorrentes:** para cada posto, contam-se os outros postos a menos de 2 e de 5 km em linha reta, com a fórmula de haversine (`int_station_neighbours`, no dbt). A estrada real fica mais longe do que a linha reta, por isso 5 km em linha reta são, na prática, uns minutos de carro.
- **Comparação com o concelho:** o preço de cada posto é comparado com a média do seu concelho, para não confundir concorrência com região. O interior é mais caro e também tem menos postos.
- **Postos que ficam de fora:** os de autoestrada (com concessão e preços próprios) e os de hipermercado. As marcas dos hiper e supermercados entram como grupo de marcas.

A distância mediana ao concorrente mais próximo é de 0,72 km. 198 postos não têm nenhum concorrente a 5 km; os distritos com mais postos nessa situação são Santarém (25), Beja (24) e Castelo Branco (19).

## O que se viu

| Concorrentes a 5 km | Gasolina 95: postos | Preço médio | Diferença para o concelho | Gasóleo: postos | Preço médio | Diferença para o concelho |
|---|---|---|---|---|---|---|
| 0 | 193 | 2,116 € | +1,8 cênt. | 189 | 2,280 € | +1,5 cênt. |
| 1 a 2 | 394 | 2,093 € | 0,0 | 385 | 2,258 € | −0,1 |
| 3 a 5 | 462 | 2,084 € | −0,1 | 444 | 2,251 € | 0,0 |
| 6 a 10 | 670 | 2,081 € | −0,2 | 641 | 2,251 € | −0,1 |
| 11 ou mais | 1252 | 2,079 € | −0,1 | 1155 | 2,252 € | −0,2 |

- **O efeito está no extremo:** os postos sem concorrentes a 5 km são 3,7 cêntimos mais caros na gasolina e 2,8 no gasóleo do que os que têm 11 ou mais. Mesmo face à média do próprio concelho, ficam 1,5 a 1,8 cêntimos acima.
- **A partir de um ou dois concorrentes,** a diferença para o concelho desaparece. Não é "quanto mais postos, mais barato": é ter ou não ter alternativa.

Por grupo de marcas, a diferença para a média do concelho (gasolina 95) é esta:

| Grupo | Com 0 a 2 concorrentes | Com 3 ou mais |
|---|---|---|
| Petrolíferas | +1,7 | +2,2 |
| Sem marca | +1,3 | −1,8 |
| Outras marcas | 0,0 | −2,6 |
| Hiper e supermercados | −8,8 | −8,0 |

- **Petrolíferas e hiper e supermercados:** o preço quase não depende da concorrência à volta. Parecem ter preços definidos para toda a rede.
- **Postos sem marca e outras marcas (independentes):** baixam o preço 3 a 4 cêntimos quando há concorrência perto, e não o baixam quando estão sozinhos. O gasóleo mostra o mesmo, com −3,4 e −3,8 cêntimos.

## Limitações

- **Um só dia:** com mais fotografias, dá para ver se o padrão se mantém e se os postos isolados demoram mais a baixar o preço.
- **O efeito estará subestimado:** um posto que seja o único do seu concelho fica sempre a 0 cêntimos da "média do concelho". Muitos postos isolados estão nesse caso.
- **Linha reta e só o número de concorrentes:** não entram a estrada nem o tráfego, nem a marca dos vizinhos (um Intermarché ao lado conta mais do que outro posto da mesma marca).
- **Uma associação, não uma causa:** os postos isolados podem ser diferentes de outras maneiras, como o volume de vendas ou a loja.

## No projeto

- **Coluna nova:** `int_station_neighbours` dá, por dia e posto, o número de concorrentes a 2 e a 5 km e a distância ao mais próximo. Tem um teste unitário com postos a 1 e a 4 km.
- **Painel:** a página "Postos em Portugal" tem uma secção "Concorrência" com estes números, para o combustível escolhido.
