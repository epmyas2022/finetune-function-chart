FROM samueltallet/alpine-llama-cpp-server:latest

WORKDIR /app

RUN apk add --no-cache curl && \
    curl -L "https://github.com/epmyas2022/finetune-function-chart/releases/download/model-0-0-2/qwen2.5-1.5b-instruct.Q4_K_M.gguf" -o qwen2.5-1.5b-instruct.Q4_K_M.gguf 

EXPOSE 8080


CMD [ \
    "/opt/llama.cpp/llama-server", \
    "-m", "./qwen2.5-1.5b-instruct.Q4_K_M.gguf", \
    "-c", "4096", \
    "-np", "1", \
    "-t", "6", \
    "-tb", "6", \
    "-fa","on", \
    "--jinja", \
    "--temp", "0.3", \
    "--top-p", "0.9", \
    "--min-p", "0.05", \
    "--repeat-penalty", "1.1", \
    "--host", "0.0.0.0", \
    "--port", "8080" \
    ]