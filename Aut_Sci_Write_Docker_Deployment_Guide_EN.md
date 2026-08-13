# Aut_Sci_Write Docker Deployment Complete Guide

> This document is for users who want to use the Aut_Sci_Write skill suite through Docker
> 
> Last Updated: 2026-06-04

---

## 📋 Table of Contents

1. [Why Use the Docker Version](#why-use-the-docker-version)
2. [Prerequisites Check](#prerequisites-check)
3. [Get Project Code](#get-project-code)
4. [Configure API Keys](#configure-api-keys)
5. [Build Docker Image](#build-docker-image)
6. [Start Container](#start-container)
7. [Use Skills](#use-skills)
8. [Common Operations](#common-operations)
9. [Troubleshooting](#troubleshooting)
10. [Relationship with Claude Code](#relationship-with-claude-code)

---

## Why Use the Docker Version

### Advantages of Docker Version

| Comparison | Traditional Installation | Docker Installation |
|-----------|-------------------------|-------------------|
| Python Environment | Manual install 3.10+ required | Built-in, no config needed |
| Node.js Environment | Manual install 18+ required | Built-in, no config needed |
| Tesseract OCR | Windows needs manual download and path config | Auto-integrated, out-of-the-box |
| Dependency Conflicts | May conflict with other system projects | Completely isolated |
| System Compatibility | Large differences across Windows/Mac/Linux | Unified environment |
| Deploy to Server | Need to reconfigure environment | Direct image copy |

### Use Cases

✅ **Recommended for Docker**:
- You don't want to install Python/Node.js dev environments locally
- You need to batch process papers on a server
- You've encountered dependency conflicts or version issues
- You want consistent environments across multiple computers

❌ **Not Recommended for Docker**:
- You mainly use it in Claude Code (direct `npx skills add` is more convenient)
- Your computer has limited performance (Docker requires extra overhead)
- You only occasionally use one or two skills

---

## Prerequisites Check

### 1. Check Operating System

Docker Desktop supports:
- **Windows 10/11** Pro/Enterprise/Education (requires WSL2)
- **Windows 10/11** Home (requires WSL2, version 20H1 and above)
- **macOS** 10.15 or higher
- **Linux** mainstream distributions (Ubuntu, Debian, CentOS, etc.)

### 2. Check Hardware Requirements

Minimum configuration:
- **Memory**: 8GB RAM (16GB recommended)
- **Disk**: At least 10GB free space (image ~1.2GB + data space)
- **Processor**: 64-bit processor with virtualization support

### 3. Install Docker Desktop

#### Windows Users

1. **Enable WSL2** (if not already enabled)

Open PowerShell (administrator):

```powershell
wsl --install
```

After restarting, open PowerShell again to verify:

```powershell
wsl -l -v
```

You should see output like:
```
  NAME      STATE           VERSION
* Ubuntu    Running         2
```

2. **Download and Install Docker Desktop**

Visit: https://www.docker.com/products/docker-desktop/

Download the Windows version and install. During installation, select:
- ✅ Use WSL 2 instead of Hyper-V
- ✅ Add shortcut to desktop

3. **Start Docker Desktop**

First launch takes 1-2 minutes. Wait for the taskbar icon to show green indicating ready.

4. **Verify Installation**

Open PowerShell or Git Bash:

```bash
docker --version
docker-compose --version
```

You should see version output, e.g.:
```
Docker version 29.4.3, build 055a478
Docker Compose version v5.1.3
```

#### macOS Users

1. Download and install Docker Desktop for Mac
2. Start Docker Desktop, wait for the status bar icon to show "Docker Desktop is running"
3. Verify installation in terminal (same commands as above)

#### Linux Users

Refer to Docker official documentation to install Docker Engine and Docker Compose:
https://docs.docker.com/engine/install/

---

## Get Project Code

### Method 1: Clone from GitHub (Recommended)

```bash
# Clone repository
git clone https://github.com/ShZhao27208/Aut_Sci_Write.git

# Enter project directory
cd Aut_Sci_Write

# View file structure
ls -la
```

You should see:
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

### Method 2: Download ZIP Archive

1. Visit: https://github.com/ShZhao27208/Aut_Sci_Write
2. Click green "Code" button → Download ZIP
3. Extract to local directory (e.g., `D:\Aut_Sci_Write`)

---

## Configure API Keys

Docker containers need to read API keys to call external services.

### Create Data Directory

```bash
mkdir -p data/input data/output
```

### Initialize .env Files

Run in project root:

```bash
# Windows (PowerShell/Git Bash)
node init-env.js

# Or run through Docker (if you don't have Node.js locally)
docker run --rm -v "$(pwd):/app" -w /app node:20 node init-env.js
```

This creates config file templates at `skills/sci-search/.env`, `skills/sci-zotero/.env`, `skills/sci-ppt/.env`, etc.

### Fill in API Keys

#### 1. sci-search (Literature Search)

Edit `skills/sci-search/.env`:

```bash
# Web of Science Starter API (optional but strongly recommended)
# Free application: https://developer.clarivate.com/apis/wos-starter
WOS_API_KEY=your_WoS_API_key

# NCBI PubMed API (optional, increases search rate limits)
# Apply at: https://www.ncbi.nlm.nih.gov/account/settings/
NCBI_API_KEY=your_NCBI_key
NCBI_EMAIL=your.email@example.com
NCBI_TOOL=sci-search
```

#### 2. sci-zotero (Reference Management)

Edit `skills/sci-zotero/.env`:

```bash
# Zotero API key (required)
# Get at: https://www.zotero.org/settings/keys
ZOTERO_API_KEY=your_Zotero_API_key

# User ID (personal library) or Group ID (team library), choose one
ZOTERO_USER_ID=your_Zotero_numeric_user_ID
# ZOTERO_GROUP_ID=team_library_ID
```

**How to get Zotero User ID**:
1. Login to https://www.zotero.org/settings/keys
2. At the top of the page you'll see "Your userID for use in API calls is XXXXXX"

#### 3. sci-ppt (PPT Generation)

Edit `skills/sci-ppt/.env`:

```bash
# AI parsing API (for PDF to PPT workflow), choose one

# Claude API (recommended)
ANTHROPIC_API_KEY=sk-ant-api03-...


# Or OpenAI API
OPENAI_API_KEY=sk-...
```

### Security Notice

⚠️ **Important**:
- `.env` files contain sensitive information, **never commit to Git repository**
- Project already excludes `.env` files in `.gitignore`
- Docker container reads these files via volume mounts (not copied into image)

---

## Build Docker Image

### Start Build

Run in project root:

```bash
docker-compose build
```

**Expected Time**: First build takes about 5-10 minutes (depending on network speed and computer performance)

### Build Process Description

You'll see output like:

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

### Verify Build Result

```bash
docker images | grep aut-sci-write
```

You should see:
```
aut-sci-write   latest   abc123def456   2 minutes ago   1.21GB
```

### Build Failed? See [Troubleshooting](#troubleshooting) section

---

## Start Container

### Start Command

```bash
docker-compose up -d
```

Parameter explanation:
- `up`: Start service
- `-d`: Run in background (detached mode)

### Verify Startup Status

```bash
docker-compose ps
```

You should see:
```
NAME                IMAGE                   STATUS
aut-sci-write       aut-sci-write:latest    Up 5 seconds
```

### View Startup Logs

```bash
docker-compose logs
```

You should see output like:
```
aut-sci-write  | [Aut_Sci_Write] Configuration status:
aut-sci-write  |   ✓ sci-search: WOS_API_KEY configured
aut-sci-write  |   ✓ sci-zotero: ZOTERO_API_KEY configured
aut-sci-write  |   ✓ sci-ppt: ANTHROPIC_API_KEY configured
aut-sci-write  |
aut-sci-write  | [Aut_Sci_Write] Container ready.
```

---

## Use Skills

### Method 1: Enter Container Interactive Shell

```bash
docker-compose exec aut-sci-write bash
```

Now you're inside the container and can run commands directly:

```bash
# Example 1: Extract paper core content
python scripts/extract_core_insights.py /data/input/paper.pdf

# Example 2: Search literature
python -m skills.sci_search.cli "perovskite solar cells high efficiency"

# Example 3: Extract figures
python -m skills.sci_figure.cli /data/input/paper.pdf --output /data/output/figures

# Example 4: Generate PPT
python -m skills.sci_ppt.cli /data/input/paper.pdf --output /data/output/presentation.pptx

# Example 5: Zotero operations
python scripts/zotero.py list
python scripts/zotero.py search "machine learning"
```

Exit container:
```bash
exit
```

### Method 2: Execute Commands Directly from Host

Without entering container, run directly:

```bash
# Extract paper
docker-compose exec aut-sci-write python scripts/extract_core_insights.py /data/input/paper.pdf

# Search literature
docker-compose exec aut-sci-write python -m skills.sci_search.cli "solid-state battery"

# Generate HTML report
docker-compose exec aut-sci-write python -m skills.sci_html.cli /data/input/paper.pdf --output /data/output/report.html
```

### File Path Description

| Host Path | Container Path | Purpose |
|-----------|---------------|---------|
| `./data/input/` | `/data/input/` | Place input files (PDFs, text, etc.) |
| `./data/output/` | `/data/output/` | Generated output files |
| `./skills/sci-search/.env` | `/app/skills/sci-search/.env` | API config (mounted) |

**Workflow**:
1. Place PDF files in project root's `data/input/` folder
2. Reference path `/data/input/xxx.pdf` in container
3. Output files auto-save to `data/output/`, accessible directly on host

---

## Common Operations

### View Container Status

```bash
# View running containers
docker-compose ps

# View container logs
docker-compose logs -f

# View resource usage
docker stats aut-sci-write
```

### Stop and Start

```bash
# Stop container (don't delete)
docker-compose stop

# Start stopped container
docker-compose start

# Stop and remove container (don't delete image)
docker-compose down

# Complete deletion (including image)
docker-compose down --rmi all
```

### Update Project

```bash
# 1. Pull latest code
git pull

# 2. Rebuild image
docker-compose build --no-cache

# 3. Restart container
docker-compose down
docker-compose up -d
```

### Install Additional Python Packages in Container

```bash
docker-compose exec aut-sci-write pip install --user package-name
```

Note: These packages are lost after container restart. Recommend modifying `requirements.txt` and rebuilding image.

### Backup and Migration

```bash
# Export image
docker save aut-sci-write:latest | gzip > aut-sci-write.tar.gz

# Import on another machine
gunzip -c aut-sci-write.tar.gz | docker load
```

---

## Troubleshooting

### Issue 1: Docker Desktop Won't Start

**Symptom**:
```
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine
```

**Cause**: Docker Desktop not running

**Solution**:
1. Windows: Launch "Docker Desktop" from start menu
2. Wait for taskbar icon to show green
3. Verify: `docker version` should show both Client and Server info

---

### Issue 2: Download Timeout During Build

**Symptom**:
```
ERROR [builder 1/6] FROM docker.io/library/python:3.11-slim
failed to solve: failed to fetch ...
```

**Cause**: Network issues or Docker Hub access restricted

**Solution**:

#### Option A: Configure Docker Registry Mirror (Recommended)

Edit Docker Desktop settings → Docker Engine, add:

```json
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://docker.1panel.live",
    "https://hub.rat.dev"
  ]
}
```

Click "Apply & Restart".

#### Option B: Use Proxy

Configure HTTP/HTTPS proxy in Docker Desktop settings → Resources → Proxies.

#### Option C: Offline Build

If you have the image built on another machine:
```bash
# Export on built machine
docker save aut-sci-write:latest -o aut-sci-write.tar

# Import on target machine after copying
docker load -i aut-sci-write.tar
```

---

### Issue 3: Python Dependency Installation Failed

**Symptom**:
```
ERROR: Could not build wheels for opencv-python
```

**Cause**: Some Python packages need compilation, may lack system dependencies

**Solution**:

Dockerfile already includes necessary compilation tools. If still failing, try:

```dockerfile
# Add more dependencies in Dockerfile builder stage
RUN apt-get install -y \
    gcc g++ \
    cmake \
    libffi-dev \
    libssl-dev
```

Then rebuild:
```bash
docker-compose build --no-cache
```

---

### Issue 4: Permission Error (Linux)

**Symptom**:
```
Permission denied: '/data/output/result.pdf'
```

**Cause**: Container user UID doesn't match host file owner

**Solution**:

```bash
# Fix data directory permissions
chmod -R 777 ./data

# Or change owner to current user
sudo chown -R $(id -u):$(id -g) ./data
```

---

### Issue 5: Container Exits Immediately After Start

**Symptom**:
```bash
docker-compose ps
# Shows STATUS as Exited
```

**Cause**: Startup script error or .env file format issue

**Solution**:

```bash
# View detailed logs
docker-compose logs

# Try interactive start for debugging
docker-compose run --rm aut-sci-write bash

# Manually execute entrypoint in container
bash /app/docker-entrypoint.sh
```

---

### Issue 6: Tesseract OCR Can't Recognize Chinese

**Symptom**:
Chinese characters in sub-figure labels appear as gibberish

**Solution**:

Container already includes `tesseract-ocr-chi-sim` (Simplified Chinese), but if you need Traditional Chinese or other languages:

Modify Dockerfile:
```dockerfile
RUN apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-chi-sim \
    tesseract-ocr-chi-tra    # Add Traditional Chinese
```

Rebuild image.

---

### Issue 7: API Key Not Working

**Symptom**:
```
AuthenticationError: Invalid API key
```

**Cause**: .env file format error or not properly mounted

**Check Steps**:

1. Verify .env file format (no extra spaces, quotes):
```bash
cat skills/sci-zotero/.env
# Should be:
# ZOTERO_API_KEY=abc123
# Not:
# ZOTERO_API_KEY = "abc123"
```

2. Verify file is mounted to container:
```bash
docker-compose exec aut-sci-write cat /app/skills/sci-zotero/.env
```

3. Verify environment variables in container:
```bash
docker-compose exec aut-sci-write env | grep API_KEY
```

---

### Issue 8: Insufficient Disk Space

**Symptom**:
```
Error response from daemon: no space left on device
```

**Solution**:

```bash
# Clean unused Docker resources
docker system prune -a

# View Docker space usage
docker system df

# Delete old images
docker images
docker rmi <image-id>
```

---

## Relationship with Claude Code

### Docker Version vs Claude Code Skills

| Dimension | Docker Container | Claude Code Skills |
|-----------|-----------------|-------------------|
| **Installation** | `docker-compose up` | `npx skills add ShZhao27208/Aut_Sci_Write -g` |
| **Use Case** | Command-line batch processing, server deployment | Conversational interaction with Claude |
| **Environment Dependencies** | Self-contained, no local config needed | Requires local Python + Node.js |
| **AI Integration** | Need to call APIs yourself | Auto-activated through Claude Code |
| **Target Users** | Developers, batch processing | Researchers, interactive use |

### Both Can Coexist

- **Docker Container**: For batch processing papers, running on servers
- **Claude Code Skills**: For daily AI conversations

Example:
1. Normally chat in Claude Code: `"/sci-search search for perovskite papers"`
2. When you need to batch process 100 PDFs, switch to Docker container with a loop script

### Migration Path

If you've already installed Claude Code Skills via `npx skills add` and now want to use Docker:

1. **No conflict**: They use different directories, can keep both
2. **Config reuse**: Can copy `~/.claude/plugins/*/skills/sci-*/.env` to project's `skills/` directory
3. **Data interop**: Mount Docker's `./data` directory to your working directory

---

## Advanced Configuration

### Customize Resource Limits

Edit `docker-compose.yml`:

```yaml
services:
  aut-sci-write:
    deploy:
      resources:
        limits:
          cpus: '2'        # Limit to 2 CPU cores
          memory: 2G       # Limit memory to 2GB
        reservations:
          cpus: '1'
          memory: 1G
```

### Use External Database

If you have your own PostgreSQL/MySQL database to store paper metadata:

```yaml
services:
  aut-sci-write:
    environment:
      - DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

Then use `os.getenv('DATABASE_URL')` in Python scripts.

### Integrate into CI/CD

Use in GitHub Actions:

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

## Summary

### Quick Reference

```bash
# Clone project
git clone https://github.com/ShZhao27208/Aut_Sci_Write.git
cd Aut_Sci_Write

# Configure API keys
node init-env.js
# Edit skills/*/.env files

# Build image
docker-compose build

# Start container
docker-compose up -d

# Use skills
docker-compose exec aut-sci-write bash
python scripts/extract_core_insights.py /data/input/paper.pdf

# Stop container
docker-compose down
```

### Get Help

- **Project Repository**: https://github.com/ShZhao27208/Aut_Sci_Write
- **Submit Issue**: https://github.com/ShZhao27208/Aut_Sci_Write/issues
- **View Documentation**: https://shzhao27208.github.io/Aut_Sci_Write/

---

**Document Version**: 1.0  
**Last Updated**: 2026-06-04  
**Applicable to**: Aut_Sci_Write v1.4.1 + Docker Compose v2.0+
