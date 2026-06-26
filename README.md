# GitLab → 企业微信机器人 中转服务

接收 GitLab webhook，翻译成企业微信 markdown 消息，推送到企业微信群机器人。

## 功能

- ✅ 支持多种 GitLab 事件：push、merge_request、tag_push、note、pipeline、wiki、build
- ✅ 一个 GitLab webhook 地址对应一个企微机器人
- ✅ Web 管理页面，可视化配置映射关系
- ✅ 事件过滤，可指定只接收某些事件类型
- ✅ 推送日志，方便排查问题
- ✅ 测试功能，一键验证企微连通性
- ✅ SQLite 存储，轻量无依赖
- ✅ Docker 一键部署

## 快速开始

### 方式一：Docker 部署（推荐）

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f
```

访问 `http://服务器IP:5000` 进入管理页面。

### 方式二：直接运行

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python app.py
```

### 方式三：systemd 服务

```bash
# 复制服务文件
sudo cp deploy/gitlab-wechat-bot.service /etc/systemd/system/

# 编辑配置
sudo vim /etc/systemd/system/gitlab-wechat-bot.service

# 启动
sudo systemctl enable gitlab-wechat-bot
sudo systemctl start gitlab-wechat-bot
```

## 使用步骤

1. 访问 `http://服务器:5000/` 打开管理页面
2. 点击"添加"，填写：
   - **备注名称**：方便识别，如"主仓库→测试群"
   - **企微 Webhook URL**：企业微信群机器人的完整地址
   - **监听事件**：`*` 表示全部，或指定如 `push,merge_request,pipeline`
3. 复制生成的 Webhook 地址（格式：`http://服务器:5000/webhook/xxx`）
4. 在 GitLab 项目中配置：
   - 进入项目 → Settings → Webhooks
   - 粘贴上面的地址
   - 勾选需要的事件类型
   - 点击 "Add webhook"
5. 回到管理页面，点击"测试"验证企微是否收到消息

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PORT` | `5000` | 服务端口 |
| `DB_PATH` | `./data/webhooks.db` | SQLite 数据库路径 |
| `LOG_RETAIN_DAYS` | `30` | 日志保留天数 |

## 消息格式示例

**代码推送：**
```
[代码推送] my-project
分支: main
提交者: zhangsan
提交数: 3

- abc12345 修复登录bug
- def67890 更新README

查看仓库
```

**合并请求：**
```
[合并请求] 添加用户模块
操作: 发起
分支: feature/user → main
操作者: lisi
状态: opened

查看详情
```

**流水线：**
```
[流水线] my-project #123
状态: ❌ failed
分支: main
触发者: wangwu

失败阶段:
- test (test)
- deploy (deploy)

查看详情
```

## 项目结构

```
GitLabToWechatBot/
├── app.py              # 主入口
├── config.py           # 配置
├── models.py           # 数据库
├── handlers/
│   ├── gitlab.py       # GitLab 事件解析
│   └── wechat.py       # 企微消息发送
├── templates/          # 页面模板
├── static/             # 静态资源
├── data/               # 数据目录（SQLite）
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## 反向代理（Nginx）

如果需要通过 Nginx 反向代理：

```nginx
server {
    listen 80;
    server_name gitlab-bot.example.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```
