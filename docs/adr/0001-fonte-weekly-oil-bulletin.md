# 0001. Fonte dos preços: o Weekly Oil Bulletin da Comissão Europeia

- **Estado:** aceite
- **Data:** 2026-10-26

## Contexto

A ideia inicial era usar os preços posto a posto da DGEG (precoscombustiveis.dgeg.gov.pt), para responder a "onde é mais barato abastecer". Mas:

- a DGEG não tem uma API pública documentada; o acesso completo aos dados é para "entidades protocoladas", e quem os mostra (agregadores, portais) tem protocolo ou faz scraping;
- um projeto em cima de um endpoint não documentado parte-se sem aviso, e não é claro que o uso seja permitido.

O [Weekly Oil Bulletin](https://energy.ec.europa.eu/data-and-analysis/weekly-oil-bulletin_en) da Comissão Europeia publica todas as semanas, desde 2005, os preços médios de cada país da UE, **com e sem impostos**, e o histórico do IVA, do imposto sobre os produtos petrolíferos (ISP) e dos outros impostos indiretos. A reprodução é autorizada com indicação da fonte.

## Decisão

Usar o ficheiro do histórico do Weekly Oil Bulletin (`Weekly_Oil_Bulletin_Prices_History_maticni_4web.xlsx`) como única fonte. Tem tudo num ficheiro: preços com e sem impostos, IVA, ISP e outros impostos, para os 27 países, a média da UE e a da zona euro.

O link do ficheiro muda quando a Comissão o substitui (leva um identificador), por isso a ingestão procura-o na página do boletim em cada execução.

## Consequências

- As perguntas passam a ser de análise, e não de "posto mais barato": quanto do preço é imposto, como evoluiu desde 2005, Portugal comparado com Espanha e com a UE, o efeito das mudanças do ISP.
- Os preços são médias nacionais semanais (ponderadas pelas vendas), não preços de um posto.
- O formato do ficheiro não está documentado: a leitura valida-o e falha com uma mensagem clara se mudar, e os testes usam uma amostra do ficheiro real.
- Os dados posto a posto da DGEG podem entrar mais tarde, se houver um acesso legítimo.
