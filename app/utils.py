# app/utils.py
import os
import json
from dotenv import load_dotenv # 確保 requirements.txt 有 python-dotenv

# 明確指定 .env 路徑 (避免它找不到)
basedir = os.path.abspath(os.path.dirname(__file__))
# 假設 .env 在 app/ 的上一層 (專案根目錄)
env_path = os.path.join(basedir, '..', '.env')
load_dotenv(env_path)

def load_config():
    """
    優先從環境變數讀取設定。
    """
    config = {
        'AD_SERVER': os.getenv('AD_SERVER'),
        'AD_BASEDN': os.getenv('AD_BASEDN'),
        'AD_USER': os.getenv('AD_USER'),
        'AD_PASS': os.getenv('AD_PASSWORD'), # 注意變數名稱
        'AD_DOMAIN': os.getenv('AD_DOMAIN'),
        'SECRET_KEY': os.getenv('FLASK_SECRET_KEY', 'dev-key-please-change')
    }

    # Debug: 印出來確認到底有沒有讀到 (看 Docker Log)
    print(f"DEBUG: Loaded AD_SERVER: {config['AD_SERVER']}")

    # Fallback: 如果環境變數空的，試試看讀舊的 config.json
    if not config['AD_SERVER']:
        json_path = os.path.join(basedir, '..', 'data', 'config.json')
        if os.path.exists(json_path):
            print("DEBUG: Fallback to config.json")
            try:
                with open(json_path, 'r') as f:
                    file_config = json.load(f)
                    for key, value in file_config.items():
                        if not config.get(key):
                            config[key] = value
            except Exception as e:
                print(f"Warning: Failed to load config.json: {e}")

    return config

def check_configured():
    config = load_config()
    return all([config.get('AD_SERVER'), config.get('AD_USER'), config.get('AD_PASS')])

def save_config(data):
    # 維持相容性，寫入 json
    try:
        json_path = os.path.join(basedir, '..', 'data', 'config.json')
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False