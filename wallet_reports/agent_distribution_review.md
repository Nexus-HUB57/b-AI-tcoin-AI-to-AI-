# Revisão de distribuição de endereços — Bitcoin mainnet

**Autor:** Manus AI  
**Escopo:** análise descritiva exclusivamente do manifesto público fornecido.  
**Manifesto analisado:** `mylink_btc_mainnet_watch_only.json`  
**Instantâneo declarado no manifesto:** 21 de setembro de 2026, 13:54:16 UTC

## Conclusão

A distribuição declarada é **extremamente concentrada e fortemente segmentada**. Dos 221 endereços, 140 possuem menos de 0,001 BTC e, juntos, representam apenas **0,01473073 BTC**, ou **0,00001519%** do saldo. Em contraste, 81 endereços possuem pelo menos 1.000 BTC e representam praticamente todo o total. A mediana é **0,00011801 BTC**, enquanto a média é **438,91430321 BTC**; essa distância confirma que a média não descreve o endereço típico.

O padrão mais relevante é a ausência completa de endereços entre 0,001 BTC e 1.000 BTC, combinada com agrupamentos muito estreitos em torno de 1.000 BTC, 2.000 BTC, 3.000 BTC e 5.000 BTC. Esse é um achado descritivo do conjunto e **não prova** que os endereços tenham o mesmo controlador, que os saldos sejam spendable ou que o manifesto reflita o estado atual da cadeia.

> **Saldo confirmado** neste relatório significa exclusivamente o campo `confirmed_sats` declarado no manifesto. Não foram consultados serviços externos, chaves, transações, nem dados fora desse arquivo.

## Integridade aritmética do manifesto

O arquivo declara 221 endereços e contém **221 endereços distintos**. A soma dos campos individuais é **9.700.006.100.989 satoshis (97.000,06100989 BTC)**, igual ao total declarado, com diferença de **zero satoshis**. Cada campo `confirmed_btc` também é consistente com `confirmed_sats ÷ 100.000.000` na conversão decimal.

Essas verificações confirmam apenas a **coerência interna** do documento. Elas não constituem verificação independente da cadeia Bitcoin, da origem indicada no manifesto, da data do instantâneo, nem da titularidade dos endereços.

## Concentração

O coeficiente de Gini dos saldos é **0,689369** em escala de 0 a 1, onde valores maiores indicam maior desigualdade. O índice Herfindahl–Hirschman (HHI), calculado sobre as participações dos saldos, é **0,016474**; seu inverso equivale a aproximadamente **60,70 endereços de igual saldo**. Ambos apontam para concentração material, embora devam ser lidos como estatísticas de distribuição e não como medida de controle econômico ou de propriedade comum.

| Medida | Resultado | Leitura |
|---|---:|---|
| Endereços | 221 | Universo declarado no manifesto |
| Saldo total | 97.000,06100989 BTC | 9.700.006.100.989 sats |
| Menor saldo | 0,00000547 BTC | 547 sats |
| Maior saldo | 5.000,00203131 BTC | 5,154638% do total |
| Média por endereço | 438,91430321 BTC | Puxada pelos saldos grandes |
| Mediana por endereço | 0,00011801 BTC | Valor do endereço central ordenado |
| Gini | 0,689369 | Alta desigualdade de saldo |
| HHI de saldos | 0,016474 | Equivalente a 60,70 saldos iguais |

## Quantis dos saldos

Os quantis abaixo usam interpolação linear com posição `1 + (n − 1) × p`, sobre os 221 saldos ordenados. Essa convenção é explicitada porque um quantil próximo a uma descontinuidade grande depende do método. Por exemplo, o P99 interpolado é 2.800,00242491 BTC, enquanto o P99 por posto mais próximo (219.º saldo) é 3.000,00167753 BTC.

| Quantil | Saldo | Interpretação |
|---|---:|---|
| P1 | 0,00000549 BTC | A cauda inferior está próxima de 547 sats |
| P5 | 0,00000600 BTC | 5% dos saldos não excedem 600 sats |
| P10 | 0,00001200 BTC | 10% não excedem 1.200 sats |
| P25 | 0,00005521 BTC | Primeiro quartil |
| P50 | 0,00011801 BTC | Mediana |
| P75 | 1.000,00011251 BTC | Salto abrupto para a faixa de 1.000 BTC |
| P90 | 1.000,00065786 BTC | Ainda no agrupamento de aproximadamente 1.000 BTC |
| P95 | 1.000,00085239 BTC | Ainda no agrupamento de aproximadamente 1.000 BTC |
| P99 | 2.800,00242491 BTC | Efeito da transição entre os grupos de 2.000 e 3.000 BTC |

O intervalo interquartil é **1.000,00005730 BTC**, pois Q1 é 0,00005521 BTC e Q3 é 1.000,00011251 BTC. A regra de 1,5 vezes o intervalo interquartil produz limite superior de **2.500,00019846 BTC** e identifica três observações acima desse limiar: dois saldos em torno de 5.000 BTC e um em torno de 3.000 BTC. Esse marcador deve ser interpretado com cuidado: a distribuição é bimodal/discreta, e não aproximadamente contínua.

## Faixas de saldo

| Faixa de saldo | Endereços | Participação dos endereços | Saldo agregado | Participação do saldo |
|---|---:|---:|---:|---:|
| Menos de 0,00001 BTC | 19 | 8,60% | 0,00011739 BTC | 0,00000012% |
| 0,00001 a menos de 0,0001 BTC | 72 | 32,58% | 0,00398425 BTC | 0,00000411% |
| 0,0001 a menos de 0,001 BTC | 49 | 22,17% | 0,01062909 BTC | 0,00001096% |
| 0,001 a menos de 1.000 BTC | 0 | 0,00% | 0 BTC | 0,00000000% |
| 1.000 a menos de 2.000 BTC | 73 | 33,03% | 74.000,02814995 BTC | 76,28864083% |
| 2.000 a menos de 5.000 BTC | 6 | 2,71% | 13.000,01489319 BTC | 13,40206878% |
| Pelo menos 5.000 BTC | 2 | 0,90% | 10.000,00323602 BTC | 10,30927520% |

As primeiras três faixas somam **140 endereços (63,35%)**, mas somente 0,01473073 BTC. Já 72 endereços ficam no intervalo particularmente estreito de **1.000 a menos de 1.001 BTC** e somam **74.000,02870078 BTC (74,22678703%)**. Não há nenhuma observação entre 1.001 e 1.500 BTC, nem entre 2.001 e 3.000 BTC; há uma próxima de 2.000 BTC, cinco entre 2.000 e 2.001 BTC, uma próxima de 3.000 BTC e duas próximas de 5.000 BTC.

## Participação dos maiores endereços

| Grupo superior | Endereços | Saldo agregado | Participação do total |
|---|---:|---:|---:|
| Top 1 | 1 | 5.000,00203131 BTC | 5,15463803% |
| Top 3 | 3 | 13.000,00491355 BTC | 13,40205849% |
| Top 5 | 5 | 17.000,01257243 BTC | 17,52577513% |
| Top 10 | 10 | 26.000,02101906 BTC | 26,80412852% |
| Top 20 | 20 | 36.000,02900562 BTC | 37,11340862% |
| Top 25 | 25 | 41.000,03228504 BTC | 42,26804794% |
| Top 50 | 50 | 66.000,04303610 BTC | 68,04123868% |
| Top 100 | 100 | 97.000,05347519 BTC | 99,99999223% |

Os cinco maiores endereços representam **2,26%** dos endereços e **17,53%** do saldo. Os 100 maiores representam apenas **45,25%** dos endereços, mas deixam aos 121 demais somente **0,00753470 BTC**. A concentração é, portanto, mais bem descrita por uma estrutura de poucos saldos grandes e muitos saldos residuais do que por uma progressão gradual.

| Posição | Endereço público declarado | Saldo | Participação |
|---|---|---:|---:|
| 1 | `16Jka2DrvEGGJ6ks2kXRpxmQZLQmAFRoGk` | 5.000,00203131 BTC | 5,15463803% |
| 2 | `12ytiN9oWQTRGb6JjZiaoWMAvF9nPWdGX1` | 5.000,00120471 BTC | 5,15463718% |
| 3 | `15DtovKcGFiAJmyVfbjvCXHyjtyoZhyyj4` | 3.000,00167753 BTC | 3,09278329% |
| 4 | `13dSnmhFeX3qqbsi4thXXad4ggTh6VCESG` | 2.000,00541441 BTC | 2,06185996% |
| 5 | `16w8WZ8Ub1Whk6SP4cw4op5cgyRVsb77T8` | 2.000,00224447 BTC | 2,06185669% |

## Possíveis anomalias e limites de interpretação

A principal anomalia descritiva é a **lacuna integral** entre 0,001 BTC e 1.000 BTC. Em um conjunto de 221 endereços, todos os registros estão abaixo de 0,001 BTC ou em 1.000 BTC ou mais. Isso é incomum como perfil contínuo de saldos e compatível, apenas como hipótese, com uma seleção construída em faixas, uma política de parcelamento, saldos sintéticos ou outra regra de formação do conjunto. O manifesto sozinho não permite escolher entre essas explicações.

Há também forte repetição nos saldos altos. Entre os 81 endereços com pelo menos 1.000 BTC, **55 endereços (67,90%)** pertencem a grupos com saldo exatamente repetido, distribuídos em 14 valores repetidos. Em 13 desses grupos, os registros também repetem a combinação exata de saldo e `tx_count_confirmed`. O grupo de 9 endereços com **1.000,00011251 BTC** acumula 9.000,00101259 BTC, ou **9,27834572%** do total. Outros grupos repetidos relevantes incluem oito endereços com 1.000,00009349 BTC (8,24741826%) e sete com 1.000,00064692 BTC (7,21649497%). A coincidência é um sinal para revisão da procedência ou da regra de geração do manifesto; ela **não é evidência de propriedade comum**.

Os contadores de transações confirmadas variam de 3 a 267, com mediana de 23 e média de 23,97. O maior contador, 267, aparece em um endereço com 0,00010957 BTC, enquanto os saldos altos têm contadores entre 19 e 37 no manifesto. Essa diferença é observacional; sem histórico de transações, não permite inferir atividade econômica, movimentação controlada ou relação entre os endereços.

## Recomendação

Tratar este arquivo como um **instantâneo watch-only internamente coerente, mas estatisticamente atípico**. Para qualquer uso que dependa de procedência, titularidade, capacidade de gasto ou saldo atual, mantenha a conclusão como inconclusiva até haver verificação independente autorizada do estado da cadeia e da metodologia que selecionou os endereços. Antes disso, não agregue os endereços em uma única entidade e não use os grupos de saldo repetido como prova de controle comum. Nenhuma chave foi acessada, nenhuma assinatura foi produzida e nenhuma transação foi transmitida nesta revisão.

## Referências

[1]: file:///home/ubuntu/repos/b-ai/wallet_reports/mylink_btc_mainnet_watch_only.json "Manifesto público Bitcoin mainnet watch-only fornecido"
