import requests
import json
import os
from datetime import datetime, timezone
import hashlib
import re
import time

# Config

FACEBOOK_URL = “https://www.facebook.com/setiawan.djordy.507?locale=vi_VN”
BOT_TOKEN = os.environ.get(‘BOT_TOKEN’)
CHAT_ID = os.environ.get(‘CHAT_ID’)

def get_page_content():
headers = {
‘User-Agent’: ‘Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36’,
‘Accept’: ‘text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8’,
‘Accept-Language’: ‘vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7’,
‘Accept-Encoding’: ‘gzip, deflate, br’,
‘Connection’: ‘keep-alive’,
‘Upgrade-Insecure-Requests’: ‘1’,
‘Sec-Fetch-Dest’: ‘document’,
‘Sec-Fetch-Mode’: ‘navigate’,
‘Sec-Fetch-Site’: ‘none’,
‘Cache-Control’: ‘no-cache’,
‘Pragma’: ‘no-cache’
}

```
# Thử nhiều lần để đảm bảo lấy được nội dung
for attempt in range(2):  # Giảm từ 3 xuống 2 lần thử
    try:
        print(f"🔍 Lần thử {attempt + 1}: Truy cập Facebook...")
        response = requests.get(FACEBOOK_URL, headers=headers, timeout=30, allow_redirects=True)
        
        if response.status_code == 200:
            print(f"✅ OK! Size: {len(response.text)} chars")
            return response.text
        else:
            print(f"⚠️ Status {response.status_code}")
            if attempt < 1:
                time.sleep(2)
            
    except Exception as e:
        print(f"❌ Lỗi lần {attempt + 1}: {str(e)[:100]}")
        if attempt < 1:
            time.sleep(2)

print("❌ Không truy cập được Facebook")
return None
```

def extract_content_hash(html_content):
“”“Tạo hash đơn giản nhưng hiệu quả”””
try:
# Làm sạch HTML cơ bản
clean_content = re.sub(r’<script[^>]*>.*?</script>’, ‘’, html_content, flags=re.DOTALL | re.IGNORECASE)
clean_content = re.sub(r’<style[^>]*>.*?</style>’, ‘’, clean_content, flags=re.DOTALL | re.IGNORECASE)

```
    # Loại bỏ HTML tags
    text_content = re.sub(r'<[^>]+>', ' ', clean_content)
    text_content = re.sub(r'\s+', ' ', text_content).strip()
    
    # Tạo hash từ phần đầu trang (nơi bài mới xuất hiện)
    relevant_content = text_content[:4000]  # 4000 ký tự đầu
    content_hash = hashlib.md5(relevant_content.encode('utf-8', errors='ignore')).hexdigest()
    
    return {
        'hash': content_hash,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'content_length': len(text_content),
        'sample': text_content[:200]  # Mẫu để debug
    }
    
except Exception as e:
    print(f"❌ Lỗi parse: {e}")
    # Fallback
    fallback_hash = hashlib.md5(html_content[:2000].encode('utf-8', errors='ignore')).hexdigest()
    return {
        'hash': fallback_hash,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'content_length': len(html_content),
        'sample': "Fallback mode",
        'fallback': True
    }
```

def send_telegram_message(message):
if not BOT_TOKEN or not CHAT_ID:
print(“❌ Thiếu config”)
return False

```
url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

try:
    data = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
    }
    
    response = requests.post(url, data=data, timeout=10)
    
    if response.status_code == 200:
        print(f"✅ Đã gửi: {message}")
        return True
    else:
        print(f"❌ Telegram lỗi: {response.status_code}")
        return False
        
except Exception as e:
    print(f"❌ Lỗi gửi: {e}")
    return False
```

def load_last_state():
“”“Load state từ file hoặc từ biến môi trường”””
# Thử đọc từ file trước
try:
if os.path.exists(‘last_state.json’):
with open(‘last_state.json’, ‘r’, encoding=‘utf-8’) as f:
data = json.load(f)
print(f”📄 Đọc state từ file: {data[‘hash’][:8]}…”)
return data
except Exception as e:
print(f”⚠️ Lỗi đọc file state: {e}”)

```
# Thử đọc từ environment variable (backup method)
try:
    state_env = os.environ.get('LAST_STATE')
    if state_env:
        data = json.loads(state_env)
        print(f"📄 Đọc state từ env: {data['hash'][:8]}...")
        return data
except Exception as e:
    print(f"⚠️ Lỗi đọc env state: {e}")

print("📄 Không có state cũ")
return None
```

def save_state(state):
“”“Lưu state vào file và biến môi trường”””
try:
# Lưu vào file
with open(‘last_state.json’, ‘w’, encoding=‘utf-8’) as f:
json.dump(state, f, ensure_ascii=False, indent=2)

```
    # Lưu vào environment variable làm backup
    os.environ['LAST_STATE'] = json.dumps(state, ensure_ascii=False)
    
    print(f"💾 Lưu state: {state['hash'][:8]}...")
    return True
except Exception as e:
    print(f"❌ Lỗi lưu state: {e}")
    return False
```

def main():
start_time = datetime.now()
print(f”\n🕐 === KIỂM TRA {start_time.strftime(’%H:%M:%S’)} ===”)

```
# Kiểm tra config
if not BOT_TOKEN or not CHAT_ID:
    print("❌ Thiếu BOT_TOKEN hoặc CHAT_ID")
    return

print(f"✅ Config OK")

# Lấy nội dung Facebook
html_content = get_page_content()
if not html_content:
    print("❌ Không truy cập được Facebook - skip lần này")
    return

# Phân tích nội dung
current_state = extract_content_hash(html_content)
print(f"🔢 Hash: {current_state['hash'][:12]}...")

# Load state cũ
last_state = load_last_state()

# So sánh và quyết định
if last_state is None:
    print("🚀 Lần đầu setup - KHÔNG GỬI THÔNG BÁO")
    save_state(current_state)
    # KHÔNG gửi thông báo khởi động nữa
    print("💾 Đã lưu state đầu tiên")
    return

# Kiểm tra thay đổi
if current_state['hash'] != last_state['hash']:
    print("🆕 PHÁT HIỆN THAY ĐỔI!")
    
    # CHỈ GỬI THÔNG BÁO KHI CÓ BÀI MỚI
    message = "Có bài viết mới từ Ren Devor"
    
    if send_telegram_message(message):
        save_state(current_state)
        print("✅ Đã xử lý thành công")
    else:
        print("❌ Gửi thông báo thất bại - giữ nguyên state")
else:
    print("✅ Không có thay đổi")

# Thống kê
duration = (datetime.now() - start_time).total_seconds()
print(f"⏱️ Mất {duration:.1f}s")
print("🏁 === XONG ===\n")
```

if **name** == “**main**”:
main()
