import threading
import os
import sys
import time
import re
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from pathlib import Path

import os
import sys

if getattr(sys, "frozen", False):
    browser_path = Path(sys.executable).resolve().parent / "ms-playwright"
    if browser_path.is_dir():
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browser_path)

URL = "https://order-tyb.stdu.edu.cn/wxh5/book?type=1"

# PyInstaller 发布版从 EXE 同目录加载随包携带的 Chromium；源码运行时使用 Playwright 默认缓存。
if getattr(sys, "frozen", False):
    bundled_browser = Path(sys.executable).resolve().parent / "ms-playwright"
    if bundled_browser.exists():
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(bundled_browser)

class Assistant:
    def __init__(self, root):
        self.root = root
        self.root.title("STDU 羽毛球智能预约助手")
        self.root.geometry("560x650")
        self.root.resizable(False, False)
        self.browser = None
        self.page = None
        self.context = None
        self.worker = None
        self.stop_event = threading.Event()
        self.run_at = None
        self.job_args = None
        self._build()

    def _build(self):
        pad = {"padx": 12, "pady": 5}
        frm = ttk.Frame(self.root, padding=12)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="STDU 羽毛球智能预约助手", font=("Microsoft YaHei UI", 16, "bold")).pack(anchor="w", **pad)
        ttk.Label(frm, text="只选择绿色「可约」；最多4个半小时段。首次使用请先登录并在网页上选好预约日期。", wraplength=510).pack(anchor="w", **pad)

        grid = ttk.Frame(frm); grid.pack(fill="x", **pad)
        self.vars = {}
        fields = [
            ("预约日期（网页上也要选同一天）", "date", datetime.now().strftime("%Y-%m-%d")),
            ("场地（1—10）", "venue", "10"),
            ("开始时间", "start", "18:00"),
            ("结束时间（不含该时刻）", "end", "20:00"),
            ("自动执行日期", "run_date", datetime.now().strftime("%Y-%m-%d")),
            ("自动执行时间（本机时间，HH:MM:SS）", "run_time", "19:59:55"),
        ]
        for r, (label, key, default) in enumerate(fields):
            ttk.Label(grid, text=label).grid(row=r, column=0, sticky="w", pady=5)
            var = tk.StringVar(value=default); self.vars[key] = var
            ent = ttk.Entry(grid, textvariable=var, width=24)
            ent.grid(row=r, column=1, sticky="ew", padx=8, pady=5)
        grid.columnconfigure(1, weight=1)

        self.date_ready = tk.BooleanVar(value=False)
        ttk.Checkbutton(frm, text="我已在学校网页中登录，并手动切换到上面填写的预约日期", variable=self.date_ready).pack(anchor="w", **pad)
        btns = ttk.Frame(frm); btns.pack(fill="x", **pad)
        ttk.Button(btns, text="打开学校预约网页", command=self.open_site).pack(side="left", padx=4)
        ttk.Button(btns, text="开始定时预约", command=self.start).pack(side="left", padx=4)
        ttk.Button(btns, text="停止任务", command=self.stop).pack(side="left", padx=4)
        ttk.Label(frm, text="运行日志", font=("Microsoft YaHei UI", 11, "bold")).pack(anchor="w", **pad)
        self.logbox = tk.Text(frm, height=15, wrap="word", state="disabled")
        self.logbox.pack(fill="both", expand=True, padx=12, pady=5)
        self.log("提示：当前版本已按你提供的 DOM 类名编写，但尚未在学校网站实测。首次运行请先用测试时段验证，不要直接设置正式抢约。")

    def log(self, msg):
        stamp = datetime.now().strftime("%H:%M:%S")
        def write():
            self.logbox.configure(state="normal")
            self.logbox.insert("end", f"[{stamp}] {msg}\n")
            self.logbox.see("end")
            self.logbox.configure(state="disabled")
        self.root.after(0, write)

    def open_site(self):
        self._open_browser()

    def _open_browser(self):
        try:
            from playwright.sync_api import sync_playwright
            if self.context and self.page:
                self.page.bring_to_front(); return
            self.pw = sync_playwright().start()
            profile = Path.home() / ".stdu_badminton_browser_profile"
            self.context = self.pw.chromium.launch_persistent_context(
                user_data_dir=str(profile), headless=False, viewport={"width": 1440, "height": 900}
            )
            self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
            self.page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            self.log("预约网页已打开。请在浏览器内登录，并手动切换到目标预约日期。")
        except Exception as e:
            self.log(f"打开网页失败：{e}")
            self.log("请先运行安装依赖.bat，再重新打开程序。")

    def _parse_time(self, value):
        if not re.fullmatch(r"\d{2}:\d{2}", value):
            raise ValueError(f"时间格式错误：{value}，应为 HH:MM")
        h, m = map(int, value.split(":"))
        if m not in (0, 30) or h < 8 or h > 21 or (h == 21 and m != 0):
            raise ValueError("预约时间须在08:00至21:30之间，且按30分钟递增")
        return h * 60 + m

    def _validate(self):
        v = {k: x.get().strip() for k, x in self.vars.items()}
        datetime.strptime(v["date"], "%Y-%m-%d")
        datetime.strptime(v["run_date"], "%Y-%m-%d")
        if not v["venue"].isdigit() or not 1 <= int(v["venue"]) <= 10:
            raise ValueError("场地编号必须是1—10")
        start, end = self._parse_time(v["start"]), self._parse_time(v["end"])
        if end <= start or (end-start) % 30:
            raise ValueError("结束时间必须晚于开始时间，并按半小时递增")
        count = (end-start)//30
        if count > 4:
            raise ValueError("网站最多选择4个时段，请把预约时长控制在2小时以内")
        run_at = datetime.strptime(v["run_date"] + " " + v["run_time"], "%Y-%m-%d %H:%M:%S")
        if run_at <= datetime.now():
            raise ValueError("自动执行时间必须晚于当前电脑时间")
        return v, start, end, run_at

    def start(self):
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("提示", "任务已经在运行")
            return
        if not self.date_ready.get():
            messagebox.showwarning("还差一步", "请先打开网页、登录，并手动切换到目标预约日期，然后勾选确认框。")
            return
        try:
            v, start, end, run_at = self._validate()
        except Exception as e:
            messagebox.showerror("参数错误", str(e)); return
        if not self.page:
            messagebox.showwarning("网页未打开", "请先点击「打开学校预约网页」并完成登录。"); return
        if not messagebox.askyesno("确认预约设置", f"预约日期：{v['date']}\n场地：{v['venue']}号场\n时段：{v['start']}—{v['end']}（{(end-start)//30}个半小时段）\n自动执行：{run_at}\n\n确认网页已经切换到目标日期？"):
            return
        self.stop_event.clear()
        self.job_args = (v, start, end)
        self.run_at = run_at
        self.log(f"定时任务已启动，等待至 {run_at}（电脑本地时间）。")
        self.root.after(100, self._scheduled_tick)

    def stop(self):
        self.stop_event.set(); self.log("已请求停止任务。")

    def _scheduled_tick(self):
        if self.stop_event.is_set():
            self.log("定时任务已停止。")
            return
        if datetime.now() < self.run_at:
            self.root.after(100, self._scheduled_tick)
            return
        self._execute_job(*self.job_args)

    def _execute_job(self, v, start, end):
        try:
            page = self.page
            page.bring_to_front()
            # Find the venue column by its exact displayed name.
            venue_name = f"羽毛球{v['venue']}号场"
            columns = page.locator(".venue-column").filter(has=page.locator(".venue-name", has_text=venue_name))
            if columns.count() != 1:
                raise RuntimeError(f"没有唯一找到{venue_name}，请确认网页已加载且日期正确。")
            column = columns.first
            slots = column.locator(".slot.matrix-slot")
            first_index = (start - 8*60)//30
            last_index = (end - 8*60)//30
            if slots.count() <= last_index-1:
                raise RuntimeError(f"场地时段数量不足：页面识别到{slots.count()}格，目标索引为{last_index-1}。")
            for idx in range(first_index, last_index):
                if self.stop_event.is_set(): return
                cell = slots.nth(idx)
                cls = (cell.get_attribute("class") or "").split()
                label = (cell.inner_text() or "").strip()
                if "selected" in cls and "已选" in label:
                    self.log(f"目标第{idx+1}格已处于选中状态，跳过。")
                    continue
                if "free" not in cls or label != "可约":
                    raise RuntimeError(f"目标时段序号{idx+1}不是绿色可约（当前：{label or cls}），为防止误订，已停止。")
                cell.click()
                page.wait_for_timeout(250)
                new_cls = (cell.get_attribute("class") or "").split()
                new_label = (cell.inner_text() or "").strip()
                if "selected" not in new_cls or "已选" not in new_label:
                    raise RuntimeError(f"时段序号{idx+1}点击后未变成蓝色已选，已停止。")
                self.log(f"已选中目标时段序号{idx+1}。")
            if self.stop_event.is_set(): return
            # Submit only the clearly labeled confirmation control.
            submit = page.get_by_role("button", name=re.compile(r"^确认提交$"))
            if submit.count() == 0:
                submit = page.get_by_text("确认提交", exact=True)
            if submit.count() != 1:
                raise RuntimeError("没有唯一找到「确认提交」按钮；为避免误点，未提交。")
            submit.click()
            page.wait_for_timeout(1800)
            body = page.locator("body").inner_text()
            if re.search(r"预约成功|提交成功|预订成功", body):
                self.log("网站页面出现成功提示：预约成功。请再核对订单记录。")
            else:
                self.log("已点击确认提交，但页面未检测到明确成功提示。请立即查看网页结果/订单记录，勿重复提交。")
        except Exception as e:
            self.log(f"任务停止：{e}")

if __name__ == "__main__":
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except Exception:
        pass
    app = Assistant(root)
    root.mainloop()
