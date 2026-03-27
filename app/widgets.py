# ./app/widgets.py
# 存放自定義 UI 元件 (MultiSelectDropdown)
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

class MultiSelectDropdown(ttk.Frame):
    def __init__(self, parent, options, width=40, field_key=None):
        super().__init__(parent)
        self.field_key = field_key
        self.options = list(options) if options else []
        self.vars = {} 
        self.selected_items = [] 

        self.display_var = tk.StringVar()
        self.entry = ttk.Entry(
            self, 
            textvariable=self.display_var, 
            width=width, 
            state="readonly")
        
        self.entry.pack(
            side=tk.LEFT, 
            fill=tk.X, 
            expand=True)
        
        self.btn = tk.Button(
            self, 
            text="▼", 
            width=2,
            height=1,
            font=("Arial", 8),
            command=self.toggle_dropdown,
            bg="#3e3e3e",
            fg="white",
            activebackground="#4a90e2",
            activeforeground="white",
            relief="raised",
            bd=1
        )
        self.btn.pack(side=tk.RIGHT)
        self.popup = None

        for opt in self.options:
            self.vars[opt] = tk.BooleanVar(value=False)

    def render_checkboxes(self):
        """清除並重新繪製所有勾選框內容"""
        if hasattr(self, 'scrollable_frame') and self.scrollable_frame:
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()

        for opt in self.options:
            if opt not in self.vars:
                self.vars[opt] = tk.BooleanVar(value=False)

            cb = tk.Checkbutton(
                self.scrollable_frame, 
                text=opt, 
                variable=self.vars[opt], 
                command=self.update_display, 
                bg="#2d2d2d", fg="#eeeeee", 
                selectcolor="#4a90e2", 
                activebackground="#3e3e3e", activeforeground="white", 
                anchor="w", 
                font=("Arial", 10),
                padx=5, pady=2
            )
            cb.pack(fill=tk.X, expand=True)

    def toggle_dropdown(self):
        if self.popup and self.popup.winfo_exists():
            self.popup.destroy()
            return

        self.popup = tk.Toplevel(self)
        self.popup.wm_overrideredirect(True) 
        self.popup.configure(bg="#2d2d2d")
        
        entry_x = self.entry.winfo_rootx()
        entry_y = self.entry.winfo_rooty()
        entry_h = self.entry.winfo_height()
        entry_w = self.entry.winfo_width()
        total_width = entry_w + self.btn.winfo_width()
        
        self.popup.geometry(f"{total_width}x250+{entry_x}+{entry_y + entry_h}")


        # ==========================================================
        # 【後】建立 Canvas 滾動區域，讓它去填滿畫面上方的剩餘空間
        # ==========================================================
        canvas_frame = tk.Frame(self.popup, bg="#2d2d2d")
        canvas_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # 這裡把 canvas 綁定到 self，方便後續焦點判斷
        self.popup_canvas = tk.Canvas(canvas_frame, bg="#2d2d2d", highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.popup_canvas.yview)
        self.scrollable_frame = tk.Frame(self.popup_canvas, bg="#2d2d2d")

        self.scrollable_frame.bind("<Configure>", lambda e: self.popup_canvas.configure(scrollregion=self.popup_canvas.bbox("all")))
        window_id = self.popup_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.popup_canvas.bind("<Configure>", lambda e: self.popup_canvas.itemconfig(window_id, width=e.width))
        self.popup_canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.popup_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 渲染內容
        self.render_checkboxes()

        self.popup.bind("<FocusOut>", self.close_popup)
        self.popup.focus_set() 

        # 滾輪綁定
        def _on_mousewheel(event):
            self.popup_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        def _on_linux_scroll_up(event):
            self.popup_canvas.yview_scroll(-1, "units")
        def _on_linux_scroll_down(event):
            self.popup_canvas.yview_scroll(1, "units")

        for widget in [self.popup, canvas_frame, self.popup_canvas, self.scrollable_frame]:
            widget.bind("<MouseWheel>", _on_mousewheel)
            widget.bind("<Button-4>", _on_linux_scroll_up)
            widget.bind("<Button-5>", _on_linux_scroll_down)

    def close_popup(self, event=None):
        if self.popup:
            self.popup.destroy()
            self.popup = None

    def update_display(self):
        selected = [opt for opt, var in self.vars.items() if var.get()]
        self.display_var.set(", ".join(selected))
        self.selected_items = selected

    def set_selection(self, items):
        if items is None: items = []
        if isinstance(items, str) and items: items = [items]
        elif not items: items = []
        self.selected_items = items
        self.display_var.set(", ".join(items))
        if not self.vars:
            for opt in self.options:
                self.vars[opt] = tk.BooleanVar(value=(opt in items))
        else:
            for opt, var in self.vars.items():
                var.set(opt in items)

    def get_selection(self):
        checked_items = [opt for opt, var in self.vars.items() if var.get()]
        
        # 找出那些被 set_selection 設定進來，但不在我們預設 options 裡的資料 (保留它們)
        preserved_items = [item for item in self.selected_items if item not in self.options]
        
        # 為了保持順序並去重
        result = []
        seen = set()
        for item in checked_items + preserved_items:
            if item not in seen:
                result.append(item)
                seen.add(item)
        return result
    