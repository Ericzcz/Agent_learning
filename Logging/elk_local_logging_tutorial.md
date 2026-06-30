# 本地 ELK 接入 Python / FastAPI 日志使用教程

本文档适用于这种场景：

```text
Python / FastAPI 本地运行
        ↓
写入 logs/app.log
        ↓
Logstash 读取日志文件
        ↓
Elasticsearch 存储日志
        ↓
Kibana 查询和展示日志
```

你的业务项目不需要放进 ELK 的 Docker Compose 里。ELK 单独用一个 `elk-compose.yml` 启动即可。

---

## 1. 目录结构

建议项目结构如下：

```text
your-project/
├── app/
│   └── main.py
├── logs/
│   └── app.log
├── elk-compose.yml
└── logstash/
    └── pipeline/
        └── logstash.conf
```

创建目录：

```bash
mkdir -p logs
mkdir -p logstash/pipeline
```

---

## 2. Python 日志配置

安装 JSON 日志库：

```bash
pip install python-json-logger
```

新建日志配置文件，例如：

```text
app/logging_config.py
```

内容如下：

```python
import logging
import os
import sys
from pythonjsonlogger import jsonlogger


def setup_logging() -> None:
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # 避免重复添加 handler
    if logger.handlers:
        logger.handlers.clear()

    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(filename)s %(lineno)d %(message)s"
    )

    # 输出到控制台
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # 输出到本地文件
    log_path = os.getenv("LOG_PATH", "logs/app.log")
    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
```

---

## 3. FastAPI 中使用日志

例如 `app/main.py`：

```python
import logging
from fastapi import FastAPI

from app.logging_config import setup_logging

setup_logging()

app = FastAPI()
logger = logging.getLogger(__name__)


@app.get("/")
def root():
    logger.info("root endpoint called")
    return {"status": "ok"}


@app.get("/error")
def error():
    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("calculation failed")

    return {"status": "error logged"}
```

启动 FastAPI：

```bash
uvicorn app.main:app --reload
```

访问接口后，日志会写入：

```text
logs/app.log
```

查看日志：

```bash
cat logs/app.log
```

你应该能看到类似：

```json
{"asctime": "2026-06-30 10:30:12,345", "levelname": "INFO", "name": "app.main", "filename": "main.py", "lineno": 14, "message": "root endpoint called"}
```

---

## 4. Logstash 配置

新建文件：

```text
logstash/pipeline/logstash.conf
```

内容如下：

```conf
input {
  file {
    path => "/host_logs/app.log"
    start_position => "beginning"
    sincedb_path => "/dev/null"
    codec => json
  }
}

filter {
  date {
    match => ["asctime", "yyyy-MM-dd HH:mm:ss,SSS"]
    target => "@timestamp"
  }
}

output {
  elasticsearch {
    hosts => ["http://elasticsearch:9200"]
    index => "python-app-logs-%{+YYYY.MM.dd}"
  }

  stdout {
    codec => rubydebug
  }
}
```

说明：

```text
input  = 从 /host_logs/app.log 读取日志
filter = 把 Python 日志里的 asctime 转换成 Elasticsearch 的 @timestamp
output = 写入 Elasticsearch，同时打印到 Logstash 控制台方便调试
```

这里的 `/host_logs/app.log` 是 Logstash 容器内部路径，后面会通过 Docker volume 映射到本机的 `./logs/app.log`。

---

## 5. ELK Docker Compose 配置

新建文件：

```text
elk-compose.yml
```

内容如下：

```yaml
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.17.0
    container_name: local_elasticsearch
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - ES_JAVA_OPTS=-Xms512m -Xmx512m
    ports:
      - "9200:9200"
    volumes:
      - elk_es_data:/usr/share/elasticsearch/data

  logstash:
    image: docker.elastic.co/logstash/logstash:8.17.0
    container_name: local_logstash
    depends_on:
      - elasticsearch
    volumes:
      - ./logstash/pipeline:/usr/share/logstash/pipeline
      - ./logs:/host_logs
    ports:
      - "5044:5044"

  kibana:
    image: docker.elastic.co/kibana/kibana:8.17.0
    container_name: local_kibana
    depends_on:
      - elasticsearch
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    ports:
      - "5601:5601"

volumes:
  elk_es_data:
```

关键配置：

```yaml
- ./logs:/host_logs
```

意思是：

```text
本机 ./logs
映射到
Logstash 容器里的 /host_logs
```

所以 Logstash 读取：

```text
/host_logs/app.log
```

实际读取的是本机：

```text
logs/app.log
```

---

## 6. 启动 ELK

在 `elk-compose.yml` 所在目录执行：

```bash
docker compose -f elk-compose.yml up -d
```

查看容器状态：

```bash
docker compose -f elk-compose.yml ps
```

你应该看到：

```text
local_elasticsearch
local_logstash
local_kibana
```

---

## 7. 检查 Elasticsearch

浏览器打开：

```text
http://localhost:9200
```

或者终端执行：

```bash
curl http://localhost:9200
```

如果返回类似下面内容，说明 Elasticsearch 正常：

```json
{
  "name": "xxx",
  "cluster_name": "docker-cluster",
  "version": {
    "number": "8.17.0"
  }
}
```

---

## 8. 检查 Logstash 是否读到日志

查看 Logstash 日志：

```bash
docker compose -f elk-compose.yml logs -f logstash
```

如果 Logstash 成功读取 `app.log`，你会看到类似字段：

```text
"levelname" => "INFO"
"message" => "root endpoint called"
"name" => "app.main"
```

如果没有内容，先手动写一条测试日志：

```bash
echo '{"asctime":"2026-06-30 10:30:12,345","levelname":"INFO","name":"test","filename":"manual.py","lineno":1,"message":"hello elk"}' >> logs/app.log
```

然后再次查看：

```bash
docker compose -f elk-compose.yml logs -f logstash
```

---

## 9. 检查 Elasticsearch 是否有日志索引

执行：

```bash
curl "http://localhost:9200/_cat/indices?v"
```

正常应该看到类似：

```text
python-app-logs-2026.06.30
```

如果没有这个 index，说明 Logstash 还没有成功写入 Elasticsearch。

---

## 10. 在 Kibana 中查看日志

浏览器打开：

```text
http://localhost:5601
```

进入：

```text
Stack Management
→ Data Views
→ Create data view
```

Data view 名称填写：

```text
python-app-logs-*
```

时间字段选择：

```text
@timestamp
```

创建完成后进入：

```text
Discover
```

就可以查看日志了。

---

## 11. Kibana 空白时怎么排查

### 情况一：时间范围太小

Kibana 默认可能是：

```text
Last 15 minutes
```

如果你的日志时间不在最近 15 分钟内，就会显示空。

解决方法：

```text
点击 Search entire time range
或者把时间范围改成 Last 24 hours / Last 7 days
```

### 情况二：Elasticsearch 没有 index

检查：

```bash
curl "http://localhost:9200/_cat/indices?v"
```

如果没有 `python-app-logs-*`，说明日志没有写入 Elasticsearch。

### 情况三：Logstash 没有读到文件

检查本机文件：

```bash
ls -l logs/app.log
cat logs/app.log
```

检查容器内是否能看到文件：

```bash
docker exec -it local_logstash ls -l /host_logs
docker exec -it local_logstash cat /host_logs/app.log
```

如果容器里看不到文件，检查 `elk-compose.yml` 的 volume：

```yaml
- ./logs:/host_logs
```

### 情况四：JSON 格式不正确

`logs/app.log` 必须是一行一条 JSON，例如：

```json
{"asctime":"2026-06-30 10:30:12,345","levelname":"INFO","message":"server started"}
```

不要是 Python 普通文本日志：

```text
2026-06-30 10:30:12 | INFO | server started
```

因为 Logstash 配置里写的是：

```conf
codec => json
```

---

## 12. 常用命令

启动 ELK：

```bash
docker compose -f elk-compose.yml up -d
```

停止 ELK，但保留 Elasticsearch 数据：

```bash
docker compose -f elk-compose.yml down
```

停止 ELK，并删除 Elasticsearch 数据：

```bash
docker compose -f elk-compose.yml down -v
```

查看 Logstash 日志：

```bash
docker compose -f elk-compose.yml logs -f logstash
```

查看 Elasticsearch index：

```bash
curl "http://localhost:9200/_cat/indices?v"
```

删除测试日志 index：

```bash
curl -X DELETE "http://localhost:9200/python-app-logs-*"
```

---

## 13. 整体链路总结

```text
FastAPI / Python
    ↓ logger.info()
logs/app.log
    ↓ Docker volume: ./logs:/host_logs
Logstash
    ↓ parse JSON + parse asctime
Elasticsearch
    ↓ index: python-app-logs-YYYY.MM.dd
Kibana
    ↓ Discover 查询日志
```

一句话：

```text
Python 负责产生日志，Logstash 负责读取和解析，Elasticsearch 负责存储和搜索，Kibana 负责展示。
```
