# Fine Tune Model for Function Qwen Chart

Este proyecto tiene como objetivo entrenar un modelo de lenguaje para generar gráficos a partir de descripciones en lenguaje natural. El modelo se basa en la arquitectura Qwen y se ha adaptado para manejar tareas específicas relacionadas con la generación de gráficos.

## Commandos

Para la generacion de los datos sinteticos, se puede ejecutar el siguiente comando:

```bash
modal run generate_dataset.py
```

Para inciar el entrenamiento del modelo, se puede ejecutar el siguiente comando:

```bash
modal run --detach trainer.py
```

Construir modelo con ollama

```bash
ollama create <ModelFile>
```

![alt text](image.png)
