# FastAPI Docker 修改代码后的操作流程

## 1. 开发阶段推荐流程

开发阶段建议使用：

- `volume mount`
- `fastapi dev`
- 自动 reload

这样你修改 Python 代码后，不需要每次重新 build Docker image。

---

## 2. 第一次启动项目

### 2.1 构建 Docker image

在项目根目录执行：

```bash
docker build --pull -t myfastapi .
docker build --pull --no-cache -t myfastapi .
```

含义：

- `docker build`：构建 Docker image
- `-t myfastapi`：给 image 起名叫 `myfastapi`
- `.`：使用当前目录下的 Dockerfile 和项目文件

---

### 2.2 启动 container

```bash
docker run -d \
  --name mycontainer \
  -p 8000:80 \
  -v $(pwd)/app:/code/app \
  myfastapi
```

含义：

- `-d`：后台运行
- `--name mycontainer`：container 名字叫 `mycontainer`
- `-p 8000:80`：把本机 8000 端口映射到 container 的 80 端口
- `-v $(pwd)/app:/code/app`：把本地 `app` 目录挂载到 container 的 `/code/app`
- `myfastapi`：使用刚才 build 出来的 image

---

### 2.3 访问 FastAPI 文档

浏览器打开：

```text
http://127.0.0.1:8000/docs
```

---

## 3. 以后修改代码后怎么做

## 情况一：只修改了 Python 代码

例如你修改了：

```text
app/main.py
```

如果你使用了 volume mount 和 reload，一般不需要重新 build。

操作流程：

```text
保存代码
→ 等待 FastAPI 自动 reload
→ 刷新网页
```

如果页面没有变化，可以先查看日志：

```bash
docker logs mycontainer
```

也可以重启 container：

```bash
docker restart mycontainer
```

---

## 情况二：修改了 requirements.txt 或 Dockerfile

如果你修改了：

```text
requirements.txt
Dockerfile
```

就需要重新 build image。

完整流程：

```bash
docker stop mycontainer
docker rm mycontainer
docker build -t myfastapi .
docker run -d \
  --name mycontainer \
  -p 8000:80 \
  -v $(pwd)/app:/code/app \
  myfastapi
```

---

## 4. 最简单记忆方式

### 只改 Python 代码

```text
保存代码
→ 自动 reload
→ 刷新网页
```

### 改了依赖或 Docker 配置

```text
stop
→ rm
→ build
→ run
```

---

## 5. 常用 Docker 命令速查

### 查看正在运行的 container

```bash
docker ps
```

### 查看所有 container

```bash
docker ps -a
```

### 查看日志

```bash
docker logs mycontainer
```

### 重启 container

```bash
docker restart mycontainer
```

### 停止 container

```bash
docker stop mycontainer
```

### 删除 container

```bash
docker rm mycontainer
```

### 重新构建 image

```bash
docker build -t myfastapi .
```

---

## 6. 推荐开发版 Dockerfile

```dockerfile
FROM python:3.14

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./app /code/app

CMD ["fastapi", "dev", "app/main.py", "--host", "0.0.0.0", "--port", "80"]
```

---

## 7. 总结

开发阶段：

```text
改 Python 文件：不用重新 build
改 requirements.txt / Dockerfile：需要重新 build
```

生产部署：

```text
每次改代码
→ 重新 build image
→ 重启 container
```
