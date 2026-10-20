# IBD Spider — macOS 打包操作手册

> 本文档只讲 **在 Mac 上怎么把项目打成 .app**。Windows 打包流程不受影响，继续用原来的 `IBDspider.spec`。

---

## 一、前置条件

| 项目 | 要求 |
|------|------|
| 操作系统 | macOS 11 (Big Sur) 及以上 |
| Python | 3.10 / 3.11 / 3.12（**不要用 3.13**，PyQt6-WebEngine 尚未支持） |
| 架构 | Apple Silicon (M系列) 或 Intel 均可 |
| 磁盘 | 预留 3GB 以上 |

检查 Python 版本：

```bash
python3 --version
```

如果版本不对，用 Homebrew 装指定版本：

```bash
brew install python@3.12
```

---

## 二、首次打包

### 1. 进入项目目录

```bash
cd "/路径/IBDspider-PlanTwo (注释正式版-MAC适配版)"
```

### 2. 创建虚拟环境（强烈建议）

```bash
python3.12 -m venv venv
source venv/bin/activate
```

> 看到命令行前面出现 `(venv)` 就说明激活成功。

### 3. 安装依赖

```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
```

### 4. 先跑一次源码，确认能启动

```bash
python main.py
```

能弹出窗口、内嵌浏览器能加载 DeepSeek 页面，说明环境 OK。**这一步必须先过，否则打包出来也是坏的。**

按 `Ctrl+C` 或关闭窗口退出。

### 5. 打包

```bash
pyinstaller IBDspider_mac.spec --noconfirm
```

首次打包约 3~8 分钟。成功后会看到：

```
dist/IBD Spider.app
```

### 6. 运行

```bash
open "dist/IBD Spider.app"
```

---

## 三、打包后的产物结构

```
dist/
└── IBD Spider.app          ← 双击就能运行的 App
build/                       ← 中间文件，可删
```

分发时只需要把 `IBD Spider.app` 压缩成 zip 或打成 dmg 发给别人。

---

## 四、常见问题

### Q1: 打开时提示「无法打开，因为无法验证开发者」

这是 macOS 的 Gatekeeper 拦截，属于**正常现象**（因为没做代码签名）。

**临时解决（自己用）**：右键点 App → 选「打开」→ 弹窗再点「打开」。

**命令行解除隔离**：

```bash
xattr -cr "dist/IBD Spider.app"
```

**彻底解决（分发给别人）**：需要 Apple 开发者账号，做代码签名 + 公证，见第五节。

### Q2: 启动就闪退，看不到任何报错

用终端启动，才能看到真实报错：

```bash
"dist/IBD Spider.app/Contents/MacOS/IBD Spider"
```

常见原因：

| 报错 | 原因 | 解决 |
|------|------|------|
| `No module named 'PyQt6.QtWebEngineCore'` | 缺 hiddenimport | 检查 spec 的 `hiddenimports` 是否包含它 |
| `win32api` / `pywintypes` 相关 | win32 依赖没排干净 | 检查 spec 的 `excludes` |
| `mian.ico not found` | 图标没打进去 | 确认 `datas` 里有 `('mian.ico', '.')` |
| 空白窗口 / 浏览器不出来 | QtWebEngine 进程被拦 | 在「系统设置 → 隐私与安全性」中允许 |

### Q3: 打包很慢 / 产物特别大（超过 300MB）

PyQt6 + QtWebEngine 本身就大，200~400MB 是正常范围。

想瘦身可以在 spec 的 `excludes` 里继续排除不用的 Qt 模块（如 `PyQt6.QtQuick`、`PyQt6.QtQml`、`PyQt6.Qt3D*`），但**不要动 QtWebEngine 相关**。

### Q4: 想在 M 系列和 Intel 上都能跑

`target_arch=None` 表示「按当前 Python 解释器的架构打包」。

- 在 M 系列 Mac 上打包 → 只能 M 系列跑（arm64）
- 在 Intel Mac 上打包 → 只能 Intel 跑（x86_64）
- **都要支持**：装 universal2 版本的 Python，或分别在两种机器上各打一次

### Q5: 内嵌浏览器的登录状态丢失

网页数据存在：

```
~/Library/Application Support/IBD Spider/  （或 QtWebEngine 默认目录）
```

打包后 App 的沙盒路径可能变，首次运行重新登录 DeepSeek / 公众号后台即可。

---

## 五、代码签名 + 公证（可选，对外分发才需要）

需要 **Apple Developer Program**（每年 $99）。

### 1. 查看可用的签名证书

```bash
security find-identity -v -p codesigning
```

### 2. 签名 App

```bash
codesign --deep --force --options runtime \
  --sign "Developer ID Application: 你的名字 (TEAMID)" \
  "dist/IBD Spider.app"
```

### 3. 打包成 dmg（可选）

```bash
hdiutil create -volname "IBD Spider" -srcfolder "dist/IBD Spider.app" -ov -format UDZO "IBD Spider.dmg"
```

### 4. 提交公证

```bash
xcrun notarytool submit "IBD Spider.dmg" \
  --apple-id "你的AppleID" \
  --team-id "TEAMID" \
  --password "App专用密码" \
  --wait
```

### 5. 装订公证结果

```bash
xcrun stapler staple "IBD Spider.dmg"
```

---

## 六、本机（Windows）已完成的适配改动

| 文件 | 改动 |
|------|------|
| `main.py` | 字体按平台自适应：Windows→Microsoft YaHei，macOS→PingFang SC |
| `main_window.py` | 无改动。深色标题栏已有 `if sys.platform == "win32"` 保护，macOS 自动跳过 |
| `ipo_panel.py` / `wechat_panel.py` | 无改动。打开文件夹已同时支持 win32 / darwin / linux |
| `IBDspider_mac.spec` | 新增，macOS 专用打包配置 |
| `requirements.txt` | 新增，依赖清单 |

**结论：Windows 上的行为和打包流程完全不受影响。**

---

## 六·五、没有 Mac？用 GitHub Actions 云端打包

> 这是**不需要自己有 Mac** 的方案。GitHub 免费提供 macOS 云机器，push 代码后自动出包。

### 已备好的文件

| 文件 | 作用 |
|------|------|
| `.github/workflows/build-mac.yml` | 打包流水线，在 macOS 云机器上自动跑 |
| `.gitignore` | 排除 build/dist/缓存/业务数据，避免把几百MB垃圾推上仓库 |

### 操作步骤

**1. 在 GitHub 建一个仓库**（新建 → 选 Private 或 Public 都行，不要勾选任何模板）

**2. 把本地代码推上去**

在项目文件夹里打开终端：

```bash
git init
git add .
git commit -m "init: IBD Spider macOS 适配版"
git branch -M main
git remote add origin https://github.com/你的用户名/仓库名.git
git push -u origin main
```

> 第一次 push 会要求登录，用 GitHub 的 Personal Access Token 代替密码（Settings → Developer settings → Personal access tokens）。

**3. 触发打包**

进 GitHub 仓库页面 → 顶部 **Actions** 标签 → 左侧选 **Build macOS App** → 右侧 **Run workflow** → 点绿色按钮。

或者打个 tag 自动触发：

```bash
git tag v2.0.0
git push origin v2.0.0
```

**4. 下载产物**

等 5~10 分钟，Actions 里那次运行变成绿色对勾后，点进去 → 页面底部 **Artifacts** → 下载 `IBD-Spider-mac.zip`。

解压得到 `IBD Spider.app`，拖到「应用程序」文件夹即可。

### 关于免费额度

| 仓库类型 | macOS 分钟数 |
|---------|-------------|
| Public（公开） | **完全免费，无限** |
| Private（私有） | 每月 2000 分钟免费，macOS 按 10 倍计费，约 200 分钟/月 |

> 一次打包约消耗 8~10 分钟，私有仓库每月约能打 20 次。够用的话就私有，不够就转公开。

### ⚠️ 图标注意

macOS 的 App 图标需要 `.icns` 格式，项目现在是 `.ico`。PyInstaller 在 macOS 上会**忽略 ico 并用默认图标**（不影响功能，只是图标不好看）。

要自定义图标，需在 Mac 上转换：

```bash
# 在 Mac 上用 iconutil 或在线工具把 png 转成 icns，然后改 spec 的 icon 指向 .icns
icon='mian.icns'
```

先跑通，图标可后续再优化。

---

## 七、验证清单

打包成功后，按顺序确认：

- [ ] App 能正常启动，不闪退
- [ ] 主窗口标题栏显示「IBD Spider v2.0 - 金融数据集成工具」
- [ ] 中文字体显示正常（不是方块乱码）
- [ ] 内嵌浏览器能加载 `https://chat.deepseek.com/`
- [ ] 四个功能面板都能切换
- [ ] 港股/美股/IPO 面板填写参数不报错
- [ ] 公众号面板能点「开始」
- [ ] 任务完成后能自动/手动打开 results 文件夹

全部通过就说明打包成功。
