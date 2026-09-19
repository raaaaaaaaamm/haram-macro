import json
import os

CONFIG_FILE = os.path.expanduser('~/.haram_macro_config.json')

def get_default_config():
    return {
        'custom_text_enabled': False,
        'custom_text': '',
        'fixed_keys': {str(k): {'enabled': False, 'interval': 1.0} for k in list(range(1, 10)) + ['0']},
        'custom_keys': {f'custom_{i}': {'enabled': False, 'key': '', 'interval': 1.0} for i in range(1, 7)}
    }

def load_all_slots():
    if not os.path.exists(CONFIG_FILE):
        default_slots = {str(i): get_default_config() for i in range(1, 6)}
        save_all_slots(default_slots)
        return default_slots
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {str(i): get_default_config() for i in range(1, 6)}

def save_all_slots(slots_data):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(slots_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print('Failed to save config:', e)
