import json
import modal

# ==============================================================================
# CONFIGURATION
# ==============================================================================

APP_NAME = "function-qwen-charts"
DATASET_FILE = "data/dataset.jsonl"
MODEL_NAME = "unsloth/Qwen2.5-1.5B-Instruct"

# Hyperparameters
MAX_SEQ_LENGTH = 4096
LORA_R = 8
LORA_ALPHA = 32
BATCH_SIZE = 16
GRAD_ACCUM_STEPS = 2
EPOCHS = 3
LR = 5e-6

# Volumes and Paths
VOLUME_NAME = "weights-function-qwen"
WEIGHTS_MOUNT_PATH = "/weights-function-qwen"
OUTPUT_DIR = f"{WEIGHTS_MOUNT_PATH}/function_qwen_chart"
MERGED_DIR = f"{WEIGHTS_MOUNT_PATH}/function_qwen_chart-merge"
GGUF_DIR = f"{WEIGHTS_MOUNT_PATH}/function_qwen_chart_q4_k_m"

# Canonical schema definition for strict tool calls

_FILTERS_FIELD = {
    "type": "array",
    "description": "Filtros sobre los datos antes de graficar. Cada filtro es un objeto {field, operator, value}. Se pueden combinar múltiples filtros. IMPORTANTE: NUNCA uses filters para extraer el límite de elementos (ej. '5 productos' o 'top 5'). El límite de elementos numérico SIEMPRE va en la propiedad limit o number_of_items, NUNCA en filters.",
    "items": {
        "type": "object",
        "properties": {
            "field": {
                "type": "string",
                "description": "Campo o dimensión por el que se filtra (ej. categoria, region, año).",
            },
            "operator": {
                "type": "string",
                "enum": ["eq", "neq", "gt", "gte", "lt", "lte", "contains"],
                "description": "Operador de comparación. eq (igual), neq (diferente), gt (mayor que), gte (mayor o igual), lt (menor que), lte (menor o igual), contains (contiene, para búsqueda parcial de texto).",
            },
            "value": {
                "description": "Valor de comparación. Puede ser texto, número o booleano según el campo."
            },
        },
        "required": ["field", "operator", "value"],
    },
}

CANONICAL_TOOLS = {
    "create_chart": {
        "description": "Crea un nuevo gráfico a partir de los datos.",
        "parameters": {
            "type": "object",
            "properties": {
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "line", "pie", "scatter"],
                    "description": "Tipo de gráfico. Obligatorio. bar (barras), line (líneas), pie (circular o pastel. NUNCA uses 'pastel', usa 'pie'), scatter (dispersión).",
                },
                "dimension": {
                    "type": "string",
                    "description": "El nombre exacto de la dimensión. No agregues sufijos como '_id'.",
                },
                "metric": {
                    "type": "string",
                    "description": "Métrica del eje Y (o eje principal). Para scatter, es la variable del eje X. Nombre exacto del campo numérico. Puede llevar guiones bajos.",
                },
                "metric_y": {
                    "type": "string",
                    "description": "Segunda variable cuantitativa para el eje Y. Obligatorio en gráficos de dispersión (scatter). Debe ser un campo numérico distinto a metric.",
                },
                "aggregation": {
                    "type": "string",
                    "enum": ["sum", "average", "count"],
                    "description": "Agregación matemática. sum (suma), average (promedio), count (cantidad).",
                },
                "sort_direction": {
                    "type": "string",
                    "enum": ["asc", "desc"],
                    "description": "Dirección de ordenamiento. asc (ascendente) = 'de menor a mayor', 'de menos a más', 'los menos vendidos', 'ascendente'. desc (descendente) = 'de mayor a menor', 'de más a menos', 'los más vendidos', 'descendente'. PRESTA ATENCIÓN: Si el usuario pide 'menos a más' o 'menos vendidos', SIEMPRE usa 'asc'. Si pide 'más a menos' o 'más vendidos', usa 'desc'.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Número máximo de elementos a mostrar (ej. el número 5 en 'los 5 más vendidos').",
                },
                "colors": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Lista de colores EN INGLÉS para el gráfico (ej. ['red'], ['red', 'blue']). SIEMPRE traduce al inglés.",
                },
                "filters": _FILTERS_FIELD,
            },
            "required": ["chart_type", "dimension", "metric", "aggregation"],
        },
    },
    "update_chart": {
        "description": "Actualiza propiedades del gráfico actualmente mostrado.",
        "parameters": {
            "type": "object",
            "properties": {
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "line", "pie", "scatter"],
                    "description": "Nuevo tipo de gráfico. bar (barras), line (líneas), pie (circular o pastel. NUNCA uses 'pastel', usa 'pie'), scatter (dispersión).",
                },
                "metric": {
                    "type": "string",
                    "description": "Nueva métrica numérica a visualizar (por ejemplo, ingresos, venta_total, cantidad). PRESTA ATENCIÓN: Si el usuario dice 'cambia la métrica por cantidad', debes establecer 'metric' en 'cantidad', NO asumas que se refiere a la agregación 'count'.",
                },
                "metric_y": {
                    "type": "string",
                    "description": "Segunda métrica numérica, para el eje Y. OBLIGATORIO si cambias el chart_type a scatter. Debe ser el nombre exacto del campo numérico, distinto a metric.",
                },
                "aggregation": {
                    "type": "string",
                    "enum": ["sum", "average", "count"],
                    "description": "Nueva agregación matemática. sum (suma), average (promedio), count (cantidad).",
                },
                "sort_direction": {
                    "type": "string",
                    "enum": ["asc", "desc"],
                    "description": "Nuevo ordenamiento. asc (ascendente) = 'de menor a mayor', 'de menos a más', 'los menos vendidos', 'ascendente'. desc (descendente) = 'de mayor a menor', 'de más a menos', 'los más vendidos', 'descendente'. PRESTA ATENCIÓN: Si el usuario pide 'menos a más' o 'menos vendidos', SIEMPRE usa 'asc'. Si pide 'más a menos' o 'más vendidos', usa 'desc'.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Nuevo límite de elementos a mostrar (ej. el número 4 en 'solo 4 productos' o 'los 4 más vendidos').",
                },
                "colors": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Nueva lista de colores EN INGLÉS para el gráfico. SIEMPRE traduce al inglés.",
                },
                "show_grid": {
                    "type": "boolean",
                    "description": "Si se debe mostrar la cuadrícula.",
                },
                "title": {"type": "string", "description": "Nuevo título del gráfico."},
                "filters": _FILTERS_FIELD,
            },
        },
    },
}

# ============================================================
# DATASET CONTEXTS
#
# Must mirror the DATASET_CONTEXTS defined in generate_data.py.
# Each JSONL row carries its schema in the dataset_context field.
# format_example reads it and injects the correct system message
# so the model always trains with the exact context it will see
# at inference time.
# ============================================================

DATASET_CONTEXTS = [
    {
        "name": "ventas_retail",
        "fields": [
            "id",
            "fecha",
            "cliente",
            "producto",
            "cantidad",
            "precio_venta",
            "categoria",
            "region",
        ],
    },
    {
        "name": "ecommerce",
        "fields": [
            "order_id",
            "fecha_pedido",
            "usuario",
            "sku",
            "nombre_producto",
            "unidades",
            "precio_unitario",
            "descuento",
            "total",
            "canal",
            "estado_pedido",
        ],
    },
    {
        "name": "inventario",
        "fields": [
            "id",
            "producto",
            "categoria",
            "stock_actual",
            "stock_minimo",
            "costo_unitario",
            "proveedor",
            "bodega",
        ],
    },
    {
        "name": "rrhh",
        "fields": [
            "empleado_id",
            "nombre",
            "departamento",
            "cargo",
            "salario",
            "fecha_ingreso",
            "sucursal",
            "activo",
        ],
    },
    {
        "name": "marketing",
        "fields": [
            "campania_id",
            "nombre_campania",
            "canal",
            "fecha_inicio",
            "fecha_fin",
            "inversion",
            "clicks",
            "conversiones",
            "roi",
            "segmento",
        ],
    },
    {
        "name": "finanzas",
        "fields": [
            "fecha",
            "cuenta",
            "tipo_movimiento",
            "monto",
            "moneda",
            "categoria",
            "sucursal",
            "aprobado",
        ],
    },
    {
        "name": "logistica",
        "fields": [
            "envio_id",
            "fecha_envio",
            "cliente",
            "destino",
            "peso_kg",
            "costo_envio",
            "transportista",
            "estado",
            "dias_entrega",
        ],
    },
    {
        "name": "pos_restaurante",
        "fields": [
            "ticket_id",
            "fecha",
            "mesa",
            "producto",
            "categoria",
            "cantidad",
            "precio",
            "mesero",
            "turno",
        ],
    },
]

# Fallback schema used when a row has no dataset_context field (e.g. legacy data).
_FALLBACK_SCHEMA = DATASET_CONTEXTS[0]


def get_dataset_context_instruction(schema: dict) -> str:
    """Builds the dataset context system message from a schema dict."""
    fields_str = ", ".join(schema["fields"])
    return (
        f"You must use the following dataset context: "
        f"The available fields are: {fields_str}."
    )


# ==============================================================================
# TRAINING LOGIC
# ==============================================================================


def configure_lora(model, FastLanguageModel):
    """Wraps the model with PEFT/LoRA configuration."""
    print("[2/7] Configurando LoRA...")
    peft_model = FastLanguageModel.get_peft_model(
        model,
        r=LORA_R,
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        lora_alpha=LORA_ALPHA,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=3407,
    )
    print("[OK] LoRA configurado")
    return peft_model


def prepare_datasets(raw_data, tokenizer):
    """Converts raw json records into tokenized HuggingFace Datasets."""
    from datasets import Dataset

    print("[4/7] Formateando dataset...")

    formatted_data = [format_example(line, tokenizer) for line in raw_data]
    dataset = Dataset.from_list(formatted_data)

    # Filter sequences exceeding maximum length
    def filter_length(example):
        return len(example["input_ids"]) < MAX_SEQ_LENGTH - 50

    original_size = len(dataset)
    dataset = dataset.filter(filter_length)
    print(f"[OK] Dataset filtrado: {len(dataset)}/{original_size} ejemplos viables.")

    # Split Train/Test
    dataset = dataset.train_test_split(test_size=0.1, seed=3407)
    train_dataset = dataset["train"]
    eval_dataset = dataset["test"]

    print("[OK] Dataset preparado")

    # Critical debug check
    print("\n" + "=" * 80)
    print("EJEMPLO REAL QUE SE VA A ENTRENAR")
    print("=" * 80)
    print(train_dataset[0]["text"])
    print("=" * 80 + "\n")

    # Drop intermediate text column
    train_dataset = train_dataset.remove_columns(["text"])
    eval_dataset = eval_dataset.remove_columns(["text"])

    return train_dataset, eval_dataset


app = modal.App(APP_NAME)

volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .add_local_file(DATASET_FILE, f"/root/{DATASET_FILE}", copy=True)
    .pip_install("transformers", "datasets", "trl", "accelerate", "peft")
    .pip_install(
        "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git",
        "unsloth_zoo @ git+https://github.com/unslothai/unsloth-zoo.git",
    )
)


def load_raw_dataset(filepath: str) -> list[dict]:
    """Loads JSONL dataset from the given path."""
    raw_data = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                raw_data.append(json.loads(line))
    return raw_data


def build_tool_schema(raw_tools: list[dict]) -> list[dict]:
    """Builds the canonical OpenAI-style tools array for prompt generation."""
    tools = []
    if not raw_tools:
        raw_tools = [{"name": "create_chart"}, {"name": "update_chart"}]

    for tool in raw_tools:
        name = tool["name"]
        canonical = CANONICAL_TOOLS.get(name, {})
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": canonical.get(
                        "description", tool.get("description", "")
                    ),
                    "parameters": canonical.get(
                        "parameters", tool.get("parameters", {})
                    ),
                },
            }
        )
    return tools


def format_example(line: dict, tokenizer) -> dict:
    """
    Parses a dataset line (supporting both legacy 'query/answers' and modern 'messages' formats)
    and formats it through the tokenizer's chat template, applying label masking.
    """
    query = ""
    tool_name = ""
    arguments = {}
    raw_tools = []

    # Parse depending on the underlying structure of the row

    query = line.get("query", "").strip()
    raw_tools = line.get("tools", [])
    answers = line.get("answers", [])

    if answers:
        answer = answers[0]
        tool_name = answer.get("name", "")
        arguments = answer.get("arguments", answer.get("parameters", {}))

    # Build the prompt array
    tools = build_tool_schema(raw_tools)

    # Resolve the schema for this specific row.
    # Each row carries its own dataset_context (set at generation time).
    # Falls back to the first schema for rows generated before this feature.
    raw_schema = line.get("dataset_context")
    schema = raw_schema if isinstance(raw_schema, dict) else _FALLBACK_SCHEMA
    system_message = {
        "role": "system",
        "content": get_dataset_context_instruction(schema),
    }

    # 1) Generate the prompt text (up to the assistant response)
    prompt_text = tokenizer.apply_chat_template(
        [system_message, {"role": "user", "content": query}],
        tools=tools,
        add_generation_prompt=True,
        tokenize=False,
    )

    # 2) Build full conversation trace
    assistant_format = {"role": "assistant"}
    if tool_name:
        assistant_format["tool_calls"] = [
            {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": arguments,
                },
            }
        ]
    else:
        # Fallback for NO TOOL
        content = (
            "Los gráficos son representaciones visuales de datos. ¿En qué te ayudo?"
        )
        if "messages" in line:
            msg = next((m for m in line["messages"] if m["role"] == "assistant"), {})
            content = msg.get("content", content)
        assistant_format["content"] = content

    full_text = tokenizer.apply_chat_template(
        [system_message, {"role": "user", "content": query}, assistant_format],
        tools=tools,
        add_generation_prompt=False,
        tokenize=False,
    )

    # 3) Tokenize and apply label masking for training
    prompt_ids = tokenizer.encode(prompt_text, add_special_tokens=False)
    full_ids = tokenizer.encode(full_text, add_special_tokens=False)

    prompt_len = len(prompt_ids)
    labels = [-100] * prompt_len + full_ids[prompt_len:]

    return {
        "input_ids": full_ids,
        "labels": labels,
        "attention_mask": [1] * len(full_ids),
        "text": full_text,  # Retained for inspection
    }


@app.function(
    image=image,
    gpu="A100",
    timeout=60 * 60 * 24,
    volumes={WEIGHTS_MOUNT_PATH: volume},
)
def run_training():
    """Main training orchestrator running inside Modal container."""
    from unsloth import FastLanguageModel, UnslothTrainer, UnslothTrainingArguments
    from transformers import DataCollatorForSeq2Seq
    import torch

    # Optimize matmuls for Ampere architectures
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True

    # 1. Load Model
    print("[1/7] Cargando Modelo Base...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL_NAME,
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=None,
        load_in_4bit=True,
    )
    print("[OK] Modelo cargado")

    # 2. Setup LoRA
    model = configure_lora(model, FastLanguageModel)

    # 3. Load Raw Data
    print("[3/7] Cargando JSONL de disco...")
    raw_data = load_raw_dataset(f"/root/{DATASET_FILE}")
    print(f"[OK] Ejemplos en disco: {len(raw_data)}")

    # 4. Tokenize & Format
    train_dataset, eval_dataset = prepare_datasets(raw_data, tokenizer)

    # 5. Setup Trainer
    print("[5/7] Configurando SFTTrainer...")
    collator = DataCollatorForSeq2Seq(
        tokenizer=tokenizer,
        padding=True,
        pad_to_multiple_of=8,
        label_pad_token_id=-100,
    )

    trainer = UnslothTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        max_seq_length=MAX_SEQ_LENGTH,
        data_collator=collator,
        packing=False,
        args=UnslothTrainingArguments(
            output_dir="outputs_functiongemma",
            per_device_train_batch_size=BATCH_SIZE,
            per_device_eval_batch_size=6,
            gradient_accumulation_steps=GRAD_ACCUM_STEPS,
            num_train_epochs=EPOCHS,
            learning_rate=LR,
            embedding_learning_rate=1e-6,
            max_grad_norm=1.0,
            weight_decay=0.01,
            lr_scheduler_type="cosine",
            warmup_steps=25,
            fp16=False,
            bf16=True,
            logging_steps=1,
            eval_strategy="steps",
            eval_steps=500,
            save_strategy="no",
            report_to="none",
            seed=3407,
            dataloader_num_workers=4,
        ),
    )
    print("[OK] SFTTrainer configurado")

    # 6. Train
    print("[6/7] Entrenando modelo...")
    trainer.train()
    print("[OK] Entrenamiento finalizado con éxito.")

    # 7. Save & Export
    print("[7/7] Guardando y exportando artefactos...")
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)

    model.save_pretrained_merged(
        MERGED_DIR,
        tokenizer,
        save_method="merged_16bit",
    )
    print(f"[OK] Pesos base y combinados (merged) guardados en: {WEIGHTS_MOUNT_PATH}")

    print("[INFO] Empaquetando GGUF Q4_K_M...")
    model.save_pretrained_gguf(
        GGUF_DIR,
        tokenizer,
        quantization_method="q4_k_m",
    )
    print("[OK] Exportación a GGUF completada")

    print("\n==========================================")
    print("ENTRENAMIENTO COMPLETADO")
    print("==========================================\n")


@app.local_entrypoint()
def main():
    run_training.spawn()
