# ./app/editor_logic.py
# 存放主要邏輯與視窗佈局 (ReviewEditorApp)
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import os
from config import UI_CONFIG, MEMORY_FIELDS
from widgets import MultiSelectDropdown
import tool

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
        self.review_labeled_level_var = tk.StringVar()
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
        # === 左側區塊 ===
        self.left_frame = ttk.Frame(self.paned_window, width=300)
        self.paned_window.add(self.left_frame)

        self.btn_frame = ttk.Frame(self.left_frame)
        self.btn_frame.pack(fill=tk.X, pady=5)
        
        self.btn_load = ttk.Button(self.btn_frame, text="📂 載入 JSON", command=self.load_json)
        self.btn_load.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.btn_save = ttk.Button(self.btn_frame, text="💾 儲存", command=self.quick_save)
        self.btn_save.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        self.btn_save_as = ttk.Button(self.btn_frame, text="💾 另存", command=self.save_as_json)
        self.btn_save_as.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # 🔍 ➕ 【新增項目】搜尋控制區塊 
        self.search_frame = ttk.Frame(self.left_frame)
        self.search_frame.pack(fill=tk.X, padx=5, pady=(5, 8))
        
        # 搜尋模式下拉選單 (ID 或 店名)
        self.search_mode_var = tk.StringVar(value="店名")
        self.search_mode_combo = ttk.Combobox(
            self.search_frame, textvariable=self.search_mode_var, 
            values=["店名", "ID"], width=5, state="readonly"
        )
        self.search_mode_combo.pack(side=tk.LEFT, padx=(0, 5))
        self.search_mode_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_listbox())
        
        # 搜尋輸入框 (綁定變數以達成即時輸入、即時過濾)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh_listbox())
        self.search_entry = ttk.Entry(self.search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 快速清空搜尋的按鈕
        self.btn_clear_search = ttk.Button(self.search_frame, text="❌", width=3, command=self.clear_search)
        self.btn_clear_search.pack(side=tk.RIGHT, padx=(3, 0))

        # 列表標題
        self.lbl_list_title = ttk.Label(self.left_frame, text="評論列表 (ID - 店名):")
        self.lbl_list_title.pack(anchor=tk.W, padx=5, pady=(0, 2))

        self.list_frame = ttk.Frame(self.left_frame)
        self.list_frame.pack(fill=tk.BOTH, expand=True)

        # 確保這幾行有加回來！
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

        # 1. 建立 Canvas (滾動區域)
        self.canvas = tk.Canvas(self.right_container, bg="#2d2d2d", highlightthickness=0)
        self.scrollbar_y = ttk.Scrollbar(self.right_container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))
        self.canvas.configure(yscrollcommand=self.scrollbar_y.set)

        self.scrollbar_y.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # 2. 建立「懸浮按鈕容器」(Place 會疊在 Canvas 上層，永遠在右上角)
        self.nav_container = tk.Frame(self.right_container, bg="#2d2d2d")
        self.nav_container.place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=10)

        # 定義高對比、深色主題友善的按鈕樣式
        btn_style = {
            "bg": "#3e3e3e", 
            "fg": "white", 
            "activebackground": "#4a90e2", 
            "activeforeground": "white", 
            "font": ("Arial", 10, "bold"), # 字體縮小
            "relief": "flat", 
            "bd": 0, 
            "padx": 8,   # 減少內部水平間距
            "pady": 2    # 減少內部垂直間距
        }

        # 3. 建立精簡版按鈕
        # 建立按鈕 (使用 Ctrl+符號 的組合)
        # 這裡改用 Unicode 箭頭符號與簡單的 Ctrl 標記
        self.btn_prev = tk.Button(self.nav_container, text="Ctrl+↑", command=self.go_prev, **btn_style)
        self.btn_prev.pack(side=tk.LEFT, padx=1)
        
        self.btn_next = tk.Button(self.nav_container, text="Ctrl+↓", command=self.go_next, **btn_style)
        self.btn_next.pack(side=tk.LEFT, padx=1)

        # 懸浮顏色變化效果
        def on_enter(e): e.widget.config(bg="#4a90e2")
        def on_leave(e): e.widget.config(bg="#3e3e3e")
        self.btn_prev.bind("<Enter>", on_enter); self.btn_prev.bind("<Leave>", on_leave)
        self.btn_next.bind("<Enter>", on_enter); self.btn_next.bind("<Leave>", on_leave)

        # 3. 綁定快捷鍵 (使用 bind_all 確保視窗全局有效)
        self.root.bind("<Control-Left>", self.handle_nav_keys)
        self.root.bind("<Control-Right>", self.handle_nav_keys)

        # 2. 【關鍵】阻止 Listbox 處理這些按鍵
        # 這會攔截掉 Listbox 的預設行為
        self.listbox.bind("<Control-Right>", lambda e: "break")
        self.listbox.bind("<Control-Left>", lambda e: "break")

        # 4. 滑鼠滾輪邏輯
        def _on_mousewheel(event):
            if event.num == 5 or event.delta < 0: self.canvas.yview_scroll(1, "units")
            elif event.num == 4 or event.delta > 0: self.canvas.yview_scroll(-1, "units")
        
        # 當滑鼠進入 Canvas 區域才綁定滾輪，移開就解除，避免影響整個程式
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", _on_mousewheel) or 
                                             self.canvas.bind_all("<Button-4>", _on_mousewheel) or 
                                             self.canvas.bind_all("<Button-5>", _on_mousewheel))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>") or 
                                             self.canvas.unbind_all("<Button-4>") or 
                                             self.canvas.unbind_all("<Button-5>"))
        

        
        # --- 建立表單欄位 ---
        
        # 1. Original ID (ReadOnly)
        cfg = UI_CONFIG["original_id"]
        self.create_form_field(cfg["label"], self.original_id_var, cfg["desc"], entry_width=20, readonly=True)

        self.merchant_category_var = tk.StringVar()
        
        name_row_frame = ttk.Frame(self.scrollable_frame)
        name_row_frame.pack(fill=tk.X, padx=10, pady=0, anchor=tk.W)

        # 左側：店名 (固定寬 350, 高 100)
        name_col = ttk.Frame(name_row_frame, width=350, height=100)
        name_col.pack(side=tk.LEFT, padx=(0, 20))
        name_col.pack_propagate(False)
        self.create_form_field_in_parent(
            name_col, UI_CONFIG["name"]["label"], self.name_var, 
            UI_CONFIG["name"]["desc"], readonly=True, entry_width=40
        )

        # 右側：店家類型 (固定寬 350, 高度調回 90)
        category_col = ttk.Frame(name_row_frame, width=350, height=90)
        category_col.pack(side=tk.LEFT)
        category_col.pack_propagate(False)
        cfg_cat = UI_CONFIG["merchant_category"]
        self.create_form_field_in_parent(
            category_col, cfg_cat["label"], self.merchant_category_var, 
            cfg_cat["desc"], options=cfg_cat["options"], entry_width=35, field_key="merchant_category"
        )

        # --- 第二組併排：食物類型 & 料理菜系 ---
        row1_frame = ttk.Frame(self.scrollable_frame)
        row1_frame.pack(fill=tk.X, padx=10, pady=0, anchor=tk.W)

        # 食物類型 (固定寬 350, 高度調回 140)
        food_col = ttk.Frame(row1_frame, width=350, height=140)
        food_col.pack(side=tk.LEFT, padx=(0, 20))
        food_col.pack_propagate(False)
        self.food_type_dropdown = self.create_form_field_in_parent(
            food_col, UI_CONFIG["food_type"]["label"], None, UI_CONFIG["food_type"]["desc"], 
            options=UI_CONFIG["food_type"]["options"], is_multiselect=True, entry_width=35, field_key="food_type"
        )

        # 料理菜系 (固定寬 350, 高度調回 140)
        cuisine_col = ttk.Frame(row1_frame, width=350, height=140)
        cuisine_col.pack(side=tk.LEFT)
        cuisine_col.pack_propagate(False)
        self.cuisine_dropdown = self.create_form_field_in_parent(
            cuisine_col, UI_CONFIG["cuisine_type"]["label"], None, UI_CONFIG["cuisine_type"]["desc"], 
            options=UI_CONFIG["cuisine_type"]["options"], is_multiselect=True, entry_width=35, field_key="cuisine_type"
        )

        # --- 第二組併排：硬服務標籤 & 服務標籤 ---
        row2_frame = ttk.Frame(self.scrollable_frame)
        row2_frame.pack(fill=tk.X, padx=10, pady=5, anchor=tk.W)

        # 硬服務標籤 (固定寬 350, 高 150)
        facility_col = ttk.Frame(row2_frame, width=350, height=150)
        facility_col.pack(side=tk.LEFT, padx=(0, 20))
        facility_col.pack_propagate(False)
        self.facility_dropdown = self.create_form_field_in_parent(
            facility_col, UI_CONFIG["facility_tags"]["label"], None, UI_CONFIG["facility_tags"]["desc"], 
            options=UI_CONFIG["facility_tags"]["options"], is_multiselect=True, entry_width=35, field_key="facility_tags"
        )

        # 服務標籤 (固定寬 350, 高 150)
        service_col = ttk.Frame(row2_frame, width=350, height=150)
        service_col.pack(side=tk.LEFT)
        service_col.pack_propagate(False)
        self.create_form_field_in_parent(
            service_col, UI_CONFIG["service_tags"]["label"], self.tags_var, UI_CONFIG["service_tags"]["desc"], 
            entry_width=35 # 這裡傳入 int
        )

        # 6. Level(等級)
        cfg = UI_CONFIG["review_labeled_level"]
        self.create_form_field(cfg["label"], self.review_labeled_level_var, cfg["desc"], entry_width=15, options=cfg["options"])

        # 5. Flavor(口味)
        cfg = UI_CONFIG["flavor"]
        self.create_form_field(cfg["label"], self.flavor_var, cfg["desc"])
        
        # [修改後]
        cfg = UI_CONFIG["summary"]
        lbl_summary = ttk.Label(self.scrollable_frame, text=cfg["label"], font=("Arial", 10, "bold"))
        lbl_summary.pack(anchor=tk.W, padx=10, pady=(15, 0))
        
        lbl_summary_desc = ttk.Label(self.scrollable_frame, text=cfg["desc"], font=("Arial", 9), foreground="#aaaaaa")
        lbl_summary_desc.pack(anchor=tk.W, padx=10, pady=(0, 5))
        
        # 使用 ScrolledText 來取代單行的 Entry
        self.txt_summary = scrolledtext.ScrolledText(
            self.scrollable_frame, 
            width=80, 
            height=3,    # 設定為 3 行，這樣視覺上就會有「多行」的感覺
            font=("Arial", 10),
            bg="#3e3e3e", 
            fg="#ffffff", 
            insertbackground="white", 
            selectbackground="#4a90e2",
            wrap=tk.WORD
        )
        self.txt_summary.pack(fill=tk.X, padx=10, pady=5)

        # 9. Review Text(完整評論內容)
        cfg = UI_CONFIG["review_text"]
        lbl_review = ttk.Label(self.scrollable_frame, text=cfg["label"], font=("Arial", 10, "bold"))
        lbl_review.pack(anchor=tk.W, padx=10, pady=(15, 0))
        
        lbl_review_desc = ttk.Label(self.scrollable_frame, text=cfg["desc"], font=("Arial", 9), foreground="#aaaaaa")
        lbl_review_desc.pack(anchor=tk.W, padx=10, pady=(0, 5))

        # 請確保這段在程式碼中：
        self.txt_review = scrolledtext.ScrolledText(
            self.scrollable_frame, 
            width=80,    # 給定基礎寬度
            height=8,    # 這裡的高度代表「行數」。設為 8 代表至少能顯示 8 行文字
            font=("Arial", 10),
            bg="#3e3e3e", 
            fg="#ffffff", 
            insertbackground="white", 
            selectbackground="#4a90e2",
        )
        # fill=tk.BOTH 會讓它填滿整個右側區域，而不會被擠壓
        self.txt_review.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.btn_apply = ttk.Button(self.scrollable_frame, text="✅ 套用變更 (Apply)", command=self.save_current_to_memory)
        self.btn_apply.pack(fill=tk.X, padx=10, pady=20)

        # 1. 在這裡定義哪些欄位需要「自動記憶與同步」
        self.MEMORY_FIELDS = ["merchant_category", "food_type", "cuisine_type", "facility_tags","service_tags"]


        # 2. 建立「欄位名稱」對應「UI元件」的字典
        # 程式會根據這裡的對應，自動去抓取或填入資料
        self.field_ui_map = {
            "merchant_category": self.merchant_category_var,
            "food_type": self.food_type_dropdown,
            "cuisine_type": self.cuisine_dropdown,
            "facility_tags": self.facility_dropdown,
            "service_tags": self.tags_var  
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
        
        # 按鈕設定 (原本的)
        style.configure("TButton", background="#3e3e3e", foreground=fg_color, borderwidth=1, focuscolor=select_bg)
        style.map("TButton", background=[("active", select_bg)], foreground=[("active", "white")])
        
        # ➕ [新增] 專門給「新增選項」用的精緻小按鈕樣式
        # 透過 padding=(左右內邊距, 上下內邊距) 來把高度「壓扁」
        style.configure("Small.TButton", 
                        background="#4a90e2",      # 預設用藍色，看起來更醒目、有提示感
                        foreground="white", 
                        font=("Arial", 7),         # 字型稍微縮小一點點
                        borderwidth=1, 
                        padding=(6, 0))            # 上下 padding 設為 1，高度就會縮得很精緻
                        
        style.map("Small.TButton", 
                  background=[("active", "#357abd")], # 懸停時變成深藍色
                  foreground=[("active", "white")])
        
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

    def create_form_field_in_parent(self, parent, label_text, variable, description="", entry_width=40, options=None, readonly=False, is_multiselect=False, field_key=None):
        """輔助方法：確保高度統一且底部對齊，並在 Label 旁加入彈出式新增按鈕"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=5)
        
        # 標題列：用來放標題文字與按鈕
        title_frame = ttk.Frame(frame)
        title_frame.pack(fill=tk.X, anchor=tk.W)
        
        lbl_title = ttk.Label(title_frame, text=label_text, font=("Arial", 10, "bold"))
        lbl_title.pack(side=tk.LEFT)
        
        # 主輸入控制項變數，預先宣告
        entry_main = None
        
        # 只有特定的這三個欄位，才在 Label 旁塞入「➕ 新增選項」按鈕
        if field_key in ["merchant_category", "food_type", "cuisine_type", "facility_tags"] and options is not None:
            btn_add = ttk.Button(
                title_frame, text="➕ 新增選項", 
                style="Small.TButton", 
                command=lambda: self.pop_add_option_window(field_key, lambda: entry_main)
            )
            btn_add.pack(side=tk.LEFT, padx=(10, 3))
        
        # 描述 (處理 wraplength 自動換行)
        if description:
            lbl_desc = ttk.Label(
                frame, text=description, font=("Arial", 9), 
                foreground="#aaaaaa", justify="left", wraplength=320 
            )
            lbl_desc.pack(anchor=tk.W, pady=(2, 3))
        
        # 輸入控制項擺放於底部
        if is_multiselect and options:
            dropdown = MultiSelectDropdown(frame, options, width=entry_width)
            dropdown.pack(side=tk.BOTTOM, anchor=tk.W, fill=tk.X, pady=(0, 5))
            entry_main = dropdown
            return dropdown 
        elif options:
            entry = ttk.Combobox(frame, textvariable=variable, values=options, width=entry_width)
            entry['state'] = 'readonly' 
            entry.pack(side=tk.BOTTOM, anchor=tk.W, fill=tk.X, pady=(0, 5))
            entry_main = entry
            return None
        else:
            entry = ttk.Entry(frame, textvariable=variable, width=entry_width)
            entry.pack(side=tk.BOTTOM, anchor=tk.W, fill=tk.X, pady=(0, 5))
            if readonly:
                entry.config(state='readonly')
            return None

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
        
    

    
    def pop_add_option_window(self, field_key, get_ui_widget_func):
        """彈出一個獨立的小視窗，供用戶輸入要新增的選項名稱（精準置中版）"""
        field_name = UI_CONFIG[field_key].get("label", field_key)
        
        pop = tk.Toplevel(self.root)
        pop.title(f"新增選項 - {field_key}")
        
        # 1. 定義彈出視窗自己的寬高
        pop_width = 380
        pop_height = 150
        pop.resizable(False, False)
        
        # 2. 【核心】強制更新主視窗幾何資訊，並計算置中座標
        self.root.update_idletasks() # 確保抓到最新的主視窗位置與大小
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        root_w = self.root.winfo_width()
        root_h = self.root.winfo_height()
        
        # 計算置中位置的 X 與 Y 座標
        center_x = root_x + (root_w // 2) - (pop_width // 2)
        center_y = root_y + (root_h // 2) - (pop_height // 2)
        
        # 3. 套用幾何設定（寬x高+X+Y）
        pop.geometry(f"{pop_width}x{pop_height}+{center_x}+{center_y}")
        pop.configure(bg="#2d2d2d")
        
        # 讓視窗強行聚焦在最上層
        pop.transient(self.root)
        pop.grab_set()
        
        # --- 以下是原本的元件排版，保持不變 ---
        lbl_hint = ttk.Label(
            pop, text=f"請輸入要加進【{field_name}】的新選項：", 
            font=("Arial", 9, "bold"), background="#2d2d2d", foreground="#eeeeee"
        )
        lbl_hint.pack(anchor=tk.W, padx=20, pady=(15, 5))
        
        input_var = tk.StringVar()
        entry_input = ttk.Entry(pop, textvariable=input_var, font=("Arial", 10), width=35)
        entry_input.pack(fill=tk.X, padx=20, pady=5)
        entry_input.focus_set()
        
        btn_frame = tk.Frame(pop, background="#2d2d2d")
        btn_frame.pack(fill=tk.X, padx=20, pady=(15, 0))
        
        def confirm_action(event=None):
            ui_widget = get_ui_widget_func()
            success = self.execute_add_option(field_key, input_var.get().strip(), ui_widget)
            if success:
                pop.destroy()
        
        entry_input.bind("<Return>", confirm_action)
        
        btn_cancel = ttk.Button(btn_frame, text="取消", width=10, command=pop.destroy)
        btn_cancel.pack(side=tk.RIGHT, padx=(5, 0))
        
        btn_ok = ttk.Button(btn_frame, text="確認新增", width=12, command=confirm_action)
        btn_ok.pack(side=tk.RIGHT)

    def execute_add_option(self, field_key, new_value, ui_widget):
        """執行新增核對：更新內存、即時刷新主介面、並以絕對安全的結構格式覆寫 config.py"""
        if not new_value:
            messagebox.showwarning("提示", "欄位不可為空，請輸入有效名稱！")
            return False
            
        global UI_CONFIG, MEMORY_FIELDS
        current_options = UI_CONFIG[field_key].get("options", [])
        
        if new_value in current_options:
            messagebox.showwarning("提示", f"該選項「{new_value}」已經存在於列表內！")
            return False
            
        # 1. 更新內存
        current_options.append(new_value)
        UI_CONFIG[field_key]["options"] = current_options
        
        # 2. 同步刷新主畫面 UI
        if hasattr(ui_widget, 'options'):  
            ui_widget.options = current_options
            if hasattr(ui_widget, 'refresh'):  
                ui_widget.refresh()
        elif isinstance(ui_widget, ttk.Combobox):  
            ui_widget['values'] = current_options
            
        # 3. 【結構化安全升級】使用 pprint 或 repr 確保產生合法的 Python 語法結構，防止引號破壞
        config_path = os.path.join(os.path.dirname(__file__), "config.py")
        try:
            import pprint
            # 使用 pprint.pformat 可以確保輸出的是完美符合 Python 語法的字典字串，會自動處理引號轉義
            ui_config_str = pprint.pformat(UI_CONFIG, indent=4, width=120, compact=False)
            memory_fields_str = pprint.pformat(MEMORY_FIELDS, indent=4)
            
            # 拼湊成一個標準、乾淨、絕對合法的 config.py 內容
            new_file_content = (
                "# ./app/config.py\n"
                "# 自動產生的設定檔 - 結構防損壞保護\n\n"
                f"UI_CONFIG = {ui_config_str}\n\n"
                f"MEMORY_FIELDS = {memory_fields_str}\n"
            )
            
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(new_file_content)
                
            self.status_var.set(f"✅ 成功將新選項「{new_value}」寫入 config.py，結構完好無損！")
            return True
            
        except Exception as e:
            messagebox.showerror("配置檔寫入錯誤", f"無法成功儲存選項至 config.py: {e}")
            return False

    # --- 邏輯處理 ---
    def load_json(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if not file_path: return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                self.data_list = tool.process_data_on_load(json.load(f))
            self.filename = file_path

            self.store_info_cache = {}
            
            # =========== [修改開始] ===========
            for item in self.data_list:
                # 💡 修正：剛載入時 original_id 已被 tool.py 改名為 place_id 了！且轉為字串
                sid = str(item.get("place_id", "")).strip()
                if not sid: continue
                
                # 1. 初始化該店家的快取字典
                if sid not in self.store_info_cache:
                    self.store_info_cache[sid] = {}

                # 2. 動態遍歷你在 __init__ 設定的記憶欄位
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
        """根據搜尋關鍵字與模式，並依據 ID 數字大小排序，即時刷新列表內容"""
        self.listbox.delete(0, tk.END)
        query = self.search_var.get().strip().lower()
        mode = self.search_mode_var.get()

        # 1. 先打包「原始索引」與「資料內容」，方便過濾與排序
        display_items = []
        for idx, item in enumerate(self.data_list):
            place_id = str(item.get('place_id', '')).strip().lower()
            name = str(item.get('name', '')).strip().lower()
            
            # 搜尋過濾條件
            if query:
                if mode == "ID" and query not in place_id:
                    continue
                elif mode == "店名" and query not in name:
                    continue
            
            display_items.append((idx, item))

        # 2. 🎯 核心修正：依據 place_id 的「數字大小」進行排序 (2 排在 10 前面)
        def get_numeric_sort_key(element):
            _, item = element
            try:
                return int(float(str(item.get("place_id", 0))))
            except (ValueError, TypeError):
                return 0

        display_items.sort(key=get_numeric_sort_key)

        # 3. 將排序後的結果塞入 Listbox 渲染
        for idx, item in display_items:
            display_text = f"[{idx}] ID:{item.get('place_id', '?')} | {item.get('name', 'Unknown')}"
            self.listbox.insert(tk.END, display_text)

    def clear_search(self):
        """清空搜尋關鍵字並還原完整列表"""
        self.search_var.set("")
        self.search_entry.focus_set()

    def on_select(self, event):
        # 1. 先儲存上一筆 (如果有的話)
        if self.current_index is not None:
            self.save_current_to_memory()

        selection = self.listbox.curselection()
        if not selection: return
        
        # 💡 【核心修正】從視覺文字中提取原始 data_list 的真實索引
        visual_text = self.listbox.get(selection[0])
        try:
            # 提取第一個 "[" 和 "]" 之間的真實索引數字
            real_index = int(visual_text.split(']')[0].replace('[', ''))
        except (ValueError, IndexError):
            return

        self.current_index = real_index
        data = self.data_list[real_index]

        self.fill_form_with_data(data)

        # 2. 讀取 ID 與基本資料
        store_id = str(data.get("place_id", "")).strip()
        self.original_id_var.set(store_id)
        self.name_var.set(data.get("name", ""))
        self.review_labeled_level_var.set(str(data.get("review_labeled_level", "")))
        # [關鍵修正：填入 Summary]
        self.txt_summary.delete("1.0", tk.END)
        self.txt_summary.insert("1.0", data.get("review_summary", ""))

        # [關鍵修正：填入 Review Text]
        # 確認這裡是否有寫這兩行，若沒有請補上
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

            # A. 取得最優先的資料來源 (Data -> Cache)
            raw_val = data.get(field)
            
            if not raw_val and cache.get(field):
                raw_val = cache[field]
                data[field] = raw_val 
                auto_filled = True

            display_list = tool.normalize_to_list(raw_val, field)

            # 填入 UI
            if hasattr(ui_widget, 'set_selection'):
                ui_widget.set_selection(display_list)
            elif isinstance(ui_widget, tk.StringVar):
                if field == "merchant_category":
                    ui_widget.set(display_list[0] if display_list else "")
                else:
                    ui_widget.set(", ".join(display_list))

        status_msg = f"正在編輯第 {real_index} 筆資料"
        if auto_filled: 
            status_msg += " (已自動帶入店家資訊)"
        self.status_var.set(status_msg)

    def handle_nav_keys(self, event):
        # 1. 如果焦點在列表上，完全不處理
        if self.root.focus_get() == self.listbox:
            return "break"
            
        # 2. 確保是按下 Control + 方向鍵才觸發
        # event.state & 0x0004 檢查是否有按住 Control 鍵
        if event.state & 0x0004:
            if event.keysym == "Right":
                self.go_next()
                return "break"
            elif event.keysym == "Left":
                self.go_prev()
                return "break"

    def go_prev(self):
        if self.current_index is None: return
        if self.current_index > 0:
            self.navigate_to(self.current_index - 1)
        else:
            messagebox.showinfo("提示", "已經是第一筆了")

    def go_next(self):
        if self.current_index is None: return
        if self.current_index < len(self.data_list) - 1:
            self.navigate_to(self.current_index + 1)
        else:
            messagebox.showinfo("提示", "已經是最後一筆了")

    def navigate_to(self, new_index):
        # 這裡會觸發 save_current_to_memory()
        self.save_current_to_memory()
        
        self.current_index = new_index
        self.listbox.select_clear(0, tk.END)
        self.listbox.select_set(new_index)
        self.listbox.see(new_index) 
        
        # 這裡直接填入資料，而不要觸發 <<ListboxSelect>>
        self.fill_form_with_data(self.data_list[new_index])

    def fill_form_with_data(self, data):
        """同步更新所有 UI 變數與內容"""
        # 1. 更新基本文字變數 (StringVars)
        self.original_id_var.set(str(data.get("place_id", "")))
        self.name_var.set(data.get("name", ""))
        self.review_labeled_level_var.set(str(data.get("review_labeled_level", "")))
        
        # 處理 Flavor
        flavors = data.get("flavor", [])
        self.flavor_var.set(", ".join(flavors) if isinstance(flavors, list) else str(flavors))
        
        # 2. 更新文字編輯區
        self.txt_summary.delete("1.0", tk.END)
        self.txt_summary.insert("1.0", data.get("review_summary", ""))
        
        self.txt_review.delete("1.0", tk.END)
        self.txt_review.insert("1.0", data.get("review_text", ""))

        # 3. 觸發 dropdown 記憶欄位的更新 (這步最關鍵，確保食物類型/菜系跳轉)
        store_id = str(data.get("place_id", "")).strip()
        cache = self.store_info_cache.get(store_id, {})
        
        for field in self.MEMORY_FIELDS:
            ui_widget = self.field_ui_map.get(field)
            if not ui_widget: continue
            
            raw_val = data.get(field) or cache.get(field)
            display_list = tool.normalize_to_list(raw_val, field)
            
            if hasattr(ui_widget, 'set_selection'):
                ui_widget.set_selection(display_list)
            elif isinstance(ui_widget, tk.StringVar):
                if field == "merchant_category":
                    ui_widget.set(display_list[0] if display_list else "")
                else:
                    ui_widget.set(", ".join(display_list))
    def save_current_to_memory(self):
        if self.current_index is None: return
        try:
            store_id = self.original_id_var.get()
            
            # (A) 取得「記憶欄位」資料
            current_memory_values = {}
            for field in self.MEMORY_FIELDS:
                ui_widget = self.field_ui_map.get(field)
                if not ui_widget: continue

                # 統一拿取 UI 的值
                if hasattr(ui_widget, 'get_selection'):
                    raw_ui_val = ui_widget.get_selection()
                else:
                    raw_ui_val = ui_widget.get()

                # 呼叫工具轉換格式 (傳入對應的 options)
                current_memory_values[field] = tool.format_value_for_save(
                    field, 
                    raw_ui_val, 
                    UI_CONFIG.get(field, {}).get("options")
                )
                # ------------------------------------

            # [新增] 定義一個簡單的清洗函數，移除無效的代理對
            def sanitize_text(text):
                if not isinstance(text, str): return text
                # 將字串以 utf-8 編碼再解碼，使用 errors='ignore' 來拋棄非法字元
                return text.encode('utf-8', 'ignore').decode('utf-8')

            # 2. 取得並清洗「單筆獨有」欄位資料
            unique_data = tool.clean_unique_data(
                sanitize_text(self.name_var.get()),
                sanitize_text(self.txt_summary.get("1.0", tk.END).strip()), # 確保這裡是用 txt_summary
                sanitize_text(self.txt_review.get("1.0", tk.END).strip()), # 確保這裡是 txt_review
                sanitize_text(self.review_labeled_level_var.get()),
                sanitize_text(self.flavor_var.get())
            )

            # 3. 呼叫 tool 執行批次更新
            self.data_list, count = tool.update_data_list_batch(
                self.data_list,
                self.current_index,
                store_id,
                unique_data,
                current_memory_values
            )

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
        
        # 1. 取得當前滾動位置 (返回 tuple: (start, end))
        current_yview = self.listbox.yview()
        
        current_data = self.data_list[self.current_index]
        new_entry = {
            "place_id": current_data.get("place_id", ""),
            "name": current_data.get("name", ""),
            "review_summary": "",
            "review_text": "", 
            "food_type": current_data.get("food_type", ""),
            "cuisine_type": current_data.get("cuisine_type", []), 
            "flavor": [],
            "service_tags": [],
            "review_labeled_level": ""
        }
        insert_pos = self.current_index + 1
        self.data_list.insert(insert_pos, new_entry)
        
        # 2. 刷新列表
        self.refresh_listbox()
        
        # 3. 執行選取
        self.listbox.select_clear(0, tk.END)
        self.listbox.select_set(insert_pos)
        self.listbox.event_generate("<<ListboxSelect>>")
        
        # 4. 強制還原滾動位置
        # moveto 接收一個 0.0 到 1.0 的浮點數，current_yview[0] 正好是原本的起點
        self.listbox.yview_moveto(current_yview[0])
        
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
        self.review_labeled_level_var.set("")
        self.summary_var.set("")

        # [手動清空] 服務標籤
        self.tags_var.set("")
        


        # =========== [自動清空記憶欄位] ===========
        # 這邊只會清空還留在 MEMORY_FIELDS 裡的 (food_type, cuisine_type)
        for field in self.MEMORY_FIELDS:
            ui_widget = self.field_ui_map.get(field)
            if ui_widget:
                if hasattr(ui_widget, 'set_selection'):
                    ui_widget.set_selection([])
                elif hasattr(ui_widget, 'set'):
                    # 💡 修正：加上 .set("") 以支援 StringVar (例如 merchant_category)
                    ui_widget.set("")
        # =======================================
        self.txt_summary.delete("1.0", tk.END)
        self.txt_review.delete("1.0", tk.END)
        
    # [新增] 快速存檔 (直接寫入當前檔案)
    def quick_save(self):
        if not self.data_list:
            messagebox.showwarning("警告", "沒有資料可以儲存")
            return
        
        if not self.filename:
            self.save_as_json()
            return

        # 先把當前編輯的內容同步進 self.data_list 內存
        if self.current_index is not None:
            self.save_current_to_memory()

        try:
            # 💡 安全關鍵：完全交由 json.dump 處理序列化，並強制指定 utf-8 確保中文字不亂碼
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump(self.data_list, f, ensure_ascii=False, indent=4)
            
            self.status_var.set(f"💾 已儲存至原檔: {os.path.basename(self.filename)}")
        except Exception as e:
            messagebox.showerror("錯誤", f"存檔失敗: {e}")

    # [修改] 另存新檔
    def save_as_json(self):
        if not self.data_list:
            messagebox.showwarning("警告", "沒有資料可以儲存")
            return
        
        if self.current_index is not None:
            self.save_current_to_memory()
            
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if not file_path: return
        
        try:
            # 💡 安全關鍵：完全交由 json.dump 處理序列化
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.data_list, f, ensure_ascii=False, indent=4)
            
            self.filename = file_path 
            messagebox.showinfo("成功", f"檔案已儲存至:\n{file_path}")
            self.status_var.set(f"💾 已另存: {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("錯誤", f"存檔失敗: {e}")