# STDU 羽毛球预约助手（Windows x64 构建项目）

本项目通过 GitHub Actions 的 Windows runner 构建，不要求使用者本机安装 Python。

## 生成 EXE
1. 在 GitHub 新建一个空仓库，将本目录中的全部文件上传（包括 `.github/workflows/build-windows.yml`）。
2. 打开仓库的 **Actions** 页面，选择 **Build Windows EXE**。
3. 点击 **Run workflow**，等待任务完成且显示绿色成功状态。
4. 在该次运行页面底部的 **Artifacts** 下载 `STDU羽毛球预约助手-Windows-x64`。
5. 解压 ZIP，双击文件夹内 `STDU羽毛球智能预约助手.exe`。

这是 onedir 便携版：EXE 需要与同目录的 `_internal`、`ms-playwright` 等文件夹放在一起，不能单独把 EXE 拿出来运行。整个解压后的文件夹可复制到其他 Windows 11 x64 电脑，不需要安装 Python。

## 重要说明
- 首次运行需在程序打开的学校网页中自行登录，并手动切换到与程序填写日期一致的预约日期。
- 定时预约依赖电脑开机、程序运行、网络正常且登录状态有效。
- 当前自动选择逻辑按用户提供的 DOM 类名编写，尚未在学校网站实测；请先用非关键时段验证。
- 提交后程序只根据页面文字检测成功提示；未检测到时请核对订单记录，不要盲目重复提交。
