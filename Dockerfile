FROM alpine/ollama

WORKDIR /app

RUN apk add --no-cache curl && \
    curl -L "https://github.com/epmyas2022/finetune-function-chart/releases/download/model-0-0-2/qwen2.5-1.5b-instruct.Q4_K_M.gguf" -o qwen2.5-1.5b-instruct.Q4_K_M.gguf && \
    curl -L "https://github.com/epmyas2022/finetune-function-chart/releases/download/model-0-0-1/Modelfile" -o Modelfile

# "Horneamos" el modelo dentro de la imagen levantando el server solo durante el build
RUN ollama serve & \
    sleep 3 && \
    ollama create chart-model -f Modelfile && \
    pkill ollama

EXPOSE 11434

ENTRYPOINT ["ollama", "serve"]