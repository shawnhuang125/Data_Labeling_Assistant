import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import os

# 全域設定
UI_CONFIG = {
    "original_id": {
        "label": "原始編號 (Original ID)",
        "desc": "資料庫中的唯一識別碼不可修改。"
    },
    "name": {
        "label": "店名 (Name)",
        "desc": "店家的完整名稱，例如：鼎泰豐 (信義店)。"
    },
    "food_type": {
        "label": "食物類型 (Food Type)",
        "desc": "(必填)粗略分類，請選擇最接近的類別。點擊右側按鈕",
        "options": [
            "麵食", "飯類", "炸物", "小吃", "粿類", "炒物", "速食", 
            "甜點", "飲料", "火鍋", "燒烤", "其他"
        ]
    },
    "cuisine_type": {
        "label": "料理菜系 (Cuisine Type)",
        "desc": "(必填)(可多選) 請點選下方列表,(如果沒有料理菜系也沒有口味描述也沒有食物類型也沒有服務標籤就刪掉該評論並新增同一店家的評論)點擊右側按鈕",
        "options": [
            "中式料理", "日式料理", "韓式料理", "泰式料理", 
            "義式料理", "美式料理", "法式料理", "台式料理",
            "新加坡料理", "馬來西亞料理","印尼料理","印度料理"
        ]
    },
    "flavor": {
        "label": "口味描述 (Flavor)",
        "desc": "(必填)請填入評論中提到的食物口感或味道描述詞，例如：外酥裡嫩, 麻辣, 奶香濃郁(如果沒有料理菜系也沒有口味描述也沒有食物類型也沒有服務標籤就刪掉該評論並新增同一店家的評論)"
    },
    "level": {
        "label": "等級 (Level)",
        "desc": "(必填)請根據Flavor欄位判斷:1=負評,2=普通好評(<2個描述詞),3=優質好評(>2個描述詞)或有包含服務標籤(Service Tags)",
        "options": ["1", "2", "3"]
    },
    "service_tags": {
        "label": "服務標籤 (Service Tags)",
        "desc": "(可多選) 請手動輸入，多個標籤請用「逗號」分隔。例如：有插座, 店員親切(如果沒有料理菜系也沒有口味描述也沒有食物類型也沒有服務標籤就刪掉該評論並新增同一店家的評論)"
        
    },
    "summary": {
        "label": "評論摘要 (Summary)",
        "desc": "(必填)找出包含品項與描述詞的句子。用拼湊的方式不考慮連貫度"
    },
    "review_text": {
        "label": "評論內容 (Review Text)",
        "desc": "完整的評論內容，請保持每一句完整 (不可修改)。"
    }
}
class MultiSelectDropdown(ttk.Frame):
    def __init__(self, parent, options, width=40):
        super().__init__(parent)
        self.options = options
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
            width=2,           # 寬度：2 個字元
            height=1,          # 高度：1 行文字 (這樣高度就會變小)
            font=("Arial", 8), # 字體：改小一點 (8號字)，按鈕會更迷你
            command=self.toggle_dropdown,
            
            # 以下是配合深色主題的顏色設定
            bg="#3e3e3e",      
            fg="white",
            activebackground="#4a90e2", # 按下去變藍色
            activeforeground="white",
            relief="raised",   # 按鈕樣式
            bd=1               # 邊框寬度
        )
        self.btn.pack(side=tk.RIGHT)
        self.popup = None

        for opt in self.options:
            self.vars[opt] = tk.BooleanVar(value=False)

    def toggle_dropdown(self):
        if self.popup and self.popup.winfo_exists():
            self.popup.destroy()
            return

        # 建立無邊框視窗
        self.popup = tk.Toplevel(self)
        self.popup.wm_overrideredirect(True) 
        self.popup.configure(bg="#2d2d2d")
        
        # 取得輸入框的位置與尺寸
        entry_x = self.entry.winfo_rootx()
        entry_y = self.entry.winfo_rooty()
        entry_h = self.entry.winfo_height()
        entry_w = self.entry.winfo_width()
        
        # 加上按鈕的寬度，讓選單跟整個元件一樣寬
        total_width = entry_w + self.btn.winfo_width()

        # 設定選單位置 (在輸入框正下方)
        y_pos = entry_y + entry_h
        
        # [修改] 設定選單大小：寬度跟元件一樣，高度固定 200
        # 如果您覺得跟元件一樣寬太窄，可以手動指定寬度，例如：f"250x200+{entry_x}+{y_pos}"
        self.popup.geometry(f"{total_width}x200+{entry_x}+{y_pos}")

        # 建立 Canvas 與 Scrollbar
        canvas = tk.Canvas(self.popup, bg="#2d2d2d", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.popup, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#2d2d2d")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        # 讓 frame 寬度跟隨 canvas
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(window_id, width=e.width)
        )

        window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        if not self.vars:
            for opt in self.options:
                self.vars[opt] = tk.BooleanVar(value=False)

        for opt in self.options:
            cb = tk.Checkbutton(
                scrollable_frame, 
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

        self.popup.bind("<FocusOut>", lambda e: self.close_popup(e))
        self.popup.focus_set() 

        # 滑鼠滾輪事件綁定
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _on_linux_scroll_up(event):
            canvas.yview_scroll(-1, "units")

        def _on_linux_scroll_down(event):
            canvas.yview_scroll(1, "units")

        for widget in [self.popup, canvas, scrollable_frame]:
            widget.bind("<MouseWheel>", _on_mousewheel)
            widget.bind("<Button-4>", _on_linux_scroll_up)
            widget.bind("<Button-5>", _on_linux_scroll_down)

    def close_popup(self, event):
        if self.popup:
            self.after(100, lambda: self.popup.destroy() if self.popup else None)

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


class ReviewEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Review JSON Editor")
        self.root.geometry("1100x900") 

        self.data_list = []
        self.current_index = None
        self.filename = None

        # 用來記憶每間店的共通資訊
        # 結構會是 { "店家ID": {"food_type": "...", "cuisine_type": [...], "service_tags": [...]} }
        self.store_info_cache = {}

        self.original_id_var = tk.StringVar()
        self.name_var = tk.StringVar()
        self.food_type_var = tk.StringVar()
        self.flavor_var = tk.StringVar()
        self.level_var = tk.StringVar()
        self.tags_var = tk.StringVar()
        self.summary_var = tk.StringVar()

        self.food_type_dropdown = None
        self.cuisine_dropdown = None
        self.tags_dropdown = None
        
        self.setup_dark_theme() 

        # --- UI 佈局 ---
        self.paned_window = tk.PanedWindow(root, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # === 左側區塊 ===
        self.left_frame = ttk.Frame(self.paned_window, width=300)
        self.paned_window.add(self.left_frame)

        self.btn_frame = ttk.Frame(self.left_frame)
        self.btn_frame.pack(fill=tk.X, pady=5)
        
        self.btn_load = ttk.Button(self.btn_frame, text="📂 載入 JSON", command=self.load_json)
        self.btn_load.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        # 快速存檔按鈕 (直接覆蓋原檔)
        self.btn_save = ttk.Button(self.btn_frame, text="💾 儲存", command=self.quick_save)
        self.btn_save.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        
        self.btn_save = ttk.Button(self.btn_frame, text="💾 另存新檔", command=self.save_as_json)
        self.btn_save.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        self.lbl_list_title = ttk.Label(self.left_frame, text="評論列表 (ID - 店名):")
        self.lbl_list_title.pack(anchor=tk.W, padx=5)

        self.list_frame = ttk.Frame(self.left_frame)
        self.list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.scrollbar = ttk.Scrollbar(self.list_frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.listbox = tk.Listbox(
            self.list_frame, 
            yscrollcommand=self.scrollbar.set, 
            font=("Arial", 10),
            bg="#2d2d2d", fg="#eeeeee",            
            selectbackground="#4a90e2", selectforeground="#ffffff", 
            highlightthickness=0, borderwidth=1,
            exportselection=False
        )
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.listbox.bind('<<ListboxSelect>>', self.on_select)
        self.scrollbar.config(command=self.listbox.yview)

        self.action_frame = ttk.Frame(self.left_frame)
        self.action_frame.pack(fill=tk.X, pady=10)
        self.btn_add_same = ttk.Button(self.action_frame, text="➕ 新增此店家評論", command=self.add_review_for_current_store)
        self.btn_add_same.pack(fill=tk.X, padx=5, pady=2)
        self.btn_delete = ttk.Button(self.action_frame, text="🗑️ 刪除選取項目", command=self.delete_current)
        self.btn_delete.pack(fill=tk.X, padx=5, pady=2)

        # === 右側區塊 ===
        self.right_container = ttk.Frame(self.paned_window)
        self.paned_window.add(self.right_container)
        
        self.canvas = tk.Canvas(self.right_container, bg="#2d2d2d", highlightthickness=0)
        self.scrollbar_y = ttk.Scrollbar(self.right_container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))
        self.canvas.configure(yscrollcommand=self.scrollbar_y.set)

        self.scrollbar_y.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # --- 建立表單欄位 ---
        
        # 1. Original ID (ReadOnly)
        cfg = UI_CONFIG["original_id"]
        self.create_form_field(cfg["label"], self.original_id_var, cfg["desc"], entry_width=20, readonly=True)
        
        # 2. [修改] Name (ReadOnly)
        cfg = UI_CONFIG["name"]
        self.create_form_field(cfg["label"], self.name_var, cfg["desc"], entry_width=40, readonly=True)
        
        # 3. Food Type
        cfg = UI_CONFIG["food_type"]
        self.food_type_dropdown = self.create_form_field(
            cfg["label"], 
            None, # 多選不需要傳入 textvariable 
            cfg["desc"], 
            options=cfg.get("options"), 
            is_multiselect=True,
            entry_width=40
        )
        # Cuisine Type()菜系)
        cfg = UI_CONFIG["cuisine_type"]
        self.cuisine_dropdown = self.create_form_field(
            cfg["label"], None, cfg["desc"], 
            options=cfg["options"], is_multiselect=True,
            entry_width=40
        )
        
        # Service Tags(服務標籤) - [修改] 改成綁定 tags_var 的文字框
        cfg = UI_CONFIG["service_tags"]
        # 注意：這裡移除 options 和 is_multiselect，並傳入 self.tags_var
        self.create_form_field(cfg["label"], self.tags_var, cfg["desc"], entry_width=100)

        # 6. Level(等級)
        cfg = UI_CONFIG["level"]
        self.create_form_field(cfg["label"], self.level_var, cfg["desc"], entry_width=15, options=cfg["options"])

        # 5. Flavor(口味)
        cfg = UI_CONFIG["flavor"]
        self.create_form_field(cfg["label"], self.flavor_var, cfg["desc"])
        
        # 8. Summary(評論摘要)
        cfg = UI_CONFIG["summary"]
        self.create_form_field(cfg["label"], self.summary_var, cfg["desc"])

        # 9. Review Text(完整評論內容)
        cfg = UI_CONFIG["review_text"]
        lbl_review = ttk.Label(self.scrollable_frame, text=cfg["label"], font=("Arial", 10, "bold"))
        lbl_review.pack(anchor=tk.W, padx=10, pady=(15, 0))
        
        lbl_review_desc = ttk.Label(self.scrollable_frame, text=cfg["desc"], font=("Arial", 9), foreground="#aaaaaa")
        lbl_review_desc.pack(anchor=tk.W, padx=10, pady=(0, 5))

        self.txt_review = scrolledtext.ScrolledText(
            self.scrollable_frame, 
            width=20, # [修改] 這裡數字改小一點(例如20)，讓 pack 去控制實際寬度，才不會被撐開導致無法縮小
            height=5, 
            font=("Arial", 10),
            bg="#3e3e3e", fg="#ffffff", insertbackground="white", selectbackground="#4a90e2",
        )
        self.txt_review.pack(fill=tk.X, expand=True, padx=10, pady=5)

        self.btn_apply = ttk.Button(self.scrollable_frame, text="✅ 套用變更 (Apply)", command=self.save_current_to_memory)
        self.btn_apply.pack(fill=tk.X, padx=10, pady=20)

        # 1. 在這裡定義哪些欄位需要「自動記憶與同步」
        self.MEMORY_FIELDS = ["food_type", "cuisine_type", "service_tags"]

        # 2. 建立「欄位名稱」對應「UI元件」的字典
        # 程式會根據這裡的對應，自動去抓取或填入資料
        self.field_ui_map = {
            "food_type": self.food_type_dropdown,
            "cuisine_type": self.cuisine_dropdown,
            "service_tags": self.tags_var  # <--- 檢查這裡！原本可能是 tags_dropdown
        }

        self.status_var = tk.StringVar()
        self.status_var.set("請載入 JSON 檔案...")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def setup_dark_theme(self):
        style = ttk.Style()
        style.theme_use('clam') 
        bg_color = "#2d2d2d"
        fg_color = "#eeeeee"
        entry_bg = "#3e3e3e"
        select_bg = "#4a90e2" # 這是你定義的藍色反白
        
        self.root.configure(bg=bg_color)
        
        # 基礎設定
        style.configure(".", background=bg_color, foreground=fg_color, fieldbackground=entry_bg)
        
        # [核心修改] 強制設定全域選取顏色，確保失去焦點時不會變灰或不見
        style.map(".", 
            background=[("selected", select_bg), ("active", select_bg)],
            foreground=[("selected", "white"), ("active", "white")]
        )
        
        # 按鈕設定
        style.configure("TButton", background="#3e3e3e", foreground=fg_color, borderwidth=1, focuscolor=select_bg)
        style.map("TButton", background=[("active", select_bg)], foreground=[("active", "white")])
        
        # 輸入框設定
        style.configure("TEntry", fieldbackground=entry_bg, foreground=fg_color, insertcolor="white")
        style.map("TEntry", fieldbackground=[("readonly", entry_bg)]) 
        
        # 下拉選單設定
        style.configure("TCombobox", fieldbackground=entry_bg, background=entry_bg, foreground=fg_color, arrowcolor="white")
        style.map("TCombobox", 
            fieldbackground=[("readonly", entry_bg)], 
            selectbackground=[("readonly", select_bg), ("!focus", select_bg)], # 失去焦點也保持藍色
            selectforeground=[("readonly", "white"), ("!focus", "white")]
        )
        
        # 傳統元件 (Listbox) 的全域設定
        self.root.option_add('*TCombobox*Listbox.background', bg_color)
        self.root.option_add('*TCombobox*Listbox.foreground', fg_color)
        self.root.option_add('*TCombobox*Listbox.selectBackground', select_bg)
        self.root.option_add('*TCombobox*Listbox.selectForeground', 'white')
        self.root.option_add('*TCombobox*Listbox.font', ("Arial", 10))
        
        # 滾動條與分割視窗
        style.configure("Vertical.TScrollbar", background="#3e3e3e", troughcolor=bg_color, arrowcolor="white", gripcount=0)
        style.configure("TPanedwindow", background=bg_color)

    def create_form_field(self, label_text, variable, description="", entry_width=None, options=None, readonly=False, is_multiselect=False):
        frame = ttk.Frame(self.scrollable_frame)
        frame.pack(fill=tk.X, padx=10, pady=8)
        lbl_title = ttk.Label(frame, text=label_text, font=("Arial", 10, "bold"))
        lbl_title.pack(anchor=tk.W)
        if description:
            # [修正] 兩個數字都要改成 62
            wrapped_desc = "\n".join([description[i:i+62] for i in range(0, len(description), 62)])
            
            lbl_desc = ttk.Label(
                frame, 
                text=wrapped_desc, 
                font=("Arial", 9), 
                foreground="#aaaaaa",
                justify="left"
            )
            lbl_desc.pack(anchor=tk.W, pady=(0, 3))
        
        if is_multiselect and options:
            dropdown = MultiSelectDropdown(frame, options, width=entry_width if entry_width else 40)
            dropdown.pack(anchor=tk.W)
            return dropdown 
        elif options:
            entry = ttk.Combobox(frame, textvariable=variable, values=options)
            entry['state'] = 'readonly' 
            if entry_width:
                entry.config(width=entry_width)
            entry.pack(anchor=tk.W)
            return None
        else:
            if entry_width:
                entry = ttk.Entry(frame, textvariable=variable, width=entry_width)
                entry.pack(anchor=tk.W) 
            else:
                entry = ttk.Entry(frame, textvariable=variable)
                entry.pack(fill=tk.X, expand=True)
            
            if readonly:
                entry.config(state='readonly')
            return None

    # --- 邏輯處理 ---
    def load_json(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if not file_path: return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                self.data_list = json.load(f)
            self.filename = file_path

            self.store_info_cache = {}
            
            # =========== [修改開始] ===========
            for item in self.data_list:
                sid = item.get("original_id")
                if not sid: continue
                
                # 1. 初始化該店家的快取字典 (不用預先寫死 Key 了)
                if sid not in self.store_info_cache:
                    self.store_info_cache[sid] = {}

                # 2. 動態遍歷你在 __init__ 設定的記憶欄位
                # 只要 JSON 裡有這個欄位的資料，就存入快取
                for field in self.MEMORY_FIELDS:
                    if item.get(field):
                        self.store_info_cache[sid][field] = item[field]
            # =========== [修改結束] ===========

            self.refresh_listbox()
            self.status_var.set(f"已載入: {os.path.basename(file_path)} | 共 {len(self.data_list)} 筆資料")
            self.current_index = None
            self.clear_form()
        except Exception as e:
            messagebox.showerror("錯誤", f"無法讀取檔案: {e}")

    def refresh_listbox(self):
        self.listbox.delete(0, tk.END)
        for idx, item in enumerate(self.data_list):
            display_text = f"[{idx}] ID:{item.get('original_id', '?')} | {item.get('name', 'Unknown')}"
            self.listbox.insert(tk.END, display_text)

    def on_select(self, event):
        # 1. 先儲存上一筆 (如果有的話)
        if self.current_index is not None:
            self.save_current_to_memory()

        selection = self.listbox.curselection()
        if not selection: return
        index = selection[0]
        self.current_index = index
        data = self.data_list[index]

        # 2. 讀取 ID 與基本資料
        store_id = data.get("original_id", "") 
        self.original_id_var.set(store_id)
        self.name_var.set(data.get("name", ""))
        self.level_var.set(str(data.get("level", "")))
        self.summary_var.set(data.get("review_summary", ""))

        # 填入文字區
        self.txt_review.delete("1.0", tk.END)
        self.txt_review.insert("1.0", data.get("review_text", ""))

        # 處理 Flavor (獨有欄位，確保以逗號分隔字串顯示)
        flavors = data.get("flavor", [])
        if isinstance(flavors, list):
            self.flavor_var.set(", ".join(flavors))
        else:
            self.flavor_var.set(str(flavors))

        # =========== [修改重點] 動態處理記憶欄位 (含服務標籤) ===========
        auto_filled = False
        cache = self.store_info_cache.get(store_id, {}) 

        for field in self.MEMORY_FIELDS:
            ui_widget = self.field_ui_map.get(field)
            if not ui_widget: continue 

            # A. 取得最優先的資料來源 (Data -> Cache -> Default Empty List)
            raw_val = data.get(field)
            
            # 若資料為空且快取有值，執行自動帶入
            if not raw_val and cache.get(field):
                raw_val = cache[field]
                data[field] = raw_val # 寫回當前資料清單，確保存檔時一致
                auto_filled = True
            
            # 確保 raw_val 最終是 List 格式，避免後續顯示錯誤
            if raw_val is None:
                raw_val = []
            elif isinstance(raw_val, str):
                raw_val = [t.strip() for t in raw_val.split(",") if t.strip()]

            # B. 填入 UI (根據元件特性分流)
            if hasattr(ui_widget, 'set_selection'):
                # 適用於：具有自定義 set_selection 方法的物件 (food_type, cuisine_type)
                ui_widget.set_selection(raw_val)
            elif isinstance(ui_widget, tk.StringVar):
                # 適用於：StringVar 變數 (service_tags)
                ui_widget.set(", ".join(raw_val))
        # =============================================================

        status_msg = f"正在編輯第 {index} 筆資料"
        if auto_filled: 
            status_msg += " (已自動帶入店家資訊)"
        self.status_var.set(status_msg)

    def save_current_to_memory(self):
        if self.current_index is None: return
        try:
            store_id = self.original_id_var.get()
            
            # (A) 取得「記憶欄位」資料 (跨筆同步：food_type, cuisine_type, service_tags)
            current_memory_values = {}
            for field in self.MEMORY_FIELDS:
                ui_widget = self.field_ui_map.get(field)
                if not ui_widget: continue

                if hasattr(ui_widget, 'get_selection'):
                    # 適用於：MultiSelectDropdown
                    current_memory_values[field] = ui_widget.get_selection()
                elif isinstance(ui_widget, tk.StringVar):
                    # 適用於：service_tags 文字輸入框
                    val_str = ui_widget.get().strip()
                    # 將 "A, B" 轉為 ["A", "B"]，並過濾掉空白項
                    current_memory_values[field] = [t.strip() for t in val_str.split(",") if t.strip()]

            # (B) 取得「單筆獨有」欄位並清洗資料
            current_name = self.name_var.get().strip()
            current_summary = self.summary_var.get().strip()
            current_review_text = self.txt_review.get("1.0", tk.END).strip()
            
            # 處理 Level (確保為整數，若非數字則保留原樣)
            lvl_raw = self.level_var.get()
            current_level = int(lvl_raw) if lvl_raw.isdigit() else lvl_raw
            
            # 處理 Flavor (雖然是獨有，但也建議轉為 List 存儲以保持結構一致)
            flavor_str = self.flavor_var.get().strip()
            current_flavor = [t.strip() for t in flavor_str.split(",") if t.strip()]

            # 2. 批次更新資料清單 (data_list)
            count = 0
            for item in self.data_list:
                # 更新「當前正在編輯」的這一筆資料
                if item is self.data_list[self.current_index]:
                    item.update({
                        "name": current_name,
                        "review_summary": current_summary,
                        "review_text": current_review_text,
                        "level": current_level,
                        "flavor": current_flavor
                    })
                
                # 同步更新「同一間店」的所有記憶欄位
                if item.get("original_id") == store_id:
                    for field, val in current_memory_values.items():
                        item[field] = val
                    count += 1

            # 3. 更新快取 (Store Cache)
            if store_id:
                if store_id not in self.store_info_cache:
                    self.store_info_cache[store_id] = {}
                self.store_info_cache[store_id].update(current_memory_values)

            self.status_var.set(f"✅ 已同步更新此店家共 {count} 筆評論的設定")
            
        except Exception as e:
            messagebox.showerror("錯誤", f"儲存變更時發生錯誤: {e}")

    def add_review_for_current_store(self):
        if self.current_index is None:
            messagebox.showwarning("提示", "請先選擇一家店，才能新增該店的評論。")
            return
        current_data = self.data_list[self.current_index]
        new_entry = {
            "original_id": current_data.get("original_id", ""),
            "name": current_data.get("name", ""),
            "review_summary": "",
            "review_text": "", 
            "food_type": current_data.get("food_type", ""),
            "cuisine_type": current_data.get("cuisine_type", []), 
            "flavor": [],
            "service_tags": [],
            "level": ""
        }
        insert_pos = self.current_index + 1
        self.data_list.insert(insert_pos, new_entry)
        self.refresh_listbox()
        self.listbox.select_clear(0, tk.END)
        self.listbox.select_set(insert_pos)
        self.listbox.event_generate("<<ListboxSelect>>")
        self.status_var.set("已新增一筆資料")

    def delete_current(self):
        if self.current_index is None: return
        if messagebox.askyesno("確認", "確定要刪除這筆評論嗎？"):
            del self.data_list[self.current_index]
            self.current_index = None
            self.clear_form()
            self.refresh_listbox()
            self.status_var.set("資料已刪除")

    def clear_form(self):
        self.original_id_var.set("")
        self.name_var.set("")
        # self.food_type_var.set("") # 這行不用，因為 food_type 在下方迴圈處理
        self.flavor_var.set("")
        self.level_var.set("")
        self.summary_var.set("")

        # [手動清空] 服務標籤
        self.tags_var.set("")
        


        # =========== [自動清空記憶欄位] ===========
        # 這邊只會清空還留在 MEMORY_FIELDS 裡的 (food_type, cuisine_type)
        for field in self.MEMORY_FIELDS:
            ui_widget = self.field_ui_map.get(field)
            if ui_widget and hasattr(ui_widget, 'set_selection'):
                ui_widget.set_selection([])
        # =======================================
        
        self.txt_review.delete("1.0", tk.END)
        
    # [新增] 快速存檔 (直接寫入當前檔案)
    def quick_save(self):
        if not self.data_list:
            messagebox.showwarning("警告", "沒有資料可以儲存")
            return
        
        # 如果還沒開啟過檔案 (例如是新建立的)，就轉去「另存新檔」
        if not self.filename:
            self.save_as_json()
            return

        # 先把當前編輯的內容寫入記憶體
        if self.current_index is not None:
            self.save_current_to_memory()

        try:
            # 直接寫入 self.filename (原檔路徑)
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump(self.data_list, f, ensure_ascii=False, indent=4)
            
            self.status_var.set(f"💾 已儲存至原檔: {os.path.basename(self.filename)}")
            # 這裡可以不用跳視窗干擾操作，或是只在狀態列顯示
            # messagebox.showinfo("成功", "已儲存") 
        except Exception as e:
            messagebox.showerror("錯誤", f"存檔失敗: {e}")

    # [修改] 另存新檔 (原本的 save_json 改名)
    def save_as_json(self):
        if not self.data_list:
            messagebox.showwarning("警告", "沒有資料可以儲存")
            return
        
        if self.current_index is not None:
            self.save_current_to_memory()
            
        # 跳出對話框問要存在哪
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if not file_path: return
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.data_list, f, ensure_ascii=False, indent=4)
            
            # 更新當前檔案路徑，這樣下次按「快速存檔」就會存到這個新檔
            self.filename = file_path 
            
            messagebox.showinfo("成功", f"檔案已儲存至:\n{file_path}")
            self.status_var.set(f"💾 已另存: {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("錯誤", f"存檔失敗: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ReviewEditorApp(root)
    root.mainloop()

