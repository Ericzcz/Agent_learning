# Docker Compose 常用命令总结

## 1. 基本概念

在 `compose.yaml` 或 `docker-compose.yml` 里，如果写了：

```yaml
services:
  api:
    build: .
    image: myfastapi
    container_name: myfastapi
    ports:
      - "8000:80"
```

含义是：

- `build: .`：根据当前目录下的 `Dockerfile` 构建 image。
- `image: myfastapi`：把构建出来的 image 命名为 `myfastapi`。
- `container_name: myfastapi`：创建出来的 container 名字叫 `myfastapi`。
- `ports: "8000:80"`：把本机的 `8000` 端口映射到容器内部的 `80` 端口。

整体流程是：

```text
Dockerfile  ->  image  ->  container
```

也就是说，`docker compose up` 并不是跳过 image，而是自动帮你 build image，然后再创建并启动 container。

---

## 2. 启动服务

### 前台启动

```bash
docker compose up
```

作用：

- 读取 `compose.yaml` / `docker-compose.yml`
- 如果有 `build: .`，会根据 `Dockerfile` 构建 image
- 创建并启动 container
- 在当前终端显示日志

停止方式：

```text
Ctrl + C
```

适合调试时使用，因为可以直接看到日志。

---

### 后台启动

```bash
docker compose up -d
```

作用：

- 在后台启动服务
- 不占用当前终端

适合日常运行。

---

### 启动并重新构建 image

```bash
docker compose up --build
```

作用：

- 重新 build image
- 然后启动 container

适合你修改了 Dockerfile、依赖文件、镜像内容之后使用。

例如修改了这些文件后，通常需要重新 build：

```text
Dockerfile
requirements.txt
pyproject.toml
poetry.lock
package.json
```

---

### 后台启动并重新构建

```bash
docker compose up -d --build
```

作用：

- 重新 build image
- 后台启动服务

这是开发中很常用的命令。

---

## 3. 停止服务

### 只停止 container

```bash
docker compose stop
```

作用：

- 停止 container
- 不删除 container
- 不删除 network
- 不删除 image

之后可以用下面的命令重新启动：

```bash
docker compose start
```

适合只是临时关闭服务。

---

### 停止并删除 container

```bash
docker compose down
```

作用：

- 停止 container
- 删除 container
- 删除 Compose 创建的 network
- 通常不会删除 image

之后如果再次运行：

```bash
docker compose up
```

Docker Compose 会重新创建 container。

---

### 停止并删除 container、network、本地 image

```bash
docker compose down --rmi local
```

作用：

- 停止 container
- 删除 container
- 删除 Compose 创建的 network
- 删除 Compose 构建出来的本地 image

如果之后再 `docker compose up`，需要重新 build image。

---

### 停止并删除 volume

```bash
docker compose down -v
```

作用：

- 停止 container
- 删除 container
- 删除 network
- 删除 volume

注意：如果 volume 里存的是数据库数据，这个命令可能会把数据删掉。使用前要确认。

---

## 4. 重新启动服务

### 启动已经停止的 container

```bash
docker compose start
```

作用：

- 启动之前已经存在、但处于停止状态的 container
- 不重新创建 container
- 不重新 build image

通常配合：

```bash
docker compose stop
```

一起使用。

---

### 重启 container

```bash
docker compose restart
```

作用：

- 停止 container
- 再重新启动 container
- 不重新 build image

适合只想重启服务，不改 image 的情况。

---

## 5. 查看日志

### 查看当前日志

```bash
docker compose logs
```

作用：

- 查看 Compose 服务的日志

---

### 实时查看日志

```bash
docker compose logs -f
```

作用：

- 持续输出日志
- 类似实时监控

退出方式：

```text
Ctrl + C
```

---

### 查看指定服务日志

如果 service 名叫 `api`：

```bash
docker compose logs -f api
```

作用：

- 只查看 `api` 这个服务的日志

---

## 6. 查看状态

### 查看 Compose 管理的 container

```bash
docker compose ps
```

作用：

- 查看当前 Compose 项目里的 container 状态
- 可以看到是否运行、端口映射等信息

---

### 查看所有 container

```bash
docker ps -a
```

作用：

- 查看所有 container
- 包括正在运行的和已经停止的

---

### 查看正在运行的 container

```bash
docker ps
```

作用：

- 只查看正在运行的 container

---

## 7. 查看 image

### 查看所有 images

```bash
docker images
```

作用：

- 查看本机已有的 Docker images

---

### 查看 Compose 创建的 images

```bash
docker compose images
```

作用：

- 查看当前 Compose 项目使用的 image

---

## 8. 进入 container

如果 service 名叫 `api`：

```bash
docker compose exec api bash
```

作用：

- 进入正在运行的 `api` container

如果 container 里没有 `bash`，可以用：

```bash
docker compose exec api sh
```

---

## 9. 修改代码之后怎么做

### 情况一：没有使用 volume

如果你的代码是通过 Dockerfile 复制进 image 的，比如：

```dockerfile
COPY ./app /code/app
```

那么修改代码后，需要重新 build：

```bash
docker compose up --build
```

或者后台运行：

```bash
docker compose up -d --build
```

---

### 情况二：使用了 volume

如果 compose 里写了：

```yaml
volumes:
  - ./app:/code/app
```

意思是把本地的 `./app` 挂载到容器里的 `/code/app`。

这种情况下，你修改本地代码，container 里也能看到变化。

如果你的 FastAPI / Uvicorn 开了 reload，通常不用重新 build。

可以只重启：

```bash
docker compose restart
```

或者如果前台运行，直接重新启动：

```bash
docker compose up
```

---

## 10. 常用命令速查表

| 命令 | 作用 |
|---|---|
| `docker compose up` | 前台启动服务，显示日志 |
| `docker compose up -d` | 后台启动服务 |
| `docker compose up --build` | 重新 build image 并启动 |
| `docker compose up -d --build` | 重新 build image 并后台启动 |
| `docker compose stop` | 只停止 container，不删除 |
| `docker compose start` | 启动已经停止的 container |
| `docker compose restart` | 重启 container，不重新 build |
| `docker compose down` | 停止并删除 container 和 network |
| `docker compose down --rmi local` | 停止并删除 container、network、本地 image |
| `docker compose down -v` | 停止并删除 container、network、volume |
| `docker compose ps` | 查看当前 Compose 项目的 container 状态 |
| `docker compose logs` | 查看日志 |
| `docker compose logs -f` | 实时查看日志 |
| `docker compose images` | 查看 Compose 使用的 images |
| `docker images` | 查看本机所有 images |
| `docker ps` | 查看正在运行的 container |
| `docker ps -a` | 查看所有 container |
| `docker compose exec api bash` | 进入 api container |

---

## 11. 推荐日常开发流程

### 第一次启动

```bash
docker compose up --build
```

或者后台：

```bash
docker compose up -d --build
```

---

### 平时启动

```bash
docker compose up -d
```

---

### 查看日志

```bash
docker compose logs -f
```

---

### 临时停止

```bash
docker compose stop
```

---

### 再次启动

```bash
docker compose start
```

---

### 修改 Dockerfile 或依赖后

```bash
docker compose up -d --build
```

---

### 想彻底删除 container 后重新来

```bash
docker compose down

docker compose up -d --build
```

---

## 12. 最重要的区别

```text
docker compose stop
= 停止 container，但 container 还在
```

```text
docker compose down
= 停止并删除 container 和 network
```

```text
docker compose up --build
= 重新构建 image，然后启动 container
```

```text
docker compose restart
= 重启 container，但不重新 build image
```
