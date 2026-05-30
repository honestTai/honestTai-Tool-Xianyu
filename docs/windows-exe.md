# Windows EXE

打包命令：

```powershell
.\scripts\build-windows-exe.ps1 -Python "C:\Path\To\python.exe" -Npm "C:\Program Files\nodejs\npm.cmd"
```

生产授权地址可以在打包时内置：

```powershell
.\scripts\build-windows-exe.ps1 `
  -Python "C:\Path\To\python.exe" `
  -Npm "C:\Program Files\nodejs\npm.cmd" `
  -LicenseServerUrl "https://www.javatzt.cn/license" `
  -LicenseClientSecret "honesttai-xianyu-license-client-v1"
```

脚本会生成打包专用 `build\release-env\.env` 并随 exe 一起放入发布目录。程序启动时只在目标目录不存在 `.env` 时复制内置配置，不会覆盖用户后续修改。

输出位置：

```text
release\honestTai-Tool-Xianyu\honestTai-Tool-Xianyu.exe
```

exe 启动后会打开独立的 Windows 桌面窗口，窗口内容由本机内嵌服务提供，不再自动弹出系统浏览器。
运行数据会放在 exe 同目录，例如 `.env`、`logs/`、`data/`、`state/`、`webview-data/`，
方便后续迁移和备份。

如果需要看到控制台日志：

```powershell
.\scripts\build-windows-exe.ps1 -Console
```

如果旧 `release` 目录被正在运行的程序占用，可以把调试包输出到独立目录：

```powershell
.\scripts\build-windows-exe.ps1 -Console -DistPath release-debug
```

## Windows 安装包

需要先安装 [Inno Setup 6](https://jrsoftware.org/isinfo.php)，然后执行：

```powershell
.\scripts\build-windows-installer.ps1 `
  -Python "C:\Path\To\python.exe" `
  -Npm "C:\Program Files\nodejs\npm.cmd" `
  -LicenseServerUrl "https://www.javatzt.cn/license"
```

输出位置：

```text
release\installer\honestTai-Tool-Xianyu-Setup.exe
```

安装包会把 exe、前端静态资源、授权配置和运行资源一起安装到用户目录，用户只需要拿到这个 `Setup.exe`，不需要手动携带 `.env` 或资源文件。
