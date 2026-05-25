# Windows EXE

打包命令：

```powershell
.\scripts\build-windows-exe.ps1 -Python "C:\Path\To\python.exe" -Npm "C:\Program Files\nodejs\npm.cmd"
```

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
