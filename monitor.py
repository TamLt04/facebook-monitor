import requests
import json
import os
from datetime import datetime
import hashlib
import re

# Config
FACEBOOK_URL = "https://www.facebook.com/setiawan.djordy.507"
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

def get_page_content():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }
    
    try:
        print(f"🔍 Đang truy cập: {FACEBOOK_URL}")
        response = requests.get(FACEBOOK_URL, headers=headers, timeout=30)
        print(f"📊 Status code: {response.status_code}")
        print(f"📏 Content length: {len(response.text)} chars")
        return response.text
    except Exception as e:
        print(f"❌ Lỗi khi lấy trang: {e}")
        return None

def extract_content_hash(html_content):
    """Tạo hash từ nội dung HTML để phát hiện thay đổi"""
    try:
        # Làm sạch HTML đơn giản bằng regex thay vì BeautifulSoup
        # Loại bỏ script và style tags
        html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        
        # Loại bỏ HTML tags
        text_content = re.sub(r'<[^>]+>', ' ', html_content)
        
        # Làm sạch whitespace
        text_content = re.sub(r'\s+', ' ', text_content).strip()
        
        # Lấy 2000 ký tự đầu để tạo hash
        relevant_content = text_content[:2000]
        
        # Tạo hash
        content_hash = hashlib.md5(relevant_content.encode('utf-8', errors='ignore')).hexdigest()
        
        # Preview 200 ký tự đầu
        preview = text_content[:200] if text_content else "Không có nội dung"
        
        return {
            'hash': content_hash,
            'preview': preview,
            'timestamp': datetime.now().isoformat(),
            'content_length': len(text_content)
        }
        
    except Exception as e:
        print(f"❌ Lỗi parse HTML: {e}")
        # Fallback: dùng raw HTML để tạo hash
        content_hash = hashlib.md5(html_content[:1000].encode('utf-8', errors='ignore')).hexdigest()
        return {
            'hash': content_hash,
            'preview': "Lỗi parse HTML, dùng raw content",
            'timestamp': datetime.now().isoformat(),
            'content_length': len(html_content)
        }

def send_telegram_message(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Chưa config BOT_TOKEN hoặc CHAT_ID")
        return False
        
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
    }
    
    try:
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            print(f"✅ Gửi thông báo Telegram thành công")
            return True
        else:
            print(f"❌ Lỗi Telegram API: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Lỗi gửi Telegram: {e}")
        return False

def load_last_state():
    try:
        with open('last_state.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("📄 Không tìm thấy file state, đây là lần chạy đầu tiên")
        return None
    except Exception as e:
        print(f"❌ Lỗi đọc state file: {e}")
        return None

def save_state(state):
    try:
        with open('last_state.json', 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        print("💾 Đã lưu state mới")
    except Exception as e:
        print(f"❌ Lỗi lưu state: {e}")

def main():
    print(f"\n🕐 === BẮT ĐẦU KIỂM TRA LÚC {datetime.now().strftime('%H:%M:%S %d/%m/%Y')} ===")
    
    # Test cấu hình
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Thiếu cấu hình BOT_TOKEN hoặc CHAT_ID")
        print("Hãy kiểm tra Settings → Secrets and variables → Actions")
        return
    
    print(f"✅ Bot Token: {BOT_TOKEN[:10]}...")
    print(f"✅ Chat ID: {CHAT_ID}")
    
    # Lấy nội dung trang
    html_content = get_page_content()
    if not html_content:
        print("❌ Không thể lấy nội dung trang")
        return
    
    # Phân tích nội dung
    current_state = extract_content_hash(html_content)
    print(f"🔢 Hash hiện tại: {current_state['hash']}")
    print(f"📝 Preview: {current_state['preview'][:100]}...")
    
    # So sánh với lần kiểm tra trước
    last_state = load_last_state()
    
    if last_state is None:
        print("🚀 Lần đầu chạy, lưu trạng thái hiện tại")
        save_state(current_state)
        
        # Gửi thông báo khởi động
        startup_message = f"""
🤖 <b>FACEBOOK MONITOR KHỞI ĐỘNG</b>

✅ Bot đã sẵn sàng giám sát trang Facebook
⏰ Kiểm tra: Mỗi phút
📱 Trang: <a href="{FACEBOOK_URL}">Setiawan Djordy</a>

📊 Trạng thái ban đầu:
- Hash: {current_state['hash'][:8]}...
- Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}
- Kích thước: {current_state['content_length']} chars

🔔 Sẽ thông báo khi có bài viết mới!
"""
        send_telegram_message(startup_message)
        return
    
    if current_state['hash'] != last_state['hash']:
        print("🆕 PHÁT HIỆN THAY ĐỔI!")
        
        message = f"""
🚨 <b>TRANG FACEBOOK CÓ CẬP NHẬT MỚI!</b>

📱 <a href="{FACEBOOK_URL}">➡️ XEM NGAY TRANG FACEBOOK</a>
⏰ Phát hiện lúc: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}

📊 Chi tiết:
- Hash cũ: {last_state['hash'][:8]}...
- Hash mới: {current_state['hash'][:8]}...
- Thay đổi kích thước: {current_state['content_length'] - last_state.get('content_length', 0)} chars

💬 Preview nội dung:
{current_state['preview'][:300]}...

⚡ Được phát hiện trong vòng 1 phút!
"""
        
        if send_telegram_message(message):
            save_state(current_state)
        else:
            print("❌ Không gửi được thông báo, không lưu state")
    else:
        print("✅ Không có thay đổi")
    
    print(f"🏁 === KẾT THÚC KIỂM TRA ===\n")

if __name__ == "__main__":
    main()
