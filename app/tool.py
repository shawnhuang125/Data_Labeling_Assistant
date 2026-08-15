# ./app/tool.py
import json

def process_data_on_load(data_list):
    """
    1. 將 original_id 欄位名稱統一改為 place_id
    2. 依照 place_id 由小到大排列
    """
    for item in data_list:
        if "original_id" in item:
            item["place_id"] = item.pop("original_id")
    
    # 排序：確保相同的 ID 排在一起
    return sorted(data_list, key=lambda x: str(x.get("place_id", "")))

def normalize_to_list(raw_val, field_name):
    """
    現在 facility_tags 已經是 List，直接回傳。
    如果原始資料是 None，則回傳空 List。
    """
    if raw_val is None:
        return []
    
    # 如果原本還有殘留的字串格式（例如 "A, B"），依然保留拆分邏輯以防萬一
    if isinstance(raw_val, str):
        return [t.strip() for t in raw_val.split(",") if t.strip()]
    
    # 這裡就是關鍵：直接回傳 List
    return raw_val if isinstance(raw_val, list) else [raw_val]

def convert_to_save_format(selected_list, field_name, all_options=None):
    """
    將 UI 的 List 轉回 JSON 儲存格式
    對應原邏輯：將 facility_tags 轉回 dict {"opt": "true/false"}
    """
    if field_name == "facility_tags" and all_options:
        tag_dict = {}
        for opt in all_options:
            tag_dict[opt] = "true" if opt in selected_list else "false"
        return tag_dict
    
    # 其他如 merchant_category, food_type 等維持原本格式
    return selected_list

def format_value_for_save(field, ui_value, all_options=None):
    """
    儲存時不再轉為字典，直接儲存 UI 選取的 List。
    """
    # 移除原本 facility_tags 轉 dict 的那段 if
    if field == "merchant_category":
        return str(ui_value).strip()

    if isinstance(ui_value, str):
        if not ui_value.strip(): return []
        return [t.strip() for t in ui_value.split(",") if t.strip()]
    # 直接回傳 UI 選取的清單 (例如 ["內用", "冷氣"])
    return ui_value

def clean_unique_data(name, summary, review_text, level_raw, flavor_str):
    """
    清洗單筆評論獨有的欄位（嚴格型態防禦版）
    """
    # 確保傳進來的都是字串，並剔除首尾空白與 Tkinter 的末尾換行
    cleaned_name = str(name).strip()
    cleaned_summary = str(summary).strip().rstrip('\n')
    cleaned_review_text = str(review_text).strip().rstrip('\n')
    
    # 【核心修正】統一保持為字串型態！絕對不要轉成 int
    # 這樣可以確保不論是寫入 JSON 還是與 config 交互，型態都是完全一致的 str
    cleaned_level = str(level_raw).strip()
    
    # 安全拆分口味標籤
    if isinstance(flavor_str, str):
        cleaned_flavor = [t.strip() for t in flavor_str.split(",") if t.strip()]
    else:
        cleaned_flavor = []
        
    return {
        "name": cleaned_name,
        "review_summary": cleaned_summary,
        "review_text": cleaned_review_text,
        "review_labeled_level": cleaned_level,
        "flavor": cleaned_flavor
    }

def update_data_list_batch(data_list, current_index, store_id, unique_data, memory_values):
    """
    執行資料更新邏輯：
    1. 更新當前編輯索引的那一筆
    2. 同步更新所有相同 place_id 的共通欄位
    """
    count = 0
    store_id_str = str(store_id).strip()
    for idx, item in enumerate(data_list):
        # A. 更新當前編輯的這筆獨有資料
        if idx == current_index:
            item.update(unique_data)
        
        # B. 只要 place_id 相同，就同步更新共通欄位 (merchant_category, food_type 等)
        # 注意：load 時已將 original_id 統一改名為 place_id
        if str(item.get("place_id", "")).strip() == store_id_str:
            for field, val in memory_values.items():
                if isinstance(val, (dict, list)):
                    item[field] = val.copy()
                else:
                    item[field] = val
            count += 1
            
    return data_list, count