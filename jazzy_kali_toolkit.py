#!/usr/bin/env python3
"""
Jazzy Kali Toolkit — existing Kali tools ke liye GUI frontend.
Nmap, WiFi audit (aircrack-ng suite), aur Metasploit ko button-click pe chalao.

Usage: sudo python3 jazzy_kali_toolkit.py
(Monitor mode aur kuch scans ke liye root chahiye)

Sirf apne lab / apne network pe use karo.
"""

import subprocess
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import shutil
import re

# ---------- Theme ----------
BG = "#0d1117"
PANEL = "#161b22"
GREEN = "#00ff41"
DIM = "#8b949e"
TEXT = "#e6edf3"
RED = "#ff3131"
AMBER = "#ffb300"
FONT = ("Consolas", 10)
FONT_BIG = ("Consolas", 11, "bold")


def tool_exists(name):
    return shutil.which(name) is not None


class ToolTab(ttk.Frame):
    """Har tab ka base: output window + run/stop."""

    def __init__(self, parent):
        super().__init__(parent)
        self.proc = None
        self._build_output()

    def _build_output(self):
        out_frame = ttk.Frame(self)
        out_frame.pack(fill="both", expand=True, padx=8, pady=8)

        btn_row = ttk.Frame(out_frame)
        btn_row.pack(fill="x", pady=(0, 4))
        self.run_btn = tk.Button(btn_row, text="▶ Run", bg=GREEN, fg="black",
                                 font=FONT_BIG, relief="flat", padx=12,
                                 command=self.on_run)
        self.run_btn.pack(side="left")
        self.stop_btn = tk.Button(btn_row, text="■ Stop", bg=RED, fg="white",
                                  font=FONT_BIG, relief="flat", padx=12,
                                  command=self.stop, state="disabled")
        self.stop_btn.pack(side="left", padx=8)
        self.clear_btn = tk.Button(btn_row, text="Clear", bg=PANEL, fg=TEXT,
                                   font=FONT, relief="flat",
                                   command=self.clear_output)
        self.clear_btn.pack(side="left")

        self.output = scrolledtext.ScrolledText(
            out_frame, bg="black", fg=GREEN, font=FONT,
            insertbackground=GREEN, wrap="word")
        self.output.pack(fill="both", expand=True)

    def log(self, text):
        self.output.insert("end", text)
        self.output.see("end")

    def clear_output(self):
        self.output.delete("1.0", "end")

    def on_run(self):
        cmd = self.build_command()
        if not cmd:
            return
        self.clear_output()
        self.log(f"$ {' '.join(cmd)}\n{'-'*50}\n")
        self.run_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        threading.Thread(target=self._run, args=(cmd,), daemon=True).start()

    def _run(self, cmd):
        try:
            self.proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1)
            for line in self.proc.stdout:
                self.log(line)
            self.proc.wait()
            self.log(f"\n{'-'*50}\n[Done, exit={self.proc.returncode}]\n")
        except FileNotFoundError:
            self.log(f"\n[ERROR] Tool nahi mila: {cmd[0]} — Kali me installed hai?\n")
        except Exception as e:
            self.log(f"\n[ERROR] {e}\n")
        finally:
            self.proc = None
            self.after(0, self._run_done)

    def _run_done(self):
        self.run_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

    def stop(self):
        if self.proc:
            self.proc.terminate()
            self.log("\n[Stopped by user]\n")

    def build_command(self):
        raise NotImplementedError


# ================= NMAP TAB =================
class NmapTab(ToolTab):
    def __init__(self, parent):
        self.target_var = tk.StringVar(value="192.168.1.1")
        self.profile_var = tk.StringVar(value="Quick scan")
        super().__init__(parent)
        if not tool_exists("nmap"):
            self.log("[WARNING] nmap nahi mila!\n")

    def _build_output(self):
        # Input row pehle, phir base ka output
        inp = ttk.Frame(self)
        inp.pack(fill="x", padx=8, pady=(8, 0))

        tk.Label(inp, text="Target:", bg=BG, fg=TEXT, font=FONT).pack(side="left")
        tk.Entry(inp, textvariable=self.target_var, bg=PANEL, fg=TEXT,
                 font=FONT, width=22, insertbackground=GREEN).pack(side="left", padx=6)

        tk.Label(inp, text="Scan:", bg=BG, fg=TEXT, font=FONT).pack(side="left")
        profiles = ["Quick scan", "Full ports", "OS detect",
                    "Service versions", "Aggressive", "Ping only"]
        ttk.Combobox(inp, textvariable=self.profile_var, values=profiles,
                     width=16, state="readonly").pack(side="left", padx=6)

        super()._build_output()

    def build_command(self):
        target = self.target_var.get().strip()
        if not target:
            messagebox.showwarning("Target?", "Target IP/hostname daalo pehle!")
            return None
        p = self.profile_var.get()
        base = ["nmap"]
        if p == "Quick scan":
            base += ["-F", target]
        elif p == "Full ports":
            base += ["-p-", target]
        elif p == "OS detect":
            base += ["-O", target]
        elif p == "Service versions":
            base += ["-sV", target]
        elif p == "Aggressive":
            base += ["-A", target]
        elif p == "Ping only":
            base += ["-sn", target]
        return base


# ================= WIFI TAB =================
class WifiTab(ToolTab):
    def __init__(self, parent):
        self.iface_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="Scan networks")
        super().__init__(parent)
        for t in ("airmon-ng", "airodump-ng"):
            if not tool_exists(t):
                self.log(f"[WARNING] {t} nahi mila! (apt install aircrack-ng)\n")
        self.after(500, self.refresh_ifaces)

    def _build_output(self):
        inp = ttk.Frame(self)
        inp.pack(fill="x", padx=8, pady=(8, 0))

        tk.Label(inp, text="Interface:", bg=BG, fg=TEXT, font=FONT).pack(side="left")
        self.iface_combo = ttk.Combobox(inp, textvariable=self.iface_var,
                                        width=12, state="readonly")
        self.iface_combo.pack(side="left", padx=6)
        tk.Button(inp, text="↻", bg=PANEL, fg=GREEN, font=FONT,
                  relief="flat", command=self.refresh_ifaces).pack(side="left")

        tk.Label(inp, text="Kaam:", bg=BG, fg=TEXT, font=FONT).pack(side="left", padx=(10, 0))
        modes = ["Scan networks", "Monitor mode ON", "Monitor mode OFF"]
        ttk.Combobox(inp, textvariable=self.mode_var, values=modes,
                     width=16, state="readonly").pack(side="left", padx=6)

        super()._build_output()

    def refresh_ifaces(self):
        try:
            out = subprocess.run(["iw", "dev"], capture_output=True,
                                 text=True, timeout=5).stdout
            ifaces = re.findall(r"Interface (\w+)", out)
            self.iface_combo["values"] = ifaces
            if ifaces and not self.iface_var.get():
                self.iface_var.set(ifaces[0])
        except Exception:
            pass

    def build_command(self):
        iface = self.iface_var.get().strip()
        if not iface:
            messagebox.showwarning("Interface?", "Pehle interface select karo!")
            return None
        m = self.mode_var.get()
        if m == "Scan networks":
            mon = iface if "mon" in iface else iface
            return ["airodump-ng", mon]
        elif m == "Monitor mode ON":
            return ["airmon-ng", "start", iface]
        else:
            return ["airmon-ng", "stop", iface]


# ================= METASPLOIT TAB =================
class MsfTab(ToolTab):
    def __init__(self, parent):
        self.cmd_var = tk.StringVar(value="search type:exploit platform:linux")
        super().__init__(parent)
        if not tool_exists("msfconsole"):
            self.log("[WARNING] msfconsole nahi mila!\n")
        self.log("Tip: neeche msfconsole command likho, Run dabao.\n"
                 "Examples:\n"
                 "  search type:auxiliary name:scanner/smb\n"
                 "  use auxiliary/scanner/portscan/tcp\n\n")

    def _build_output(self):
        inp = ttk.Frame(self)
        inp.pack(fill="x", padx=8, pady=(8, 0))
        tk.Label(inp, text="msf>", bg=BG, fg=GREEN, font=FONT_BIG).pack(side="left")
        tk.Entry(inp, textvariable=self.cmd_var, bg=PANEL, fg=TEXT,
                 font=FONT, insertbackground=GREEN).pack(
                     side="left", fill="x", expand=True, padx=6)
        super()._build_output()

    def build_command(self):
        cmd = self.cmd_var.get().strip()
        if not cmd:
            return None
        # Har command ko msfconsole -q -x me chalao
        return ["msfconsole", "-q", "-x", f"{cmd}; exit"]


# ================= MAIN APP =================
class KaliToolkit(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Jazzy Kali Toolkit")
        self.geometry("900x600")
        self.configure(bg=BG)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL, foreground=TEXT,
                        font=FONT, padding=(14, 6))
        style.map("TNotebook.Tab", background=[("selected", GREEN)],
                  foreground=[("selected", "black")])
        style.configure("TCombobox", fieldbackground=PANEL, background=PANEL,
                        foreground=TEXT)

        header = tk.Label(self, text="⚡ JAZZY KALI TOOLKIT",
                          bg=BG, fg=GREEN, font=("Consolas", 14, "bold"))
        header.pack(pady=(10, 4))
        sub = tk.Label(self, text="Apne lab pe hi use karo 🔒",
                       bg=BG, fg=DIM, font=("Consolas", 9))
        sub.pack(pady=(0, 6))

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        nb.add(NmapTab(nb), text="  Nmap Scan  ")
        nb.add(WifiTab(nb), text="  WiFi Audit  ")
        nb.add(MsfTab(nb), text="  Metasploit  ")


if __name__ == "__main__":
    import os
    if os.geteuid() != 0:
        print("[!] Root chahiye kuch features ke liye — sudo se chalao:")
        print("    sudo python3 jazzy_kali_toolkit.py")
    app = KaliToolkit()
    app.mainloop()
