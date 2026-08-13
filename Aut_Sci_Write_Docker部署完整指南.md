# Aut_Sci_Write Docker 部署完整指南

> 本文档面向希望通过 Docker 使用 Aut_Sci_Write 技能包的用户
> 
> 更新时间：2026-06-04

---

## 📋 目录

1. [为什么使用 Docker 版本](#为什么使用-docker-版本)
2. [前置条件检查](#前置条件检查)
3. [获取项目代码](#获取项目代码)
4. [配置 API 密钥](#配置-api-密钥)
5. [构建 Docker 镜像](#构建-docker-镜像)
6. [启动容器](#启动容器)
7. [使用技能](#使用技能)
8. [常用操作](#常用操作)
9. [故障排除](#故障排除)
10. [与 Claude Code 的关系](#与-claude-code-的关系)

---

## 为什么使用 Docker 版本

### Docker 版本的优势

| 对比项 | 传统安装 | Docker 安装 |
|--------|----------|------------|
| Python 环境 | 需要手动安装 3.10+ | 镜像自带，无需配置 |
| Node.js 环境 | 需要手动安装 18+ | 镜像自带，无需配置 |
| Tesseract OCR | Windows 需手动下载并配置路径 | 自动集成，开箱即用 |
| 依赖冲突 | 可能与系统其他项目冲突 | 完全隔离 |
| 系统兼容性 | Windows/Mac/Linux 差异大 | 统一环境 |
| 部署服务器 | 需重新配置环境 | 直接复制镜像 |

### 适用场景

✅ **推荐使用 Docker 的情况**：
- 你不想在本机安装 Python/Node.js 等开发环境
- 你需要在服务器上批量处理文献
- 你遇到了依赖冲突或版本问题
- 你希望在多台电脑上保持环境一致

❌ **不推荐使用 Docker 的情况**：
- 你主要在 Claude Code 中使用（直接用 `npx skills add` 安装更方便）
- 你的电脑性能有限（Docker 需要额外开销）
- 你只是偶尔使用一两个 skill

---

## 前置条件检查

### 1. 检查操作系统

Docker Desktop 支持：
- **Windows 10/11** 专业版/企业版/教育版（需要 WSL2）
- **Windows 10/11** 家庭版（需要 WSL2，20H1 及以上版本）
- **macOS** 10.15 或更高版本
- **Linux** 主流发行版（Ubuntu、Debian、CentOS 等）

### 2. 检查硬件要求

最低配置：
- **内存**：8GB RAM（推荐 16GB）
- **硬盘**：至少 10GB 可用空间（镜像约 1.2GB + 数据空间）
- **处理器**：支持虚拟化的 64 位处理器

### 3. 安装 Docker Desktop

#### Windows 用户

1. **启用 WSL2**（如果尚未启用）

打开 PowerShell（管理员权限）：

```powershell
wsl --install
```

重启电脑后，再次打开 PowerShell 验证：

```powershell
wsl -l -v
```

应该看到类似输出：
```
  NAME      STATE           VERSION
* Ubuntu    Running         2
```

2. **下载并安装 Docker Desktop**

访问：https://www.docker.com/products/docker-desktop/

下载 Windows 版本并安装。安装时选择：
- ✅ Use WSL 2 instead of Hyper-V
- ✅ Add shortcut to desktop

3. **启动 Docker Desktop**

首次启动需要 1-2 分钟，等待右下角任务栏图标显示绿色表示就绪。

4. **验证安装**

打开 PowerShell 或 Git Bash：

```bash
docker --version
docker-compose --version
```

应该看到版本号输出，例如：
```
Docker version 29.4.3, build 055a478
Docker Compose version v5.1.3
```

#### macOS 用户

1. 下载并安装 Docker Desktop for Mac
2. 启动 Docker Desktop，等待状态栏图标显示 "Docker Desktop is running"
3. 在终端验证安装（命令同上）

#### Linux 用户

参考 Docker 官方文档安装 Docker Engine 和 Docker Compose：
https://docs.docker.com/engine/install/

---

## 获取项目代码

### 方法 1：从 GitHub 克隆（推荐）

```bash
# 克隆仓库
git clone https://github.com/ShZhao27208/Aut_Sci_Write.git

# 进入项目目录
cd Aut_Sci_Write

# 查看文件结构
ls -la
```

你应该看到：
```
Dockerfile
docker-compose.yml
docker-entrypoint.sh
requirements.txt
package.json
skills/
data/
...
```

### 方法 2：下载 ZIP 压缩包

1. 访问：https://github.com/ShZhao27208/Aut_Sci_Write
2. 点击绿色 "Code" 按钮 → Download ZIP
3. 解压到本地目录（例如 `D:\Aut_Sci_Write`）

---

## 配置 API 密钥

Docker 容器需要读取 API 密钥才能调用外部服务。

### 创建数据目录

```bash
mkdir -p data/input data/output
```

### 初始化 .env 文件

在项目根目录运行：

```bash
# Windows (PowerShell/Git Bash)
node init-env.js

# 或者通过 Docker 运行（如果本地没有 Node.js）
docker run --rm -v "$(pwd):/app" -w /app node:20 node init-env.js
```

这会在 `skills/sci-search/.env`、`skills/sci-zotero/.env`、`skills/sci-ppt/.env` 等位置创建配置文件模板。

### 填写 API 密钥

#### 1. sci-search（文献检索）

编辑 `skills/sci-search/.env`：

```bash
# Web of Science Starter API（可选，但强烈推荐）
# 免费申请：https://developer.clarivate.com/apis/wos-starter
WOS_API_KEY=你的_WoS_API_密钥

# NCBI PubMed API（可选，提高检索频率限制）
# 申请：https://www.ncbi.nlm.nih.gov/account/settings/
NCBI_API_KEY=你的_NCBI_密钥
NCBI_EMAIL=your.email@example.com
NCBI_TOOL=sci-search
```

#### 2. sci-zotero（文献管理）

编辑 `skills/sci-zotero/.env`：

```bash
# Zotero API 密钥（必填）
# 获取：https://www.zotero.org/settings/keys
ZOTERO_API_KEY=你的_Zotero_API_密钥

# 用户 ID（个人文库）或组 ID（团队文库），二选一
ZOTERO_USER_ID=你的_Zotero_数字用户ID
# ZOTERO_GROUP_ID=团队文库ID
```

**如何获取 Zotero User ID**：
1. 登录 https://www.zotero.org/settings/keys
2. 页面顶部会显示 "Your userID for use in API calls is XXXXXX"

#### 3. sci-ppt（PPT 生成）

编辑 `skills/sci-ppt/.env`：

```bash
# AI 解析 API（用于 PDF 转 PPT 工作流），选择其一即可

# Claude API（推荐）
ANTHROPIC_API_KEY=sk-ant-api03-...


# 或 OpenAI API
OPENAI_API_KEY=sk-...
```

### 安全提示

⚠️ **重要**：
- `.env` 文件包含敏感信息，**切勿提交到 Git 仓库**
- 项目已在 `.gitignore` 中排除 `.env` 文件
- Docker 容器会通过 volume 挂载读取这些文件（不会复制到镜像中）

---

## 构建 Docker 镜像

### 开始构建

在项目根目录运行：

```bash
docker-compose build
```

**预计时间**：首次构建约 5-10 分钟（取决于网络速度和电脑性能）

### 构建过程说明

你会看到类似输出：

```
[+] Building 234.5s (21/21) FINISHED
 => [internal] load build definition from Dockerfile
 => [internal] load .dockerignore
 => [builder 1/6] FROM docker.io/library/python:3.11-slim
 => [builder 2/6] RUN apt-get update && apt-get install...
 => [builder 3/6] RUN curl -fsSL https://deb.nodesource.com/setup_20.x...
 => [builder 4/6] COPY requirements.txt package.json ./
 => [builder 5/6] RUN pip install --no-cache-dir --user -r requirements.txt
 => [builder 6/6] RUN npm install --production
 => [stage-1 1/8] FROM docker.io/library/python:3.11-slim
 => [stage-1 2/8] RUN apt-get update && apt-get install tesseract-ocr...
 => [stage-1 3/8] RUN curl -fsSL https://deb.nodesource.com...
 => [stage-1 4/8] RUN useradd -m -u 1000 scientist...
 => [stage-1 5/8] COPY --from=builder --chown=scientist:scientist /root/.local...
 => [stage-1 6/8] COPY --from=builder --chown=scientist:scientist /build/node_modules...
 => [stage-1 7/8] COPY --chown=scientist:scientist . .
 => [stage-1 8/8] RUN node init-env.js
 => exporting to image
 => => writing image sha256:abc123...
 => => naming to docker.io/library/aut-sci-write:latest
```

### 验证构建结果

```bash
docker images | grep aut-sci-write
```

应该看到：
```
aut-sci-write   latest   abc123def456   2 minutes ago   1.21GB
```

### 构建失败？参考[故障排除](#故障排除)部分

---

## 启动容器

### 启动命令

```bash
docker-compose up -d
```

参数说明：
- `up`：启动服务
- `-d`：后台运行（detached mode）

### 验证启动状态

```bash
docker-compose ps
```

应该看到：
```
NAME                IMAGE                   STATUS
aut-sci-write       aut-sci-write:latest    Up 5 seconds
```

### 查看启动日志

```bash
docker-compose logs
```

你应该看到类似输出：
```
aut-sci-write  | [Aut_Sci_Write] Configuration status:
aut-sci-write  |   ✓ sci-search: WOS_API_KEY configured
aut-sci-write  |   ✓ sci-zotero: ZOTERO_API_KEY configured
aut-sci-write  |   ✓ sci-ppt: ANTHROPIC_API_KEY configured
aut-sci-write  |
aut-sci-write  | [Aut_Sci_Write] Container ready.
```

---

## 使用技能

### 方式 1：进入容器交互式 Shell

```bash
docker-compose exec aut-sci-write bash
```

现在你在容器内部，可以直接运行命令：

```bash
# 示例 1：提取论文核心内容
python scripts/extract_core_insights.py /data/input/paper.pdf

# 示例 2：检索文献
python -m skills.sci_search.cli "perovskite solar cells high efficiency"

# 示例 3：提取图片
python -m skills.sci_figure.cli /data/input/paper.pdf --output /data/output/figures

# 示例 4：生成 PPT
python -m skills.sci_ppt.cli /data/input/paper.pdf --output /data/output/presentation.pptx

# 示例 5：Zotero 操作
python scripts/zotero.py list
python scripts/zotero.py search "machine learning"
```

退出容器：
```bash
exit
```

### 方式 2：从宿主机直接执行命令

不进入容器，直接运行：

```bash
# 提取论文
docker-compose exec aut-sci-write python scripts/extract_core_insights.py /data/input/paper.pdf

# 搜索文献
docker-compose exec aut-sci-write python -m skills.sci_search.cli "solid-state battery"

# 生成 HTML 报告
docker-compose exec aut-sci-write python -m skills.sci_html.cli /data/input/paper.pdf --output /data/output/report.html
```

### 文件路径说明

| 宿主机路径 | 容器内路径 | 用途 |
|-----------|----------|------|
| `./data/input/` | `/data/input/` | 放置输入文件（PDF、文本等） |
| `./data/output/` | `/data/output/` | 生成的输出文件 |
| `./skills/sci-search/.env` | `/app/skills/sci-search/.env` | API 配置（已挂载） |

**工作流程**：
1. 将 PDF 文件放到项目根目录的 `data/input/` 文件夹
2. 在容器内引用路径 `/data/input/xxx.pdf`
3. 输出文件自动保存到 `data/output/`，你可以在宿主机直接访问

---

## 常用操作

### 查看容器状态

```bash
# 查看运行中的容器
docker-compose ps

# 查看容器日志
docker-compose logs -f

# 查看资源占用
docker stats aut-sci-write
```

### 停止和启动

```bash
# 停止容器（不删除）
docker-compose stop

# 启动已停止的容器
docker-compose start

# 停止并删除容器（不删除镜像）
docker-compose down

# 完全删除（包括镜像）
docker-compose down --rmi all
```

### 更新项目

```bash
# 1. 拉取最新代码
git pull

# 2. 重新构建镜像
docker-compose build --no-cache

# 3. 重启容器
docker-compose down
docker-compose up -d
```

### 在容器内安装额外的 Python 包

```bash
docker-compose exec aut-sci-write pip install --user package-name
```

注意：容器重启后这些包会丢失，建议修改 `requirements.txt` 后重新构建镜像。

### 备份和迁移

```bash
# 导出镜像
docker save aut-sci-write:latest | gzip > aut-sci-write.tar.gz

# 在另一台机器上导入
gunzip -c aut-sci-write.tar.gz | docker load
```

---

## 故障排除

### 问题 1：Docker Desktop 无法启动

**症状**：
```
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine
```

**原因**：Docker Desktop 未运行

**解决方案**：
1. Windows：从开始菜单启动 "Docker Desktop"
2. 等待右下角任务栏图标显示绿色
3. 验证：`docker version` 应该同时显示 Client 和 Server 信息

---

### 问题 2：构建时下载超时

**症状**：
```
ERROR [builder 1/6] FROM docker.io/library/python:3.11-slim
failed to solve: failed to fetch ...
```

**原因**：网络问题或 Docker Hub 访问受限

**解决方案**：

#### 方案 A：配置 Docker 镜像加速器（推荐）

编辑 Docker Desktop 设置 → Docker Engine，添加：

```json
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.ccs.tencentyun.com"
  ]
}
```

点击 "Apply & Restart"。

#### 方案 B：使用代理

在 Docker Desktop 设置 → Resources → Proxies 中配置 HTTP/HTTPS 代理。

#### 方案 C：离线构建

如果你有其他机器已构建好镜像：
```bash
# 在已构建的机器上导出
docker save aut-sci-write:latest -o aut-sci-write.tar

# 复制到目标机器后导入
docker load -i aut-sci-write.tar
```

---

### 问题 3：Python 依赖安装失败

**症状**：
```
ERROR: Could not build wheels for opencv-python
```

**原因**：某些 Python 包需要编译，可能缺少系统依赖

**解决方案**：

Dockerfile 已包含必要的编译工具。如果仍失败，尝试：

```dockerfile
# 在 Dockerfile 的 builder 阶段添加更多依赖
RUN apt-get install -y \
    gcc g++ \
    cmake \
    libffi-dev \
    libssl-dev
```

然后重新构建：
```bash
docker-compose build --no-cache
```

---

### 问题 4：权限错误（Linux）

**症状**：
```
Permission denied: '/data/output/result.pdf'
```

**原因**：容器内用户 UID 与宿主机文件所有者不匹配

**解决方案**：

```bash
# 修改 data 目录权限
chmod -R 777 ./data

# 或修改所有者为当前用户
sudo chown -R $(id -u):$(id -g) ./data
```

---

### 问题 5：容器启动后立即退出

**症状**：
```bash
docker-compose ps
# 显示 STATUS 为 Exited
```

**原因**：启动脚本错误或 .env 文件格式问题

**解决方案**：

```bash
# 查看详细日志
docker-compose logs

# 尝试交互式启动以调试
docker-compose run --rm aut-sci-write bash

# 在容器内手动执行 entrypoint
bash /app/docker-entrypoint.sh
```

---

### 问题 6：Tesseract OCR 无法识别中文

**症状**：
提取子图标签时中文识别为乱码

**解决方案**：

容器已包含 `tesseract-ocr-chi-sim`（简体中文），但如果需要繁体中文或其他语言：

修改 Dockerfile：
```dockerfile
RUN apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-chi-sim \
    tesseract-ocr-chi-tra    # 添加繁体中文
```

重新构建镜像。

---

### 问题 7：API 密钥不生效

**症状**：
```
AuthenticationError: Invalid API key
```

**原因**：`.env` 文件格式错误或未正确挂载

**检查步骤**：

1. 验证 `.env` 文件格式（无多余空格、引号）：
```bash
cat skills/sci-zotero/.env
# 应该是：
# ZOTERO_API_KEY=abc123
# 而不是：
# ZOTERO_API_KEY = "abc123"
```

2. 验证文件已挂载到容器：
```bash
docker-compose exec aut-sci-write cat /app/skills/sci-zotero/.env
```

3. 验证容器内环境变量：
```bash
docker-compose exec aut-sci-write env | grep API_KEY
```

---

### 问题 8：磁盘空间不足

**症状**：
```
Error response from daemon: no space left on device
```

**解决方案**：

```bash
# 清理未使用的 Docker 资源
docker system prune -a

# 查看 Docker 占用空间
docker system df

# 删除旧的镜像
docker images
docker rmi <image-id>
```

---

## 与 Claude Code 的关系

### Docker 版本 vs Claude Code Skills

| 对比维度 | Docker 容器 | Claude Code Skills |
|---------|-------------|-------------------|
| **安装方式** | `docker-compose up` | `npx skills add ShZhao27208/Aut_Sci_Write -g` |
| **使用场景** | 命令行批处理、服务器部署 | 与 Claude 对话式交互 |
| **环境依赖** | 自包含，无需本机配置 | 需要本机 Python + Node.js |
| **AI 集成** | 需自己调用 API | 通过 Claude Code 自动激活 |
| **适合人群** | 开发者、批量处理 | 科研人员、交互式使用 |

### 两者可以共存

- **Docker 容器**：用于批量处理文献、在服务器上运行
- **Claude Code Skills**：用于日常与 AI 对话时调用

例如：
1. 平时在 Claude Code 中对话：`"/sci-search 搜索钙钛矿论文"`
2. 需要批量处理 100 篇 PDF 时，切换到 Docker 容器用脚本循环

### 迁移路径

如果你已经通过 `npx skills add` 安装了 Claude Code Skills，现在想用 Docker：

1. **不冲突**：两者使用不同的目录，可以同时保留
2. **配置复用**：可以将 `~/.claude/plugins/*/skills/sci-*/.env` 复制到项目的 `skills/` 目录
3. **数据互通**：将 Docker 的 `./data` 目录挂载到你的工作目录

---

## 进阶配置

### 自定义资源限制

编辑 `docker-compose.yml`：

```yaml
services:
  aut-sci-write:
    deploy:
      resources:
        limits:
          cpus: '2'        # 限制使用 2 核 CPU
          memory: 2G       # 限制内存 2GB
        reservations:
          cpus: '1'
          memory: 1G
```

### 使用外部数据库

如果你有自己的 PostgreSQL/MySQL 数据库存储文献元数据：

```yaml
services:
  aut-sci-write:
    environment:
      - DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

然后在 Python 脚本中使用 `os.getenv('DATABASE_URL')`。

### 集成到 CI/CD

在 GitHub Actions 中使用：

```yaml
name: Process Papers
on: [push]

jobs:
  extract:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker image
        run: docker-compose build
      - name: Extract papers
        run: docker-compose run --rm aut-sci-write python scripts/extract_core_insights.py /data/input/*.pdf
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: extracted-data
          path: data/output/
```

---

## 总结

### 快速参考

```bash
# 克隆项目
git clone https://github.com/ShZhao27208/Aut_Sci_Write.git
cd Aut_Sci_Write

# 配置 API 密钥
node init-env.js
# 编辑 skills/*/.env 文件

# 构建镜像
docker-compose build

# 启动容器
docker-compose up -d

# 使用技能
docker-compose exec aut-sci-write bash
python scripts/extract_core_insights.py /data/input/paper.pdf

# 停止容器
docker-compose down
```

### 获取帮助

- **项目仓库**：https://github.com/ShZhao27208/Aut_Sci_Write
- **提交 Issue**：https://github.com/ShZhao27208/Aut_Sci_Write/issues
- **查看文档**：https://shzhao27208.github.io/Aut_Sci_Write/

---

**文档版本**：1.0  
**最后更新**：2026-06-04  
**适用于**：Aut_Sci_Write v1.4.1 + Docker Compose v2.0+
