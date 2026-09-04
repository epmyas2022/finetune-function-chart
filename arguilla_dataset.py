import json
import argilla as rg

from datasets import load_dataset

client = rg.Argilla(
    api_url="http://localhost:6900",
    api_key="admin.apikey",
)


# Convertir a Argilla
dataset = rg.Dataset(
    name="fine_tune_charts",
    workspace="admin",
    client=client,
    settings=rg.Settings(
        fields=[
            rg.TextField(
                name="query",
                title="Query",
                use_markdown=True,
            ),
            rg.TextField(
                name="dataset_context",
                title="Dataset Context",
                use_markdown=True,
            ),
            rg.TextField(
                name="tools",
                title="Tools",
                use_markdown=True,
            ),
            rg.TextField(
                name="answers",
                title="Answers",
                use_markdown=True,
            ),
        ],
        questions=[
            rg.RatingQuestion(
                name="quality",
                title="¿Qué tan bueno es este ejemplo para el fine-tuning?",
                values=[1, 2, 3, 4, 5],
                required=True,
            ),
            rg.LabelQuestion(
                name="category",
                title="¿Qué herramienta se necesita para resolver la solicitud?",
                labels={
                    "CREATE_CHART": "Crear gráfico",
                    "UPDATE_CHART": "Actualizar gráfico",
                    "NO_TOOL_NEEDED": "Ninguna herramienta",
                },
                required=True,
            ),
        ],
    ),
)


# Publicar
dataset.create()


with open("dataset.jsonl", "r", encoding="utf-8") as f:
    records = []

    for line in f:
        data = json.loads(line)

        records.append(
            rg.Record(
                fields={
                    "query": data["query"],
                    "tools": json.dumps(data["tools"], ensure_ascii=False, indent=2),
                    "dataset_context": json.dumps(data["dataset_context"], ensure_ascii=False, indent=2),
                    "answers": json.dumps(data["answers"], ensure_ascii=False),
                }
            )
        )

dataset.records.log(records)
