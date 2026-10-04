---
name: criar-graficos-matplotlib
description: Cria gráficos (linhas, colunas, pizza, heatmap) com matplotlib executando o código na tool run_python. Use quando o aluno pedir para visualizar dados, comparar valores, ver distribuição/proporção ou ver uma matriz/correlação.
---

1. Identifique o tipo de gráfico mais adequado à pergunta do aluno:
   - **linhas** — evolução de uma ou mais séries ao longo de um eixo contínuo (tempo, épocas de treino, etc.).
   - **colunas (barras)** — comparação de valores entre categorias discretas.
   - **pizza** — proporção de partes em um todo (poucas categorias, idealmente até 5-6).
   - **heatmap** — matriz de valores (ex.: correlação entre variáveis, matriz de confusão).
2. Monte o código Python do exemplo, sempre com `matplotlib.pyplot` (`import matplotlib.pyplot as plt`; o sandbox já configura o backend `Agg`, não é preciso fazer isso nem chamar `plt.show()`).
3. Inclua título (`plt.title`), rótulos dos eixos (`plt.xlabel`/`plt.ylabel`) e, quando houver mais de uma série, legenda (`plt.legend()`). Para heatmaps, inclua uma barra de cores (`plt.colorbar()`).
4. Envie o código para a tool `run_python`. O sandbox captura automaticamente qualquer figura matplotlib aberta ao final da execução — não é preciso salvar nem retornar a imagem manualmente.
5. Comente o resultado: o que o gráfico mostra, e se algum valor chama atenção (tendência, outlier, categoria dominante, correlação forte, etc.).

## Exemplos por tipo de gráfico

### Linhas — evolução de uma métrica

```python
import matplotlib.pyplot as plt

epocas = list(range(1, 11))
perda_treino = [0.9, 0.7, 0.55, 0.45, 0.38, 0.33, 0.29, 0.26, 0.24, 0.22]
perda_validacao = [0.95, 0.78, 0.65, 0.58, 0.54, 0.52, 0.51, 0.52, 0.54, 0.57]

plt.figure(figsize=(6, 4))
plt.plot(epocas, perda_treino, marker="o", label="Treino")
plt.plot(epocas, perda_validacao, marker="o", label="Validação")
plt.title("Perda por época")
plt.xlabel("Época")
plt.ylabel("Perda")
plt.legend()
```

Bom para mostrar overfitting: a perda de validação para de cair e volta a subir enquanto a de treino continua caindo.

### Colunas — comparação entre categorias

```python
import matplotlib.pyplot as plt

modelos = ["Regressão Logística", "Árvore de Decisão", "Random Forest", "SVM"]
acuracia = [0.82, 0.78, 0.89, 0.85]

plt.figure(figsize=(6, 4))
plt.bar(modelos, acuracia, color="steelblue")
plt.title("Acurácia por modelo")
plt.ylabel("Acurácia")
plt.ylim(0, 1)
plt.xticks(rotation=20)
```

### Pizza — proporção de categorias

```python
import matplotlib.pyplot as plt

classes = ["Spam", "Não spam"]
quantidades = [120, 380]

plt.figure(figsize=(5, 5))
plt.pie(quantidades, labels=classes, autopct="%1.1f%%", startangle=90)
plt.title("Distribuição das classes no dataset")
```

Use pizza só com poucas categorias; com muitas, prefira colunas.

### Heatmap — matriz de correlação

```python
import matplotlib.pyplot as plt
import numpy as np

variaveis = ["idade", "renda", "anos_estudo", "score_credito"]
matriz_correlacao = np.array(
    [
        [1.00, 0.35, 0.20, 0.41],
        [0.35, 1.00, 0.55, 0.62],
        [0.20, 0.55, 1.00, 0.48],
        [0.41, 0.62, 0.48, 1.00],
    ]
)

plt.figure(figsize=(5, 4))
plt.imshow(matriz_correlacao, cmap="coolwarm", vmin=-1, vmax=1)
plt.xticks(range(len(variaveis)), variaveis, rotation=45, ha="right")
plt.yticks(range(len(variaveis)), variaveis)
plt.colorbar(label="Correlação")
plt.title("Matriz de correlação")
```

Para uma matriz de confusão, o mesmo padrão funciona: troque os rótulos pelas classes e os valores pelas contagens de acertos/erros.
