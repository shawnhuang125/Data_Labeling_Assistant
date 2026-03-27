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

        # 右側：店家類型 (固定寬 350, 高 100)
        category_col = ttk.Frame(name_row_frame, width=350, height=100)
        category_col.pack(side=tk.LEFT)
        category_col.pack_propagate(False)
        cfg_cat = UI_CONFIG["merchant_category"]
        self.create_form_field_in_parent(
            category_col, cfg_cat["label"], self.merchant_category_var, 
            cfg_cat["desc"], options=cfg_cat["options"], entry_width=35
        )

        # --- 第一組併排：食物類型 & 料理菜系 ---
        row1_frame = ttk.Frame(self.scrollable_frame)
        row1_frame.pack(fill=tk.X, padx=10, pady=0, anchor=tk.W)

        # 食物類型 (固定寬 350, 高 150)
        food_col = ttk.Frame(row1_frame, width=350, height=150)
        food_col.pack(side=tk.LEFT, padx=(0, 20))
        food_col.pack_propagate(False)
        self.food_type_dropdown = self.create_form_field_in_parent(
            food_col, UI_CONFIG["food_type"]["label"], None, UI_CONFIG["food_type"]["desc"], 
            options=UI_CONFIG["food_type"]["options"], is_multiselect=True, entry_width=35
        )

        # 料理菜系 (固定寬 350, 高 150)
        cuisine_col = ttk.Frame(row1_frame, width=350, height=150)
        cuisine_col.pack(side=tk.LEFT)
        cuisine_col.pack_propagate(False)
        self.cuisine_dropdown = self.create_form_field_in_parent(
            cuisine_col, UI_CONFIG["cuisine_type"]["label"], None, UI_CONFIG["cuisine_type"]["desc"], 
            options=UI_CONFIG["cuisine_type"]["options"], is_multiselect=True, entry_width=35
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
            options=UI_CONFIG["facility_tags"]["options"], is_multiselect=True, entry_width=35
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
        cfg = UI_CONFIG.get("review_labeled_level", UI_CONFIG.get("level", {}))
        self.create_form_field(cfg.get("label", "評論標記等級"), self.review_labeled_level_var, cfg.get("desc", ""), entry_width=15, options=cfg.get("options", []))

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

    def create_form_field_in_parent(self, parent, label_text, variable, description="", entry_width=40, options=None, readonly=False, is_multiselect=False):
        """輔助方法：確保高度統一且底部對齊，並修正類型警告"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=5)
        
        # 標題
        lbl_title = ttk.Label(frame, text=label_text, font=("Arial", 10, "bold"))
        lbl_title.pack(anchor=tk.W)
        
        # 描述 (使用 wraplength 處理自動換行，避免撐開容器)
        if description:
            lbl_desc = ttk.Label(
                frame, text=description, font=("Arial", 9), 
                foreground="#aaaaaa", justify="left", wraplength=320 
            )
            lbl_desc.pack(anchor=tk.W, pady=(0, 3))
        
        # 輸入控制項：統一放置於底部 (tk.BOTTOM)
        if is_multiselect and options:
            dropdown = MultiSelectDropdown(frame, options, width=entry_width)
            dropdown.pack(side=tk.BOTTOM, anchor=tk.W, fill=tk.X, pady=(0, 5))
            return dropdown 
        elif options:
            entry = ttk.Combobox(frame, textvariable=variable, values=options, width=entry_width)
            entry['state'] = 'readonly' 
            entry.pack(side=tk.BOTTOM, anchor=tk.W, fill=tk.X, pady=(0, 5))
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
        self.listbox.delete(0, tk.END)
        for idx, item in enumerate(self.data_list):
            display_text = f"[{idx}] ID:{item.get('place_id', '?')} | {item.get('name', 'Unknown')}"
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
        store_id = str(data.get("place_id", "")).strip()
        self.original_id_var.set(store_id)
        self.name_var.set(data.get("name", ""))
        self.review_labeled_level_var.set(str(data.get("review_labeled_level", "")))
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

        status_msg = f"正在編輯第 {index} 筆資料"
        if auto_filled: 
            status_msg += " (已自動帶入店家資訊)"
        self.status_var.set(status_msg)

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

            # 2. 取得並清洗「單筆獨有」欄位資料
            unique_data = tool.clean_unique_data(
                self.name_var.get(),
                self.summary_var.get(),
                self.txt_review.get("1.0", tk.END),
                self.review_labeled_level_var.get(),
                self.flavor_var.get()
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