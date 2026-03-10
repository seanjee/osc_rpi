~/.config/systemd/user/rpiosc.service

1) 先确认启动命令
你现在手动能跑的命令一般是：

cd /home/sean/osc_rpi && PYTHONPATH=src python -m rpiosc.app
如果你需要 X11/Wayland 图形界面，必须在“图形会话已登录”后启动（systemd user service 正是这样）。

2) 创建 systemd 用户服务
创建文件：

~/.config/systemd/user/rpiosc.service
内容示例（按你当前路径写死，最简单可靠）：

3) 启用并启动
执行：

systemctl --user daemon-reload
systemctl --user enable rpiosc.service
systemctl --user start rpiosc.service
查看日志（排障用）：

journalctl --user -u rpiosc.service -f
4) 确保“自动登录”已开启
如果你用的是 GNOME（Ubuntu 默认），在登录界面设置里开启自动登录；或编辑：

custom.conf（需要 sudo）
把对应用户的 AutomaticLoginEnable=true、AutomaticLogin=sean 打开。
如果你告诉我你用的是 GDM / LightDM / SDDM 哪个登录管理器，我可以给你最准确的自动登录配置位置。

你希望它“在桌面加载完成后再启动”（更稳），还是“只要登录就立刻起”（更快）？我可以把 service 的 After= 调得更贴合你的桌面环境。