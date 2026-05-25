# Windows EXE

打包命令：

```powershell
.\scripts\build-windows-exe.ps1 -Python "C:\Path\To\python.exe" -Npm "C:\Program Files\nodejs\npm.cmd"
```

输出位置：

```text
dist\honestTai-Tool-Xianyu\honestTai-Tool-Xianyu.exe
```

exe 启动后会在本机打开 Web GUI，并把 `.env`、`logs/`、`data/`、`state/`
等运行数据放在 exe 同目录，方便后续迁移和备份。

如果需要看到控制台日志：

```powershell
.\scripts\build-windows-exe.ps1 -Console
```
