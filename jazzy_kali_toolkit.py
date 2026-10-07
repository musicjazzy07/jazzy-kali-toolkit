#!/usr/bin/env python3
"""
Jazzy Kali Toolkit v2.0 — Kali tools ke liye universal GUI frontend.
Saare tool definitions tools.json me hain — naya tool = JSON me entry.

Usage: sudo python3 jazzy_kali_toolkit.py
Sirf apne lab / apne network pe use karo.
"""

import json
import os
import re
import shlex
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

BASE = os.path.dirname(os.path.abspath(__file__))

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


def load_tools():
    with open(os.path.join(BASE, "tools.json"), encoding="utf-8") as f:
        data = json.load(f)
    return data["tools"]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Jazzy Kali Toolkit v2.0")
        self.geometry("1000x680")
        self.configure(bg=BG)
        self.tools = load_tools()
        self.proc = None
        self.field_widgets = {}
        self.current_tool = None

        self._style()
        self._header()
        self._body()
        self._output()
        self._populate_tree()
        # Pehla tool select karo
        first = self.tree.get_children()[0]
        self.tree.selection_set(self.tree.get_children(first)[0])
        self.on_select(None)

    # ---------- UI setup ----------
    def _style(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("TFrame", background=BG)
        s.configure("TLabel", background=BG, foreground=TEXT, font=FONT)
        s.configure("Treeview", background=PANEL, foreground=TEXT,
                    fieldbackground=PANEL, font=FONT, rowheight=24)
        s.configure("Treeview.Heading", background=BG, foreground=GREEN)
        s.map("Treeview", background=[("selected", GREEN)],
              foreground=[("selected", "black")])
        s.configure("TCombobox", fieldbackground=PANEL, background=PANEL,
                    foreground=TEXT)

    def _header(self):
        tk.Label(self, text="⚡ JAZZY KALI TOOLKIT",
                 bg=BG, fg=GREEN, font=("Consolas", 14, "bold")).pack(pady=(8, 0))
        tk.Label(self, text=f"{len(self.tools)} tools • apne lab pe hi use karo 🔒",
                 bg=BG, fg=DIM, font=("Consolas", 9)).pack(pady=(0, 6))
        search_row = tk.Frame(self, bg=BG)
        search_row.pack(fill="x", padx=10, pady=(0, 4))
        tk.Label(search_row, text="🔍", bg=BG, fg=GREEN, font=FONT).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._populate_tree())
        tk.Entry(search_row, textvariable=self.search_var, bg=PANEL, fg=TEXT,
                 font=FONT, insertbackground=GREEN).pack(side="left", fill="x",
                                                        expand=True, padx=6)

    def _body(self):
        mid = tk.Frame(self, bg=BG)
        mid.pack(fill="both", expand=True, padx=10)

        # Left: tool tree
        left = tk.Frame(mid, bg=BG, width=230)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)
        self.tree = ttk.Treeview(left, show="tree")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        # Right: dynamic form
        right = tk.Frame(mid, bg=PANEL, relief="flat")
        right.pack(side="left", fill="both", expand=True)
        self.form_title = tk.Label(right, text="", bg=PANEL, fg=GREEN,
                                   font=("Consolas", 12, "bold"))
        self.form_title.pack(pady=(10, 2), padx=12, anchor="w")
        self.form_warn = tk.Label(right, text="", bg=PANEL, fg=AMBER,
                                  font=("Consolas", 9))
        self.form_warn.pack(padx=12, anchor="w")
        self.form_frame = tk.Frame(right, bg=PANEL)
        self.form_frame.pack(fill="x", padx=12, pady=8)

        btn_row = tk.Frame(right, bg=PANEL)
        btn_row.pack(fill="x", padx=12, pady=(0, 10))
        self.run_btn = tk.Button(btn_row, text="▶ Run", bg=GREEN, fg="black",
                                 font=FONT_BIG, relief="flat", padx=16,
                                 command=self.on_run)
        self.run_btn.pack(side="left")
        self.stop_btn = tk.Button(btn_row, text="■ Stop", bg=RED, fg="white",
                                  font=FONT_BIG, relief="flat", padx=16,
                                  command=self.stop, state="disabled")
        self.stop_btn.pack(side="left", padx=8)

    def _output(self):
        out_label = tk.Label(self, text="OUTPUT", bg=BG, fg=DIM,
                             font=("Consolas", 9, "bold"))
        out_label.pack(anchor="w", padx=12)
        self.output = scrolledtext.ScrolledText(
            self, bg="black", fg=GREEN, font=FONT, height=12,
            insertbackground=GREEN, wrap="word")
        self.output.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # ---------- Tool list ----------
    def _populate_tree(self):
        q = self.search_var.get().lower()
        self.tree.delete(*self.tree.get_children())
        cats = {}
        for t in self.tools:
            if q and q not in t["name"].lower() and q not in t["category"].lower():
                continue
            cat = t["category"]
            if cat not in cats:
                cats[cat] = self.tree.insert("", "end", text=cat, open=True)
            self.tree.insert(cats[cat], "end", text=t["name"],
                             values=(t["name"],))

    def _find_tool(self, name):
        for t in self.tools:
            if t["name"] == name:
                return t
        return None

    def on_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        if not vals:
            return  # category header
        tool = self._find_tool(vals[0])
        if not tool:
            return
        self.current_tool = tool
        self._build_form(tool)

    # ---------- Dynamic form ----------
    def _build_form(self, tool):
        for w in self.form_frame.winfo_children():
            w.destroy()
        self.field_widgets = {}

        installed = shutil.which(tool.get("check", "")) is not None
        status = "✅ installed" if installed else "❌ nahi mila"
        self.form_title.config(
            text=f"{tool['name']}  [{status}]")
        if tool.get("lab_only"):
            self.form_warn.config(
                text="⚠️ Sirf apne lab / apne network pe chalao!")
        else:
            self.form_warn.config(text="")

        for f in tool.get("fields", []):
            row = tk.Frame(self.form_frame, bg=PANEL)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=f["label"] + ":", bg=PANEL, fg=TEXT,
                     font=FONT, width=20, anchor="w").pack(side="left")
            key = f["key"]
            ftype = f.get("type", "text")
            if ftype == "choice":
                var = tk.StringVar(value=f.get("default", ""))
                labels = f.get("choice_labels", f["choices"])
                cmap = dict(zip(labels, f["choices"]))
                combo = ttk.Combobox(row, textvariable=var, values=labels,
                                     width=30, state="readonly")
                combo.pack(side="left", fill="x", expand=True)
                # display label -> actual value
                self.field_widgets[key] = (var, cmap)
            elif ftype == "check":
                var = tk.BooleanVar(value=f.get("default", False))
                tk.Checkbutton(row, variable=var, bg=PANEL,
                               activebackground=PANEL).pack(side="left")
                self.field_widgets[key] = (var, f.get("flag", ""))
            else:
                var = tk.StringVar(value=f.get("default", ""))
                tk.Entry(row, textvariable=var, bg=BG, fg=TEXT, font=FONT,
                         insertbackground=GREEN).pack(side="left", fill="x",
                                                      expand=True)
                self.field_widgets[key] = (var, None)

    def _collect_values(self, tool):
        vals = {}
        for f in tool.get("fields", []):
            key = f["key"]
            ftype = f.get("type", "text")
            var, extra = self.field_widgets.get(key, (None, None))
            if var is None:
                vals[key] = ""
            elif ftype == "choice":
                vals[key] = extra.get(var.get(), var.get())
            elif ftype == "check":
                vals[key] = extra if var.get() else ""
            else:
                vals[key] = var.get()
        return vals

    # ---------- Run ----------
    def log(self, text):
        self.output.insert("end", text)
        self.output.see("end")

    def on_run(self):
        tool = self.current_tool
        if not tool:
            return
        vals = self._collect_values(tool)
        cmd = []
        for part in tool["command"]:
            # {key} placeholders bharo
            def repl(m):
                return vals.get(m.group(1), "")
            filled = re.sub(r"\{(\w+)\}", repl, part)
            if filled.strip():
                cmd.append(filled)
        if not cmd:
            return
        # msfconsole -x wala case: last arg me spaces hain — split mat karo
        if tool.get("check") == "msfconsole":
            pass  # already list form me sahi hai
        self.output.delete("1.0", "end")
        self.log(f"$ {' '.join(cmd)}\n{'-'*60}\n")
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
            self.log(f"\n{'-'*60}\n[Done, exit={self.proc.returncode}]\n")
        except FileNotFoundError:
            self.log(f"\n[ERROR] Tool nahi mila: {cmd[0]}\n")
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


if __name__ == "__main__":
    import os
    if os.geteuid() != 0:
        print("[!] Kuch features ke liye root chahiye — sudo se chalao.")
    App().mainloop()
