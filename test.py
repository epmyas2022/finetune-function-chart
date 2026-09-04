import ollama

_FILTER_ITEM_SCHEMA = {
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

_FILTERS_FIELD = {
    "type": "array",
    "description": "Filtros sobre los datos antes de graficar. Cada filtro es un objeto {field, operator, value}. Se pueden combinar múltiples filtros. IMPORTANTE: NUNCA uses filters para extraer el límite de elementos (ej. '5 productos' o 'top 5'). El límite de elementos numérico SIEMPRE va en la propiedad limit o number_of_items, NUNCA en filters.",
    "items": {
        "$ref": "#/_FILTER_ITEM_SCHEMA"
    }
}

tools = [
    {
        "type": "function",
        "function": {
            "name": "create_chart",
            "description": "Crea un nuevo gráfico a partir de los datos.",
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
    },
    {
        "type": "function",
        "function": {
            "name": "update_chart",
            "description": "Actualiza propiedades del gráfico actualmente mostrado.",
            "parameters": {
                "type": "object",
                "properties": {
                    "chart_type": {
                        "type": "string",
                        "enum": ["bar", "line", "pie", "scatter"],
                        "description": "Nuevo tipo de gráfico. bar (barras), line (líneas), pie (circular o pastel. NUNCA uses 'pastel', usa 'pie'), scatter (dispersión)."
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
    }
]

tests = [
    "Crea un grafico de barras color rojo de los 5 productos mas vendidos usando la metrica de venta_total.",
    "Crea un grafico de las tallas mas vendidas usando la metrica de total_venta",
    "Crea un grafico de lineas de las ventas por fecha usando la metrica de venta_total.",
    "Crea un grafico circular de las ventas por categoria usando la metrica de ingresos.",
    "Crea un grafico de dispersion relacionando precio y cantidad vendida.",
    # ------------------------------------------------------------------
    # CREATE_CHART - agregaciones
    # ------------------------------------------------------------------
    "Muestra las ventas totales por producto agrupando por producto y sumando venta_total.",
    "Crea un grafico con el promedio de precio por categoria.",
    "Crea un grafico mostrando la cantidad de ventas por producto.",
    "Hola, como estas?",
    "Actualiza el color del grafico a azul y el titulo a 'Ventas por categoria'.",
]


for test in tests:
    try:
        response = ollama.chat(
            model="function-gemma-chart",
            messages=[
                {
                    "role": "user",
                    "content": test,
                }
            ],
            tools=tools,
        )

        print("\nCONSULTA:", test)

        print("CONTENT:")
        print(response["message"]["content"])

        print("\nTOOL CALLS:")
        print(response["message"].get("tool_calls"))
    except Exception as e:
        print("\nCONSULTA:", test)
        continue
