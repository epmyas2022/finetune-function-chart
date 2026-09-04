import json

import modal

app = modal.App("generate-dataset")

NAME_VOLUME = "datasets"

VOLUME_MOUNT = f"/{NAME_VOLUME}"

volume = modal.Volume.from_name(NAME_VOLUME, create_if_missing=True)

image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.4.1-devel-ubuntu22.04",
        add_python="3.12",
    )
    .pip_install(
        "distilabel[vllm]==1.5.3", "vllm==0.6.2", "transformers==4.46.1", "accelerate"
    )
    .run_commands(
        'python -c \'import distilabel, vllm; print("distilabel", distilabel.__version__); print("vllm", vllm.__version__)\''
    )
)


# ============================================================
# TOOLS
# ============================================================


_FILTERS_FIELD = {
    "type": "array",
    "description": "Filtros sobre los datos antes de graficar. Cada filtro es un objeto {field, operator, value}. Se pueden combinar múltiples filtros. IMPORTANTE: NUNCA uses filters para extraer el límite de elementos (ej. '5 productos' o 'top 5'). El límite de elementos numérico SIEMPRE va en la propiedad limit o number_of_items, NUNCA en filters.",
    "items": {
        "type": "object",
            "properties": {
                "field": {
                    "type": "string",
                    "description": "Campo o dimensión por el que se filtra (ej. categoria, region, año)."
                },
                "operator": {
                    "type": "string",
                    "enum": ["eq", "neq", "gt", "gte", "lt", "lte", "contains"],
                    "description": "Operador de comparación. eq (igual), neq (diferente), gt (mayor que), gte (mayor o igual), lt (menor que), lte (menor o igual), contains (contiene, para búsqueda parcial de texto)."
                },
                "value": {
                    "description": "Valor de comparación. Puede ser texto, número o booleano según el campo."
                }
            },
            "required": ["field", "operator", "value"]
    }
}

CREATE_CHART = {
    "name": "create_chart",
    "parameters": {
        "type": "object",
            "properties": {
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "line", "pie", "scatter"],
                    "description": "Tipo de gráfico. Obligatorio. bar (barras), line (líneas), pie (circular o pastel. NUNCA uses 'pastel', usa 'pie'), scatter (dispersión)."
                },
                "dimension": {
                    "type": "string",
                    "description": "El nombre exacto de la dimensión. No agregues sufijos como '_id'."
                },
                "metric": {
                    "type": "string",
                    "description": "Métrica del eje Y (o eje principal). Para scatter, es la variable del eje X. Nombre exacto del campo numérico. Puede llevar guiones bajos."
                },
                "metric_y": {
                    "type": "string",
                    "description": "Segunda variable cuantitativa para el eje Y. Obligatorio en gráficos de dispersión (scatter). Debe ser un campo numérico distinto a metric."
                },
                "aggregation": {
                    "type": "string",
                    "enum": ["sum", "average", "count"],
                    "description": "Agregación matemática. sum (suma), average (promedio), count (cantidad)."
                },
                "sort_direction": {
                    "type": "string",
                    "enum": ["asc", "desc"],
                    "description": "Dirección de ordenamiento. asc (ascendente) = 'de menor a mayor', 'de menos a más', 'los menos vendidos', 'ascendente'. desc (descendente) = 'de mayor a menor', 'de más a menos', 'los más vendidos', 'descendente'. PRESTA ATENCIÓN: Si el usuario pide 'menos a más' o 'menos vendidos', SIEMPRE usa 'asc'. Si pide 'más a menos' o 'más vendidos', usa 'desc'."
                },
                "limit": {
                    "type": "integer",
                    "description": "Número máximo de elementos a mostrar (ej. el número 5 en 'los 5 más vendidos')."
                },
                "colors": {
                    "type": "array",
                    "items": { "type": "string" },
                    "description": "Lista de colores EN INGLÉS para el gráfico (ej. ['red'], ['red', 'blue']). SIEMPRE traduce al inglés."
                },
                "filters": _FILTERS_FIELD
            },
            "required": ["chart_type", "dimension", "metric", "aggregation"]

    }
}

UPDATE_CHART = {
    "name": "update_chart",
    "parameters": {
        "type": "object",
            "properties": {
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "line", "pie", "scatter"],
                    "description": "Nuevo tipo de gráfico. bar (barras), line (líneas), pie (circular o pastel. NUNCA uses 'pastel', usa 'pie'), scatter (dispersión)."
                },
                "dimension": {
                    "type": "string",
                    "description": "Nueva dimensión. No agregues sufijos como '_id'."
                },
                "metric": {
                    "type": "string",
                    "description": "Nueva métrica numérica a visualizar (por ejemplo, ingresos, venta_total, cantidad). PRESTA ATENCIÓN: Si el usuario dice 'cambia la métrica por cantidad', debes establecer 'metric' en 'cantidad', NO asumas que se refiere a la agregación 'count'."
                },
                "metric_y": {
                    "type": "string",
                    "description": "Segunda métrica numérica, para el eje Y. OBLIGATORIO si cambias el chart_type a scatter. Debe ser el nombre exacto del campo numérico, distinto a metric."
                },
                "aggregation": {
                    "type": "string",
                    "enum": ["sum", "average", "count"],
                    "description": "Nueva agregación matemática. sum (suma), average (promedio), count (cantidad)."
                },
                "sort_direction": {
                    "type": "string",
                    "enum": ["asc", "desc"],
                    "description": "Nuevo ordenamiento. asc (ascendente) = 'de menor a mayor', 'de menos a más', 'los menos vendidos', 'ascendente'. desc (descendente) = 'de mayor a menor', 'de más a menos', 'los más vendidos', 'descendente'. PRESTA ATENCIÓN: Si el usuario pide 'menos a más' o 'menos vendidos', SIEMPRE usa 'asc'. Si pide 'más a menos' o 'más vendidos', usa 'desc'."
                },
                "limit": {
                    "type": "integer",
                    "description": "Nuevo límite de elementos a mostrar (ej. el número 4 en 'solo 4 productos' o 'los 4 más vendidos')."
                },
                "colors": {
                    "type": "array",
                    "items": { "type": "string" },
                    "description": "Nueva lista de colores EN INGLÉS para el gráfico. SIEMPRE traduce al inglés."
                },
                "show_grid": {
                    "type": "boolean",
                    "description": "Si se debe mostrar la cuadrícula."
                },
                "title": {
                    "type": "string",
                    "description": "Nuevo título del gráfico."
                },
                "filters": _FILTERS_FIELD
            }

    }
}

TOOLS = [
    CREATE_CHART,
    UPDATE_CHART,
]

# ============================================================
# DATASET CONTEXTS
#
# Each schema classifies its fields so resolve_example() can
# substitute dimension/metric/metric_y in POSITIVE_EXAMPLES
# with real fields from the assigned dataset. This guarantees
# that every generated example is coherent with its context —
# the model never sees a metric that doesn't exist in the schema.
#
# Field type conventions:
#   dimensions  → categorical fields suitable as group-by axis
#   metrics     → numeric fields suitable as aggregatable values
#   temporal    → date/time fields suitable as time-series axis
# ============================================================

DATASET_CONTEXTS = [
    {
        "name": "ventas_retail",
        "fields": ["id", "fecha", "cliente", "producto", "cantidad", "precio_venta", "categoria", "region"],
        "dimensions": ["producto", "categoria", "cliente", "region"],
        "metrics":    ["cantidad", "precio_venta"],
        "temporal":   ["fecha"],
    },
    {
        "name": "ecommerce",
        "fields": ["order_id", "fecha_pedido", "usuario", "sku", "nombre_producto", "unidades", "precio_unitario", "descuento", "total", "canal", "estado_pedido"],
        "dimensions": ["nombre_producto", "canal", "estado_pedido", "usuario"],
        "metrics":    ["unidades", "precio_unitario", "descuento", "total"],
        "temporal":   ["fecha_pedido"],
    },
    {
        "name": "inventario",
        "fields": ["id", "producto", "categoria", "stock_actual", "stock_minimo", "costo_unitario", "proveedor", "bodega"],
        "dimensions": ["producto", "categoria", "proveedor", "bodega"],
        "metrics":    ["stock_actual", "stock_minimo", "costo_unitario"],
        "temporal":   [],
    },
    {
        "name": "rrhh",
        "fields": ["empleado_id", "nombre", "departamento", "cargo", "salario", "fecha_ingreso", "sucursal", "activo"],
        "dimensions": ["departamento", "cargo", "sucursal"],
        "metrics":    ["salario"],
        "temporal":   ["fecha_ingreso"],
    },
    {
        "name": "marketing",
        "fields": ["campania_id", "nombre_campania", "canal", "fecha_inicio", "fecha_fin", "inversion", "clicks", "conversiones", "roi", "segmento"],
        "dimensions": ["nombre_campania", "canal", "segmento"],
        "metrics":    ["inversion", "clicks", "conversiones", "roi"],
        "temporal":   ["fecha_inicio", "fecha_fin"],
    },
    {
        "name": "finanzas",
        "fields": ["fecha", "cuenta", "tipo_movimiento", "monto", "moneda", "categoria", "sucursal", "aprobado"],
        "dimensions": ["cuenta", "tipo_movimiento", "categoria", "sucursal"],
        "metrics":    ["monto"],
        "temporal":   ["fecha"],
    },
    {
        "name": "logistica",
        "fields": ["envio_id", "fecha_envio", "cliente", "destino", "peso_kg", "costo_envio", "transportista", "estado", "dias_entrega"],
        "dimensions": ["destino", "transportista", "estado", "cliente"],
        "metrics":    ["peso_kg", "costo_envio", "dias_entrega"],
        "temporal":   ["fecha_envio"],
    },
    {
        "name": "pos_restaurante",
        "fields": ["ticket_id", "fecha", "mesa", "producto", "categoria", "cantidad", "precio", "mesero", "turno"],
        "dimensions": ["producto", "categoria", "mesa", "mesero", "turno"],
        "metrics":    ["cantidad", "precio"],
        "temporal":   ["fecha"],
    },
]


def get_dataset_context_instruction(schema: dict) -> str:
    """Builds the dataset context instruction string from a schema dict."""
    fields_str = ", ".join(schema["fields"])
    return (
        f"You must use the following dataset context: "
        f"The available fields are: {fields_str}."
    )


def _pick(fields: list[str], offset: int) -> str:
    """Round-robin pick from a list using an integer offset."""
    return fields[offset % len(fields)]


def resolve_example(template: dict, schema: dict, offset: int) -> dict:
    """
    Returns a new example dict with dimension/metric/metric_y replaced
    by real fields from the schema. The template structure (chart_type,
    aggregation, sort_direction, limit, colors, filters) is preserved
    exactly — only the field names change.

    If a schema has no temporal fields and the template uses a temporal
    dimension (e.g. 'meses', 'fecha'), falls back to a categorical dimension.
    """
    import copy
    params = copy.deepcopy(template["parameters"])

    dims = schema["dimensions"]
    mets = schema["metrics"]
    # Use temporal fields for time-series dimensions when available,
    # otherwise fall back to categorical dimensions.
    temporal = schema.get("temporal") or dims

    # Detect whether the original dimension was time-based
    TIME_HINTS = {"meses", "mes", "fecha", "año", "años", "trimestre", "trimestres",
                  "semana", "semanas", "dia", "dias", "hora", "horas"}
    original_dim = params.get("dimension", "")
    is_temporal = any(hint in original_dim.lower() for hint in TIME_HINTS)

    if "dimension" in params:
        params["dimension"] = _pick(temporal if is_temporal else dims, offset)

    if "metric" in params:
        params["metric"] = _pick(mets, offset)

    if "metric_y" in params:
        # Pick a different metric than the one used for metric
        metric_index = offset % len(mets)
        metric_y_index = (offset + 1) % len(mets)
        # Ensure metric and metric_y are different when possible
        if len(mets) > 1 and metric_y_index == metric_index:
            metric_y_index = (metric_y_index + 1) % len(mets)
        params["metric_y"] = mets[metric_y_index]

    return {"intent": template["intent"], "parameters": params}




# ============================================================
# EJEMPLOS BASE POSITIVOS
#
# Python controla los parámetros.
# Nunca dejamos que el LLM invente el JSON.
# ============================================================

POSITIVE_EXAMPLES = [
    # --- bar ---
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "productos", "metric": "ventas", "aggregation": "sum"}},
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "categorías", "metric": "ventas", "aggregation": "sum"}},
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "productos", "metric": "ventas", "aggregation": "average"}},
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "productos", "metric": "ventas", "aggregation": "count"}},
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "sucursales", "metric": "ingresos", "aggregation": "sum"}},
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "marcas", "metric": "ventas", "aggregation": "sum"}},
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "proveedores", "metric": "deuda_total", "aggregation": "sum"}},
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "paises", "metric": "importaciones", "aggregation": "sum"}},
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "vendedores", "metric": "comisiones", "aggregation": "average"}},
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "ciudades", "metric": "usuarios_activos", "aggregation": "count"}},
    # --- line ---
    {"intent": "create_chart", "parameters": {"chart_type": "line", "dimension": "meses", "metric": "ventas", "aggregation": "sum"}},
    {"intent": "create_chart", "parameters": {"chart_type": "line", "dimension": "meses", "metric": "margen", "aggregation": "average"}},
    {"intent": "create_chart", "parameters": {"chart_type": "line", "dimension": "categorías", "metric": "ventas", "aggregation": "sum"}},
    {"intent": "create_chart", "parameters": {"chart_type": "line", "dimension": "fecha", "metric": "venta_total", "aggregation": "sum"}},
    {"intent": "create_chart", "parameters": {"chart_type": "line", "dimension": "fecha", "metric": "pedidos", "aggregation": "count"}},
    {"intent": "create_chart", "parameters": {"chart_type": "line", "dimension": "años", "metric": "ingresos", "aggregation": "sum"}},
    {"intent": "create_chart", "parameters": {"chart_type": "line", "dimension": "semanas", "metric": "visitas", "aggregation": "sum"}},
    {"intent": "create_chart", "parameters": {"chart_type": "line", "dimension": "dias", "metric": "errores", "aggregation": "count"}},
    {"intent": "create_chart", "parameters": {"chart_type": "line", "dimension": "trimestres", "metric": "ganancia_neta", "aggregation": "sum"}},
    {"intent": "create_chart", "parameters": {"chart_type": "line", "dimension": "horas", "metric": "temperatura", "aggregation": "average"}},
    # --- pie (el usuario puede decir "circular" - siempre mapea a "pie") ---
    {"intent": "create_chart", "parameters": {"chart_type": "pie", "dimension": "categorías", "metric": "ventas", "aggregation": "sum"}},
    {"intent": "create_chart", "parameters": {"chart_type": "pie", "dimension": "productos", "metric": "ventas", "aggregation": "sum"}},
    {"intent": "create_chart", "parameters": {"chart_type": "pie", "dimension": "categorías", "metric": "ingresos", "aggregation": "sum"}},
    {"intent": "create_chart", "parameters": {"chart_type": "pie", "dimension": "vendedores", "metric": "ventas", "aggregation": "sum"}},
    {"intent": "create_chart", "parameters": {"chart_type": "pie", "dimension": "regiones", "metric": "ventas", "aggregation": "sum"}},
    {"intent": "create_chart", "parameters": {"chart_type": "pie", "dimension": "canales", "metric": "conversiones", "aggregation": "count"}},
    {"intent": "create_chart", "parameters": {"chart_type": "pie", "dimension": "dispositivos", "metric": "sesiones", "aggregation": "count"}},
    {"intent": "create_chart", "parameters": {"chart_type": "pie", "dimension": "tipos_pago", "metric": "ingresos", "aggregation": "sum"}},
    {"intent": "create_chart", "parameters": {"chart_type": "pie", "dimension": "segmentos", "metric": "clientes", "aggregation": "count"}},
    {"intent": "create_chart", "parameters": {"chart_type": "pie", "dimension": "marcas", "metric": "inventario", "aggregation": "sum"}},
    # --- scatter: SIEMPRE "scatter", NUNCA "line".
    {"intent": "create_chart", "parameters": {"chart_type": "scatter", "dimension": "productos", "metric": "precio", "metric_y": "cantidad_vendida", "aggregation": "sum"}},
    {"intent": "create_chart", "parameters": {"chart_type": "scatter", "dimension": "productos", "metric": "costo", "metric_y": "ganancia", "aggregation": "sum"}},
    {"intent": "create_chart", "parameters": {"chart_type": "scatter", "dimension": "clientes", "metric": "descuento", "metric_y": "unidades_compradas", "aggregation": "sum"}},
    {"intent": "create_chart", "parameters": {"chart_type": "scatter", "dimension": "productos", "metric": "precio", "metric_y": "margen", "aggregation": "average"}},
    {"intent": "create_chart", "parameters": {"chart_type": "scatter", "dimension": "categorías", "metric": "venta_total", "metric_y": "costo_total", "aggregation": "average"}},
    {"intent": "create_chart", "parameters": {"chart_type": "scatter", "dimension": "clientes", "metric": "edad", "metric_y": "total_compras", "aggregation": "count"}},
    {"intent": "create_chart", "parameters": {"chart_type": "scatter", "dimension": "campañas", "metric": "inversión", "metric_y": "roi", "aggregation": "average"}},
    {"intent": "create_chart", "parameters": {"chart_type": "scatter", "dimension": "sucursales", "metric": "metros_cuadrados", "metric_y": "ingresos", "aggregation": "sum"}},
    {"intent": "create_chart", "parameters": {"chart_type": "scatter", "dimension": "vehiculos", "metric": "kilometraje", "metric_y": "precio_reventa", "aggregation": "average"}},
    {"intent": "create_chart", "parameters": {"chart_type": "scatter", "dimension": "estudiantes", "metric": "horas_estudio", "metric_y": "nota_final", "aggregation": "average"}},
    # --- sort_direction ---
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "productos", "metric": "ventas", "aggregation": "sum", "sort_direction": "asc"}},
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "productos", "metric": "ventas", "aggregation": "sum", "sort_direction": "desc"}},
    {"intent": "create_chart", "parameters": {"chart_type": "line", "dimension": "meses", "metric": "ventas", "aggregation": "sum", "sort_direction": "asc"}},
    {"intent": "create_chart", "parameters": {"chart_type": "pie", "dimension": "categorías", "metric": "ventas", "aggregation": "sum", "sort_direction": "desc"}},
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "ciudades", "metric": "poblacion", "aggregation": "sum", "sort_direction": "desc"}},
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "empleados", "metric": "ausencias", "aggregation": "sum", "sort_direction": "asc"}},
    # --- limit: DEBE extraerse del número en "los N más/menos X" ---
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "productos", "metric": "ventas", "aggregation": "sum", "limit": 5}},
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "productos", "metric": "ventas", "aggregation": "sum", "sort_direction": "desc", "limit": 10}},
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "categorías", "metric": "ingresos", "aggregation": "sum", "sort_direction": "desc", "limit": 3}},
    {"intent": "create_chart", "parameters": {"chart_type": "pie", "dimension": "regiones", "metric": "ventas", "aggregation": "sum", "limit": 5}},
    {"intent": "create_chart", "parameters": {"chart_type": "line", "dimension": "meses", "metric": "precio_venta", "aggregation": "sum", "limit": 6}},
    {"intent": "create_chart", "parameters": {"chart_type": "scatter", "dimension": "productos", "metric": "precio", "metric_y": "margen_total", "aggregation": "average", "limit": 20}},
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "vendedores", "metric": "ventas", "aggregation": "sum", "sort_direction": "desc", "limit": 7}},
    {"intent": "create_chart", "parameters": {"chart_type": "pie", "dimension": "productos", "metric": "ventas", "aggregation": "sum", "sort_direction": "desc", "limit": 5}},
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "servicios", "metric": "costos", "aggregation": "sum", "sort_direction": "asc", "limit": 3}},
    {"intent": "create_chart", "parameters": {"chart_type": "line", "dimension": "semanas", "metric": "usuarios_nuevos", "aggregation": "sum", "sort_direction": "desc", "limit": 4}},
    # --- color ---
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "productos", "metric": "ventas", "aggregation": "sum", "colors": ["blue"]}},
    {"intent": "create_chart", "parameters": {"chart_type": "line", "dimension": "meses", "metric": "ventas_total", "aggregation": "sum", "colors": ["green"]}},
    {"intent": "create_chart", "parameters": {"chart_type": "pie", "dimension": "categorías", "metric": "ventas", "aggregation": "sum", "colors": ["red"]}},
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "regiones", "metric": "ingresos", "aggregation": "sum", "colors": ["orange", "blue"]}},
    {"intent": "create_chart", "parameters": {"chart_type": "pie", "dimension": "canales", "metric": "ventas", "aggregation": "sum", "colors": ["red", "yellow", "green"]}},
    {"intent": "create_chart", "parameters": {"chart_type": "scatter", "dimension": "clientes", "metric": "edad", "metric_y": "compras", "aggregation": "sum", "colors": ["purple"]}},
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "marcas", "metric": "ventas", "aggregation": "sum", "colors": ["black", "gray"]}},
    # --- aggregation=average ---
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "categorías", "metric": "precio", "aggregation": "average"}},
    {"intent": "create_chart", "parameters": {"chart_type": "line", "dimension": "meses", "metric": "ticket_promedio", "aggregation": "average"}},
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "vendedores", "metric": "comisión", "aggregation": "average"}},
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "sucursales", "metric": "ingresos", "aggregation": "average"}},
    {"intent": "create_chart", "parameters": {"chart_type": "pie", "dimension": "categorías", "metric": "precio_unitario", "aggregation": "average"}},
    {"intent": "create_chart", "parameters": {"chart_type": "scatter", "dimension": "productos", "metric": "costo", "metric_y": "precio_venta", "aggregation": "average"}},
    {"intent": "create_chart", "parameters": {"chart_type": "line", "dimension": "dias", "metric": "tiempo_respuesta", "aggregation": "average"}},
    # --- tallas: dimension="tallas", NO confundir con la métrica ---
    {"intent": "create_chart", "parameters": {"chart_type": "pie", "dimension": "tallas", "metric": "unidades_vendidas", "aggregation": "sum"}},
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "tallas", "metric": "total_venta", "aggregation": "sum", "sort_direction": "desc"}},
    {"intent": "create_chart", "parameters": {"chart_type": "pie", "dimension": "tallas", "metric": "ventas", "aggregation": "sum"}},
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "tallas", "metric": "ventas", "aggregation": "count"}},
    # --- combos completos ---
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "productos", "metric": "venta_total", "aggregation": "sum", "sort_direction": "desc", "limit": 5, "colors": ["red"]}},
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "sucursales", "metric": "ingresos", "aggregation": "average", "sort_direction": "desc", "limit": 10, "colors": ["purple"]}},
    {"intent": "create_chart", "parameters": {"chart_type": "scatter", "dimension": "clientes", "metric": "compras_totales", "metric_y": "ticket_promedio", "aggregation": "average", "colors": ["lightblue"]}},
    {"intent": "create_chart", "parameters": {"chart_type": "scatter", "dimension": "regiones", "metric": "costo_envío", "metric_y": "ingresos", "aggregation": "average", "colors": ["yellow"]}},
    {"intent": "create_chart", "parameters": {"chart_type": "scatter", "dimension": "campañas", "metric": "inversión", "metric_y": "roi", "aggregation": "average", "colors": ["white"]}},
    {"intent": "create_chart", "parameters": {"chart_type": "pie", "dimension": "vendedores", "metric": "comisiones", "aggregation": "average", "sort_direction": "asc", "limit": 3, "colors": ["green"]}},
    {"intent": "create_chart", "parameters": {"chart_type": "line", "dimension": "días", "metric": "visitas", "aggregation": "count", "sort_direction": "desc", "limit": 14, "colors": ["blue"]}},
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "marcas", "metric": "ingresos_totales", "aggregation": "sum", "sort_direction": "desc", "limit": 10, "colors": ["orange"]}},
    {"intent": "create_chart", "parameters": {"chart_type": "pie", "dimension": "tallas", "metric": "unidades_vendidas", "aggregation": "sum", "sort_direction": "desc", "limit": 4, "colors": ["pink"]}},
    {"intent": "create_chart", "parameters": {"chart_type": "line", "dimension": "años", "metric": "crecimiento", "aggregation": "average", "sort_direction": "asc", "limit": 5, "colors": ["black"]}},
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "canales", "metric": "conversiones", "aggregation": "count", "sort_direction": "desc", "limit": 8, "colors": ["gray"]}},
    # --- filters: igualdad (eq) ---
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "productos", "metric": "ventas", "aggregation": "sum", "filters": [{"field": "categoria", "operator": "eq", "value": "Electrónica"}]}},
    {"intent": "create_chart", "parameters": {"chart_type": "line", "dimension": "meses", "metric": "ingresos", "aggregation": "sum", "filters": [{"field": "region", "operator": "eq", "value": "Norte"}]}},
    {"intent": "create_chart", "parameters": {"chart_type": "pie", "dimension": "categorías", "metric": "ventas", "aggregation": "sum", "filters": [{"field": "año", "operator": "eq", "value": 2024}]}},
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "vendedores", "metric": "comisiones", "aggregation": "sum", "filters": [{"field": "activo", "operator": "eq", "value": True}]}},
    # --- filters: distinto (neq) ---
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "productos", "metric": "ventas", "aggregation": "sum", "filters": [{"field": "categoria", "operator": "neq", "value": "Descontinuado"}]}},
    # --- filters: rangos (gt / gte / lt / lte) ---
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "productos", "metric": "ventas", "aggregation": "sum", "filters": [{"field": "precio", "operator": "gt", "value": 100}]}},
    {"intent": "create_chart", "parameters": {"chart_type": "line", "dimension": "meses", "metric": "ingresos", "aggregation": "sum", "filters": [{"field": "año", "operator": "gte", "value": 2023}]}},
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "categorías", "metric": "margen", "aggregation": "average", "filters": [{"field": "costo", "operator": "lt", "value": 500}]}},
    {"intent": "create_chart", "parameters": {"chart_type": "scatter", "dimension": "clientes", "metric": "edad", "metric_y": "compras_totales", "aggregation": "sum", "filters": [{"field": "edad", "operator": "lte", "value": 35}]}},
    # --- filters: búsqueda parcial (contains) ---
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "productos", "metric": "ventas", "aggregation": "sum", "filters": [{"field": "nombre", "operator": "contains", "value": "Pro"}]}},
    {"intent": "create_chart", "parameters": {"chart_type": "pie", "dimension": "categorías", "metric": "ventas", "aggregation": "sum", "filters": [{"field": "descripcion", "operator": "contains", "value": "tech"}]}},
    # --- filters: múltiples filtros combinados ---
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "productos", "metric": "ventas", "aggregation": "sum", "filters": [{"field": "categoria", "operator": "eq", "value": "Electrónica"}, {"field": "precio", "operator": "gt", "value": 200}]}},
    {"intent": "create_chart", "parameters": {"chart_type": "line", "dimension": "meses", "metric": "ingresos", "aggregation": "sum", "filters": [{"field": "region", "operator": "eq", "value": "Sur"}, {"field": "año", "operator": "gte", "value": 2023}]}},
    {"intent": "create_chart", "parameters": {"chart_type": "bar", "dimension": "vendedores", "metric": "ventas", "aggregation": "sum", "sort_direction": "desc", "limit": 10, "filters": [{"field": "activo", "operator": "eq", "value": True}, {"field": "ventas", "operator": "gt", "value": 1000}]}},
    
    # ============================================================
    # UPDATE_CHART
    # ============================================================
    # --- sort_direction solo ---
    {"intent": "update_chart", "parameters": {"sort_direction": "asc"}},   # menos vendidos / de menor a mayor
    {"intent": "update_chart", "parameters": {"sort_direction": "asc"}},   
    {"intent": "update_chart", "parameters": {"sort_direction": "desc"}},  # más vendidos / de mayor a menor
    {"intent": "update_chart", "parameters": {"sort_direction": "desc"}},  
    # --- sort_direction + limit: fuerza frases "los N más/menos X" ---
    {"intent": "update_chart", "parameters": {"sort_direction": "asc",  "limit": 5}},   # los 5 menos vendidos
    {"intent": "update_chart", "parameters": {"sort_direction": "asc",  "limit": 10}},  # los 10 menos vendidos
    {"intent": "update_chart", "parameters": {"sort_direction": "asc",  "limit": 3}},   # los 3 menos vendidos
    {"intent": "update_chart", "parameters": {"sort_direction": "desc", "limit": 5}},   # los 5 más vendidos
    {"intent": "update_chart", "parameters": {"sort_direction": "desc", "limit": 10}},  # los 10 más vendidos
    {"intent": "update_chart", "parameters": {"sort_direction": "desc", "limit": 3}},   # los 3 más vendidos
    # --- show_grid solo ---
    {"intent": "update_chart", "parameters": {"show_grid": True}},
    {"intent": "update_chart", "parameters": {"show_grid": False}},
    # --- limit solo ---
    {"intent": "update_chart", "parameters": {"limit": 5}},
    {"intent": "update_chart", "parameters": {"limit": 10}},
    {"intent": "update_chart", "parameters": {"limit": 3}},
    {"intent": "update_chart", "parameters": {"limit": 4}},
    {"intent": "update_chart", "parameters": {"limit": 2}},
    {"intent": "update_chart", "parameters": {"limit": 15}},
    {"intent": "update_chart", "parameters": {"limit": 20}},
    # --- colors solo ---
    {"intent": "update_chart", "parameters": {"colors": ["red"]}},
    {"intent": "update_chart", "parameters": {"colors": ["blue"]}},
    {"intent": "update_chart", "parameters": {"colors": ["green"]}},
    {"intent": "update_chart", "parameters": {"colors": ["red", "blue"]}},
    {"intent": "update_chart", "parameters": {"colors": ["green", "yellow", "red"]}},
    {"intent": "update_chart", "parameters": {"colors": ["purple", "orange"]}},
    {"intent": "update_chart", "parameters": {"colors": ["black"]}},
    # --- title solo ---
    {"intent": "update_chart", "parameters": {"title": "Ventas por producto"}},
    {"intent": "update_chart", "parameters": {"title": "Top 10 categorías"}},
    {"intent": "update_chart", "parameters": {"title": "Ingresos mensuales"}},
    {"intent": "update_chart", "parameters": {"title": "Ventas"}},
    {"intent": "update_chart", "parameters": {"title": "Resumen anual"}},
    {"intent": "update_chart", "parameters": {"title": "Crecimiento"}},
    {"intent": "update_chart", "parameters": {"title": "Rendimiento Q1"}},
    {"intent": "update_chart", "parameters": {"title": "Comparativa de costos"}},
    # --- chart_type solo ---
    {"intent": "update_chart", "parameters": {"chart_type": "bar"}},
    {"intent": "update_chart", "parameters": {"chart_type": "line"}},
    {"intent": "update_chart", "parameters": {"chart_type": "pie"}},
    {"intent": "update_chart", "parameters": {"chart_type": "scatter", "metric_y": "costo"}},
    # --- metric solo ---
    {"intent": "update_chart", "parameters": {"metric": "ingresos"}},
    {"intent": "update_chart", "parameters": {"metric": "venta_total"}},
    {"intent": "update_chart", "parameters": {"metric": "margen"}},
    {"intent": "update_chart", "parameters": {"metric": "unidades_vendidas"}},
    {"intent": "update_chart", "parameters": {"metric": "precio_promedio"}},
    {"intent": "update_chart", "parameters": {"metric": "descuentos"}},
    # --- metric_y solo (para scatter) ---
    {"intent": "update_chart", "parameters": {"metric_y": "costo"}},
    {"intent": "update_chart", "parameters": {"metric_y": "ganancia"}},
    {"intent": "update_chart", "parameters": {"metric_y": "roi"}},
    {"intent": "update_chart", "parameters": {"metric_y": "ticket_promedio"}},
    {"intent": "update_chart", "parameters": {"metric_y": "utilidad"}},
    # --- metric + otros campos ---
    {"intent": "update_chart", "parameters": {"metric": "ingresos", "colors": ["blue"]}},
    {"intent": "update_chart", "parameters": {"metric": "venta_total", "sort_direction": "desc"}},
    {"intent": "update_chart", "parameters": {"metric": "margen", "title": "Margen por producto"}},
    {"intent": "update_chart", "parameters": {"metric": "ingresos", "chart_type": "bar"}},
    {"intent": "update_chart", "parameters": {"metric": "venta_total", "sort_direction": "desc", "limit": 10}},
    {"intent": "update_chart", "parameters": {"metric": "conversiones", "colors": ["green"], "title": "Conversiones mensuales"}},
    {"intent": "update_chart", "parameters": {"metric": "rentabilidad", "colors": ["purple"], "sort_direction": "asc"}},
    # --- metric_y + otros campos ---
    {"intent": "update_chart", "parameters": {"metric_y": "ingresos", "colors": ["red"]}},
    {"intent": "update_chart", "parameters": {"metric_y": "costo_total", "title": "Costo contra ventas"}},
    {"intent": "update_chart", "parameters": {"metric": "precio", "metric_y": "margen"}},
    # --- combos de 2 campos ---
    {"intent": "update_chart", "parameters": {"chart_type": "bar", "sort_direction": "asc"}},
    {"intent": "update_chart", "parameters": {"chart_type": "line", "show_grid": True}},
    {"intent": "update_chart", "parameters": {"chart_type": "pie", "limit": 5}},
    {"intent": "update_chart", "parameters": {"chart_type": "scatter", "metric_y": "margen"}},
    {"intent": "update_chart", "parameters": {"chart_type": "scatter", "metric": "precio", "metric_y": "unidades"}},
    {"intent": "update_chart", "parameters": {"sort_direction": "asc", "limit": 10}},
    {"intent": "update_chart", "parameters": {"sort_direction": "desc", "show_grid": False}},
    {"intent": "update_chart", "parameters": {"limit": 3, "title": "Top 3 productos"}},
    {"intent": "update_chart", "parameters": {"colors": ["red"], "show_grid": True}},
    {"intent": "update_chart", "parameters": {"show_grid": True, "title": "Ventas"}},
    {"intent": "update_chart", "parameters": {"title": "Ventas por producto", "colors": ["green"]}},
    {"intent": "update_chart", "parameters": {"sort_direction": "desc", "title": "Mayores ventas"}},
    {"intent": "update_chart", "parameters": {"sort_direction": "asc", "title": "Menores ventas"}},
    {"intent": "update_chart", "parameters": {"sort_direction": "asc", "title": "Crecimiento de ventas", "colors": ["green"]}},
    {"intent": "update_chart", "parameters": {"sort_direction": "desc", "title": "Top productos", "colors": ["red"]}},
    {"intent": "update_chart", "parameters": {"chart_type": "line", "title": "Tendencia mensual"}},
    {"intent": "update_chart", "parameters": {"limit": 10, "colors": ["orange"]}},
    {"intent": "update_chart", "parameters": {"limit": 20, "colors": ["purple"]}},
    # --- combos de 3 campos ---
    {"intent": "update_chart", "parameters": {"sort_direction": "desc", "show_grid": False, "limit": 10}},
    {"intent": "update_chart", "parameters": {"colors": ["red"], "show_grid": True, "title": "Ventas mensuales"}},
    {"intent": "update_chart", "parameters": {"chart_type": "bar", "sort_direction": "desc", "colors": ["blue"]}},
    {"intent": "update_chart", "parameters": {"chart_type": "scatter", "show_grid": True, "title": "Dispersión de margen"}},
    {"intent": "update_chart", "parameters": {"limit": 5, "sort_direction": "desc", "title": "Top 5"}},
    {"intent": "update_chart", "parameters": {"chart_type": "pie", "limit": 3, "colors": ["green"]}},
    # --- combos completos ---
    {"intent": "update_chart", "parameters": {"chart_type": "bar", "sort_direction": "desc", "limit": 5, "colors": ["yellow"], "show_grid": True, "title": "Top 5"}},
    {"intent": "update_chart", "parameters": {"chart_type": "bar", "sort_direction": "asc", "limit": 15, "colors": ["purple"], "show_grid": True, "title": "Resumen completo"}},
    {"intent": "update_chart", "parameters": {"chart_type": "line", "sort_direction": "desc", "limit": 12, "colors": ["gray"], "show_grid": False, "title": "Evolución anual"}},
    {"intent": "update_chart", "parameters": {"chart_type": "scatter", "metric_y": "gastos", "colors": ["black"], "show_grid": True, "title": "Ingresos vs Gastos"}},
    # --- color + title ---
    {"intent": "update_chart", "parameters": {"colors": ["blue"], "title": "Ventas por categoría"}},
    {"intent": "update_chart", "parameters": {"colors": ["red"], "title": "Top productos"}},
    {"intent": "update_chart", "parameters": {"colors": ["green"], "title": "Ingresos por región"}},
    {"intent": "update_chart", "parameters": {"colors": ["purple"], "title": "Ventas por marca"}},
    {"intent": "update_chart", "parameters": {"colors": ["orange"], "title": "Pedidos del mes"}},
    # --- filters solo en update ---
    {"intent": "update_chart", "parameters": {"filters": [{"field": "categoria", "operator": "eq", "value": "Electrónica"}]}},
    {"intent": "update_chart", "parameters": {"filters": [{"field": "precio", "operator": "gt", "value": 500}]}},
    {"intent": "update_chart", "parameters": {"filters": [{"field": "nombre", "operator": "contains", "value": "Pro"}]}},
    {"intent": "update_chart", "parameters": {"filters": [{"field": "año", "operator": "gte", "value": 2023}]}},
    # --- filters + otros campos de update ---
    {"intent": "update_chart", "parameters": {"filters": [{"field": "region", "operator": "eq", "value": "Norte"}], "colors": ["blue"]}},
    {"intent": "update_chart", "parameters": {"filters": [{"field": "precio", "operator": "lt", "value": 200}], "sort_direction": "desc"}},
    {"intent": "update_chart", "parameters": {"filters": [{"field": "categoria", "operator": "neq", "value": "Descontinuado"}], "title": "Productos activos"}},
    {"intent": "update_chart", "parameters": {"filters": [{"field": "categoria", "operator": "eq", "value": "Ropa"}, {"field": "año", "operator": "gte", "value": 2024}], "sort_direction": "desc", "limit": 5}},
    {"intent": "update_chart", "parameters": {"filters": [{"field": "status", "operator": "eq", "value": "Entregado"}], "show_grid": True, "title": "Pedidos entregados"}},
]


# ============================================================
# EJEMPLOS NEGATIVOS
#
# Estas preguntas contienen conceptos relacionados con
# gráficos/datos, pero NO requieren una herramienta.
# ============================================================

NEGATIVE_EXAMPLES = [
    # ============================================================
    # 1. PREGUNTAS SOBRE DATOS
    # ============================================================
    "¿Cuáles son los productos más vendidos?",
    "¿Qué producto vendió más?",
    "¿Cuál fue el producto con mayores ventas?",
    "¿Qué productos tienen más ventas?",
    "¿Cuál es el producto menos vendido?",
    "¿Cuánto vendimos este mes?",
    "¿Cuánto vendimos durante enero?",
    "¿Cuántas ventas tuvimos este año?",
    "¿Cuál fue el total de ventas?",
    "¿Cuánto dinero generaron las ventas?",
    "¿Cuál es el margen promedio?",
    "¿Qué producto tiene mayor margen?",
    "¿Cuál es el producto con menor margen?",
    "¿Qué categoría genera más ingresos?",
    "¿Qué categoría vende menos?",
    "¿Cuál fue el mes con mayores ventas?",
    "¿Cuál fue el mes con menores ventas?",
    "¿Cuántas unidades vendimos?",
    "¿Cuántos productos se vendieron?",
    "¿Cuál es el promedio de ventas?",
    "¿Cuál es el promedio de margen por producto?",
    # ============================================================
    # 2. ANÁLISIS DE DATOS
    # ============================================================
    "Analiza las ventas por producto.",
    "Analiza el comportamiento de las ventas.",
    "Analiza el rendimiento de los productos.",
    "Analiza las ventas de este mes.",
    "Analiza el margen de los productos.",
    "Analiza las ventas por categoría.",
    "¿Qué conclusiones puedes sacar de las ventas?",
    "¿Qué productos tienen mejor rendimiento?",
    "¿Qué productos tienen peor rendimiento?",
    "¿Qué tendencias observas en las ventas?",
    "¿Qué producto debería vender más?",
    "¿Qué productos están teniendo un buen desempeño?",
    "¿Qué productos están teniendo un bajo desempeño?",
    "¿Qué categoría tiene mejor rendimiento?",
    "¿Cómo se comportaron las ventas durante el año?",
    "¿Qué podemos concluir de nuestros datos de ventas?",
    "¿Qué oportunidades ves en estos datos?",
    "¿Qué problemas puedes detectar en las ventas?",
    # ============================================================
    # 3. COMPARACIONES Y OPERACIONES SOBRE DATOS
    # ============================================================
    "Compara las ventas de enero y febrero.",
    "Compara las ventas de este mes con las del mes pasado.",
    "Compara el margen de los productos.",
    "Compara las ventas entre categorías.",
    "¿Qué producto vendió más que los demás?",
    "¿Qué categoría tuvo mayor crecimiento?",
    "¿Qué mes tuvo mejores resultados?",
    "¿Qué producto tuvo el mayor incremento de ventas?",
    "¿Qué producto tuvo la mayor caída en ventas?",
    "Ordena los productos de mayor a menor.",
    "Ordena las categorías por ventas.",
    "Ordena los productos por margen.",
    "Clasifica los productos según sus ventas.",
    "Dime cuáles son los tres productos con más ventas.",
    # ============================================================
    # 4. MODIFICACIÓN DE DATOS
    # ============================================================
    "Cambia el nombre del producto.",
    "Actualiza el precio del producto.",
    "Modifica el precio del producto.",
    "Cambia el nombre de una categoría.",
    "Actualiza las ventas del producto.",
    "Modifica los datos del producto.",
    "Elimina este producto.",
    "Agrega un nuevo producto.",
    "Cambia la categoría del producto.",
    "Actualiza la información del producto.",
    "Corrige el precio del producto.",
    "Modifica el margen del producto.",
    # ============================================================
    # 5. CONCEPTOS SOBRE GRÁFICOS
    # ============================================================
    "¿Qué es un gráfico de barras?",
    "¿Qué es un gráfico de líneas?",
    "¿Qué es un gráfico circular?",
    "¿Qué es un gráfico de dispersión?",
    "¿Qué significa gráfico de barras?",
    "¿Cuál es la diferencia entre un gráfico de barras y uno de líneas?",
    "¿Cuál es la diferencia entre un gráfico circular y uno de barras?",
    "¿Cuándo debería utilizar un gráfico de barras?",
    "¿Cuándo debería utilizar un gráfico de líneas?",
    "¿Cuándo debería utilizar un gráfico circular?",
    "¿Cuándo es recomendable utilizar un gráfico de dispersión?",
    "¿Qué tipo de datos se pueden representar con un gráfico de barras?",
    "¿Qué información muestra un gráfico de líneas?",
    "¿Qué información muestra un gráfico circular?",
    "¿Para qué sirve un gráfico de dispersión?",
    "¿Cómo se interpreta un gráfico de barras?",
    "¿Cómo se interpreta un gráfico de líneas?",
    "¿Cómo funciona un gráfico circular?",
    "¿Cómo funciona un gráfico de dispersión?",
    "¿Qué ventajas tiene un gráfico de barras?",
    "¿Qué ventajas tiene un gráfico de líneas?",
    # ============================================================
    # 6. SOLICITUDES VAGAS O INCOMPLETAS DE GRÁFICOS
    # ============================================================
    "Hazme un gráfico.",
    "Crea un chart.",
    "Quiero un gráfico de barras pero no sé de qué.",
    "Dibuja un gráfico de líneas.",
    "Genera una visualización.",
    "Muéstrame eso en un gráfico.",
    "Ponlo en formato visual.",
    "¿Me haces un pie chart?",
    "Actualiza el gráfico.",
    "Cámbiale los colores.",
    "Modifica esto.",
    "Crea una gráfica con los datos.",
    "Quiero ver mis datos.",
    "Necesito una representación visual.",
    # ============================================================
    # 7. SOLICITUDES DE EJEMPLOS
    # ============================================================
    "Dame un ejemplo de un gráfico de barras.",
    "Dame un ejemplo de un gráfico de líneas.",
    "Dame un ejemplo de un gráfico circular.",
    "Dame un ejemplo de un gráfico de dispersión.",
    "¿Puedes mostrarme un ejemplo de un gráfico de barras?",
    "¿Puedes mostrarme un ejemplo de un gráfico de líneas?",
    "¿Cómo sería un gráfico de barras?",
    "¿Cómo sería un gráfico de líneas?",
    "Enséñame un ejemplo de un gráfico circular.",
    # ============================================================
    # 7. SOLICITUDES DE CÓDIGO
    # ============================================================
    "Dame el código de un gráfico de barras en Python.",
    "¿Cómo puedo crear un gráfico de barras en Python?",
    "¿Cómo hago un gráfico de líneas con Python?",
    "¿Puedes darme código para crear un gráfico circular?",
    "¿Cómo implemento un gráfico de dispersión en Python?",
    "Dame un ejemplo de código usando Matplotlib para un gráfico de barras.",
    "¿Cómo puedo crear gráficos con Python?",
    "¿Qué librería de Python puedo utilizar para crear gráficos?",
    "¿Cómo puedo crear un gráfico con Pandas?",
    "¿Cómo puedo personalizar un gráfico en Python?",
    # ============================================================
    # 8. CONCEPTOS DE NEGOCIO / DATOS
    # ============================================================
    "¿Qué significa margen en ventas?",
    "¿Qué es el margen de ganancia?",
    "¿Qué significa promedio?",
    "¿Qué es una métrica?",
    "¿Qué es una dimensión?",
    "¿Qué es una agregación?",
    "¿Qué significa sumar las ventas?",
    "¿Qué significa calcular el promedio?",
    "¿Qué es un KPI?",
    "¿Qué es un KPI y cómo se utiliza en el análisis de datos?",
    "¿Cómo puedo analizar mis datos de ventas?",
    "¿Cómo puedo mejorar mis habilidades de análisis de datos?",
    "¿Cómo puedo mejorar mis ventas?",
    "¿Cuál es la mejor estrategia de marketing?",
    # ============================================================
    # 9. CONSULTAS GENERALES
    # ============================================================
    "¿Qué puedes hacer?",
    "¿Cuáles son tus funciones?",
    "¿Puedes ayudarme?",
    "Necesito ayuda.",
    "¿Cómo puedes ayudarme?",
    "¿Qué tipo de cosas puedes hacer?",
    "¿Quién eres?",
    "¿Cómo te llamas?",
    "Hola.",
    "Hola, ¿cómo estás?",
    "Buenos días.",
    "Buenas tardes.",
    "Buenas noches.",
    "Gracias.",
    "Muchas gracias.",
    "Hasta luego.",
    "¡Hasta la vista!",
    # ============================================================
    # 10. CONSULTAS COMPLETAMENTE AJENAS
    # ============================================================
    "¿Cuál es la capital de Francia?",
    "¿Cuál es la capital de El Salvador?",
    "¿Cuál es la población de España?",
    "¿Dónde queda Barcelona?",
    "¿Cuál es el clima promedio en Madrid?",
    "¿Cuál es el clima hoy?",
    "¿Quién es el presidente de Estados Unidos?",
    "¿Cuál es la población de Estados Unidos?",
    "¿Cuál es la moneda de Japón?",
    "¿Cuántos habitantes tiene El Salvador?",
    "¿Cuál es la capital de Alemania?",
    "¿Dónde está París?",
]

# ============================================================
# CONSTRUCCIÓN DE PROMPTS
# ============================================================


def create_positive_prompt(example: dict, variation: str, schema: dict) -> str:
    intent = example["intent"]
    parameters = json.dumps(
        example["parameters"],
        ensure_ascii=False,
    )

    if intent == "create_chart":
        action = "crear un gráfico nuevo desde cero"
        action_hint = (
            "IMPORTANTE: usa verbos de creación como 'crea', 'dame', 'haz', 'genera', 'muéstrame'. "
            "La frase describe una petición NUEVA, no una modificación de algo existente."
        )
    else:
        action = "modificar/actualizar el gráfico que ya está en pantalla"
        action_hint = (
            "IMPORTANTE: el gráfico YA EXISTE en pantalla. "
            "Usa OBLIGATORIAMENTE verbos de modificación como 'cambia', 'actualiza', 'ahora muestra', "
            "'pon', 'modifica', 'ajusta', 'limita a', 'quiero que ahora'. "
            "NUNCA uses 'crea', 'genera', 'dame un gráfico' porque el gráfico ya existe. "
            "La frase debe dejar claro que es una acción sobre algo que ya se está viendo."
        )

    # Build chart_type hint to reinforce correct mappings in generated phrases
    chart_type = example["parameters"].get("chart_type", "")
    limit_val = example["parameters"].get("limit")
    aggregation = example["parameters"].get("aggregation", "")

    metric_val = example["parameters"].get("metric")
    metric_y_val = example["parameters"].get("metric_y")
    
    if metric_val and metric_y_val:
        scatter_rel = f"El gráfico relaciona '{metric_val}' (eje X) con '{metric_y_val}' (eje Y). La frase DEBE mencionar explícitamente ambas variables."
    elif metric_y_val:
        scatter_rel = f"La frase DEBE mencionar explícitamente la nueva métrica '{metric_y_val}' para el eje Y o como segunda variable."
    else:
        scatter_rel = ""

    chart_type_hints = {
        "scatter": (
            "IMPORTANTE: usa siempre la frase 'gráfico de dispersión' para referirte al tipo de gráfico. "
            "NUNCA uses 'gráfico de líneas'. "
            + scatter_rel
        ),
        "pie": "IMPORTANTE: puedes llamarlo 'gráfico circular', 'gráfico de torta', 'gráfico de pastel' o 'pie chart'. NUNCA uses 'circle' ni ningún valor fuera del enum.",
    }
    
    if limit_val is not None:
        limit_hint = f"IMPORTANTE: el límite de elementos es {limit_val}. Exprésalo obligatoriamente como 'los {limit_val} más...', 'top {limit_val}', o 'mostrar solo {limit_val} datos'. Usa números en lugar de palabras (2 en vez de dos)."
    else:
        limit_hint = "IMPORTANTE: NO hay un límite de elementos especificado. NUNCA inventes cantidades numéricas ni uses palabras como 'top 5' o 'dos datos'."

    aggregation_hint = (
        "IMPORTANTE: la agregación es 'average' (promedio). En el texto puedes decir 'promedio' o 'media', pero el valor del parámetro es SIEMPRE 'average', nunca 'promedio'."
        if aggregation == "average"
        else ""
    )

    order_val = example["parameters"].get("sort_direction", "")
    order_hint = {
        "asc": (
            "IMPORTANTE: el orden es ascendente (de menor a mayor). "
            "Expresa 'los menos X', 'los peores', 'de menor a mayor'. "
            "NUNCA uses 'los más vendidos' ni 'los mejores'."
        ),
        "desc": (
            "IMPORTANTE: el orden es descendente (de mayor a menor). "
            "Expresa 'los más vendidos', 'los mejores', 'de mayor a menor'. "
            "NUNCA uses 'los menos vendidos' ni 'los peores'."
        ),
    }.get(order_val, "")

    colors_val = example["parameters"].get("colors")
    if isinstance(colors_val, list) and colors_val:
        if len(colors_val) > 1:
            colors_hint = "IMPORTANTE: el usuario pide varios colores. Los valores están en INGLÉS en el parámetro, pero en tu frase debes pedir los colores en ESPAÑOL. Exprésalo de forma natural como 'con colores rojo, azul y verde' (traduciendo los valores). NO uses corchetes []."
        else:
            colors_hint = "IMPORTANTE: el usuario pide un color. El valor está en INGLÉS en el parámetro, pero en la frase debes pedirlo en ESPAÑOL (ej. si dice 'red', redacta 'en color rojo'). NO uses corchetes []."
    else:
        colors_hint = "IMPORTANTE: NO hay color especificado en los parámetros. NUNCA menciones colores en la frase."

    title_val = example["parameters"].get("title")
    if title_val:
        title_hint = f"IMPORTANTE: el usuario pide explícitamente que el nuevo título sea '{title_val}'. Incluye esa petición literal en la frase (ej. pon de título '{title_val}', o cambia el nombre a '{title_val}')."
    else:
        title_hint = "IMPORTANTE: NO hay título especificado. NUNCA menciones un título en la frase."

    filters_val = example["parameters"].get("filters", [])
    if filters_val:
        filters_hint = "IMPORTANTE: el usuario pide filtrar los datos. Menciona los filtros explícitamente de forma natural en la frase, por ejemplo 'donde la categoría sea Electrónica' o 'con precio mayor a 100'. No menciones la palabra 'filters' ni uses el formato JSON."
    else:
        filters_hint = "IMPORTANTE: NO hay filtros en los parámetros. La frase NO debe sugerir ninguna condición, restricción de datos, 'donde', 'que sean de', 'solo los de', ni nada que implique filtrar. El gráfico muestra todos los datos sin condiciones."

    extra_hints = "\n".join(filter(None, [
        action_hint,
        chart_type_hints.get(chart_type, ""),
        limit_hint,
        aggregation_hint,
        order_hint,
        colors_hint,
        title_hint,
        filters_hint,
    ]))

    # Build a list of parameter keys present so the prompt is explicit
    present_params = list(example["parameters"].keys())
    present_params_str = ", ".join(present_params)

    return f"""
Genera 15 expresiones distintas de la intención proporcionada.

Contexto del dataset:
{get_dataset_context_instruction(schema)}

Estilo de esta generación:
{variation}

Acción:
{action}

Parámetros (EXACTAMENTE estos, ni más ni menos):
{parameters}

Parámetros presentes: {present_params_str}

Reglas estrictas:
- Cada respuesta debe expresar exactamente la misma intención.
- CRÍTICO: La frase SOLO debe implicar los parámetros listados en "Parámetros presentes". Si un parámetro NO está en esa lista, la frase NO debe mencionarlo ni sugerirlo de ninguna forma.
- CRÍTICO: NUNCA inventes colores, títulos, filtros, ordenamiento, límites, ni ningún otro parámetro que no esté en los Parámetros.
- CRÍTICO: Si la acción es 'modificar', la frase DEBE sonar como una modificación de algo existente, NUNCA como creación de algo nuevo.
- Incluye diversidad de tonos: formal, informal, coloquial y hasta con algún pequeño error de tipeo natural.
- Tomar en cuenta que una metric se puede representar con guion bajo ejemplo precio_total, etc
- Usa exactamente la misma palabra para la dimensión y métrica que aparecen en los parámetros, sin agregar sufijos inventados como '_id'.
- Los campos que menciones en las frases DEBEN ser campos reales del dataset. No inventes campos que no están en el contexto del dataset.
- No elimines requisitos que sí están en los parámetros.
- No cambies ningún valor de los parámetros.
- No menciones explícitamente los nombres técnicos de los parámetros (ej: en vez de "dimension sucursales", di "para las sucursales").
- Usa lenguaje natural y conversacional.
- Las frases deben ser muy diferentes entre sí en estructura y vocabulario.
- Una frase por línea.
- No agregues un numeral al inicio de cada frase (1., 2., 3., etc.).
- El idioma de la frase debe ser español siempre.
- Respeta el estilo de la generación, no agregues explicaciones ni comentarios.
{extra_hints}
""".strip()


def create_negative_prompt(query: str) -> str:
    """
    Genera variaciones de una intención que NO requiere
    ninguna herramienta.
    """
    return f"""
Genera 5 formas diferentes de expresar la siguiente intención:

"{query}"

Reglas estrictas:
- La petición NO debe solicitar crear ni modificar un gráfico válido de forma completa.
- No debe requerir ninguna herramienta técnica del sistema.
- Mantén exactamente la misma intención base.
- Incluye diversidad de tonos: formal, informal, directo, y con dudas.
- Usa lenguaje natural en español.
- Las frases deben ser muy diferentes entre sí.
- Una frase por línea.
- No agregues un numeral al inicio de cada frase (1., 2., 3., etc.).
- El idioma de la frase debe ser español siempre.
""".strip()


def build_positive_row(query: str, example: dict, schema: dict | None = None) -> dict:
    intent = example["intent"]
    # Strip None, empty lists, and empty dicts — the model must never see
    # null or empty collection fields in the answer (e.g. filters: []).
    # The tools schema stays full so training matches inference exactly.
    clean_params = {
        k: v for k, v in example["parameters"].items()
        if v is not None and v != [] and v != {}
    }

    row = {
        "query": query,
        "tools": TOOLS,
        "answers": [
            {
                "name": intent,
                "arguments": clean_params,
            }
        ],
    }
    if schema:
        row["dataset_context"] = schema
    return row


def build_negative_row(query: str, schema: dict | None = None) -> dict:
    row = {
        "query": query,
        "tools": TOOLS,
        "answers": [],
    }
    if schema:
        row["dataset_context"] = schema
    return row


def save_jsonl(rows: list[dict], path: str) -> None:
    # "w" — overwrites the file on every run so stale data from
    # previous generations never pollutes the new dataset.
    with open(path, "w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


VARIATIONS = [
    "formal",
    "coloquial",
    "directa",
    "pregunta",
    "imperativa",
    "usuario de negocio",
    "usuario técnico",
    "usuario principiante",
    "mensaje muy corto",
    "mensaje detallado",
    "lenguaje natural",
    "con abreviaciones",
    "con pequeño error tipográfico",
]

def generate_dataset():
    from distilabel.llms import vLLM
    from distilabel.pipeline import Pipeline
    from distilabel.steps.tasks import TextGeneration
    from distilabel.steps import LoadDataFromDicts

    with Pipeline(name="chart-tool-dataset") as pipeline:

        inputs = []

        # -------------------------
        # POSITIVOS
        # -------------------------

        # 5 pasadas × len(POSITIVE_EXAMPLES) × len(DATASET_CONTEXTS) × 15 frases
        for index in range(7):
            for ex_index, template in enumerate(POSITIVE_EXAMPLES):
                # Rotate across all available dataset schemas
                schema = DATASET_CONTEXTS[(index * len(POSITIVE_EXAMPLES) + ex_index) % len(DATASET_CONTEXTS)]

                # Substitute dimension/metric with real fields from the schema.
                # The offset combines pass + example index for maximum field variety.
                offset = index * len(POSITIVE_EXAMPLES) + ex_index
                example = resolve_example(template, schema, offset)

                inputs.append(
                    {
                        "instruction": create_positive_prompt(example, VARIATIONS[index % len(VARIATIONS)], schema),
                        "type": "positive",
                        "intent": example["intent"],
                        # Serialize as JSON string — distilabel preserves strings
                        # reliably across pipeline steps; nested dicts may be lost.
                        "parameters": json.dumps(example["parameters"], ensure_ascii=False),
                        "dataset_context": json.dumps(schema, ensure_ascii=False),
                    }
                )

        # -------------------------
        # NEGATIVOS
        #6 pasadas para mantener proporción balanceada con el set positivo
        # -------------------------
        for neg_index, _ in enumerate(range(5)):
            for q_index, query in enumerate(NEGATIVE_EXAMPLES):
                schema = DATASET_CONTEXTS[(neg_index * len(NEGATIVE_EXAMPLES) + q_index) % len(DATASET_CONTEXTS)]
                inputs.append(
                    {
                        "instruction": create_negative_prompt(query),
                        "type": "negative",
                        "intent": None,
                        "parameters": None,
                        "dataset_context": json.dumps(schema, ensure_ascii=False),
                    }
                )

        loader = LoadDataFromDicts(name="load_data", data=inputs)

        local_llm = vLLM(
            model="Qwen/Qwen2.5-14B-Instruct",
            tokenizer="Qwen/Qwen2.5-14B-Instruct",
            extra_kwargs={
                "max_model_len": 8192,  # Limita el contexto para que no desborde la VRAM
                "gpu_memory_utilization": 0.95,  # Le da permiso a vLLM de usar casi toda la GPU
            },
        )

        generator = TextGeneration(
            name="generate_queries",
            llm=local_llm,
            input_batch_size=8,
        )

        loader >> generator

        result = pipeline.run(
            parameters={
                "generate_queries": {
                    "llm": {
                        "generation_kwargs": {
                            "temperature": 0.7,  # más variedad léxica sin perder coherencia
                            "top_p": 0.9,
                            "max_new_tokens": 512,
                        }
                    }
                }
            }
        )

    return result


def process_results(result):

    print("Procesando resultados...", result)

    rows = []

    # Dependiendo de la versión de Distilabel,
    # aquí tendrás acceso a los outputs del step.
    #
    # Conceptualmente:
    #
    # generated_text = ...
    #
    # Después convertimos cada frase en:
    #
    # positive -> answers con tool
    # negative -> answers []

    for item in result["default"]["train"]:

        generated_text = item["generation"]

        print("Generado:", generated_text)

        lines = [line.strip() for line in generated_text.split("\n") if line.strip()]

        # Deserialize dataset_context (stored as JSON string by distilabel)
        raw_context = item.get("dataset_context")
        if isinstance(raw_context, str):
            try:
                schema = json.loads(raw_context)
            except (json.JSONDecodeError, TypeError):
                schema = None
        elif isinstance(raw_context, dict):
            schema = raw_context
        else:
            schema = None

        if item["type"] == "positive":
            raw_params_value = item["parameters"]

            # Deserialize: parameters was stored as a JSON string to survive
            # distilabel's internal serialization. Parse it back to a dict.
            if isinstance(raw_params_value, str):
                try:
                    raw_params = json.loads(raw_params_value)
                except (json.JSONDecodeError, TypeError):
                    raw_params = None
            elif isinstance(raw_params_value, dict):
                raw_params = raw_params_value  # legacy / already a dict
            else:
                raw_params = None

            if not raw_params or not isinstance(raw_params, dict):
                print(f"[SKIP] parameters vacío o inválido para intent={item['intent']}: {raw_params_value!r}")
                continue

            example = {
                "intent": item["intent"],
                "parameters": raw_params,
            }

            for query in lines:
                row = build_positive_row(query, example, schema)
                # Secondary guard: never save a positive row with empty arguments
                if not row["answers"][0]["arguments"]:
                    print(f"[SKIP] arguments vacío después de clean_params: query={query!r}")
                    continue
                rows.append(row)

        else:

            for query in lines:

                rows.append(build_negative_row(query, schema))

    return rows


# ============================================================
# MAIN
# ============================================================


@app.function(
    image=image,
    gpu="A100",
    timeout=60 * 60 * 24,
    secrets=[modal.Secret.from_name("huggingface")],
    volumes={VOLUME_MOUNT: volume},
)
def start():

    import random

    import os

    token = os.getenv("HF_TOKEN")

    print("HF_TOKEN existe:", token is not None)
    print("HF_TOKEN válido:", token[:7] if token else None)

    result = generate_dataset()

    dataset = process_results(result)

    random.shuffle(dataset)

    save_jsonl(dataset, path=f"{VOLUME_MOUNT}/dataset.jsonl")

    print(f"Dataset generado: {len(dataset)} ejemplos")


@app.local_entrypoint()
def main():
    start.remote()
