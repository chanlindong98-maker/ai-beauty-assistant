# 魅丽健康助手 - 部署指南

本文档介绍如何部署和运行魅丽健康助手的前后端服务。

## 前置要求

1. **Node.js** >= 18.0
2. **Python** >= 3.10
3. **Supabase 项目**（已创建）
4. **Google Gemini API Key**

---

## 第一步：配置 Supabase 数据库

1. 登录 [Supabase Dashboard](https://supabase.com/dashboard)
2. 进入您的项目
3. 点击左侧菜单 **SQL Editor**
4. 复制 `database/init.sql` 的内容并执行
5. 确认表创建成功（在 **Table Editor** 中查看）

---

## 第二步：配置后端

### 2.1 创建环境变量文件

```bash
cd backend
copy .env.example .env
```

### 2.2 编辑 `.env` 文件

填入您的真实配置：

```env
# Supabase 配置（从 Project Settings → API 获取）
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIs...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIs...

# Gemini API Key
GEMINI_API_KEY=AIza...

# 应用配置
DEBUG=true
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
```

### 2.3 安装依赖并启动

```bash
# 创建虚拟环境（推荐）
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

后端服务将在 http://localhost:8000 启动。

访问 http://localhost:8000/docs 可查看 API 文档。

---

## 第三步：配置前端

### 3.1 编辑 `.env.local` 文件

```env
# Supabase 配置
VITE_SUPABASE_URL=https://xxxxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIs...

# 后端 API 地址
VITE_API_BASE_URL=http://localhost:8000
```

### 3.2 安装依赖并启动

```bash
# 在项目根目录
npm install

# 启动开发服务器
npm run dev
```

前端将在 http://localhost:5173 启动。

---

## 验证部署

1. 打开浏览器访问 http://localhost:5173
2. 点击"个人中心"
3. 注册一个新账号
4. 检查是否获得 3 次魔法值
5. 尝试使用"云试衣"功能
6. 确认魔法值正确扣减

---

## 项目结构

```
ai-魅丽健康助手/
├── App.tsx                 # 前端主组件
├── services/
│   ├── api.ts              # 后端 API 服务
│   ├── supabaseClient.ts   # Supabase 客户端
│   └── geminiService.ts    # （已废弃，改用后端）
├── backend/                # 后端服务
│   ├── main.py             # FastAPI 入口
│   ├── config.py           # 配置管理
│   ├── api/                # API 路由
│   ├── services/           # 业务服务
│   ├── schemas/            # 数据模型
│   └── middleware/         # 中间件
└── database/
    └── init.sql            # 数据库初始化脚本
```

---

## 常见问题

### Q: 后端启动报错 "ModuleNotFoundError"
A: 确保已安装所有依赖：`pip install -r requirements.txt`

### Q: 前端提示 "CORS error"
A: 检查后端 `.env` 中的 `CORS_ORIGINS` 是否包含前端地址

### Q: 注册时提示 "用户名已存在"
A: 用户名用于生成邮箱地址，请使用唯一的用户名

### Q: AI 功能返回错误
A: 检查后端日志和 Gemini API Key 是否正确配置
