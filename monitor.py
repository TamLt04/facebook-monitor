import requests
import json
import os
from datetime import datetime, timezone
import hashlib
import re
import time

# Config
FACEBOOK_URL = "https://www.facebook.com/setiawan.djordy.507?locale=vi_VN"
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

def get_page_content():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    }
    
    # Thử nhiều lần để đảm bảo lấy được nội dung
    for attempt in range(3):
        try:
            print(f"🔍 Lần thử {attempt + 1}: Đang truy cập Facebook...")
            response = requests.get(FACEBOOK_URL, headers=headers, timeout=45, allow_redirects=True)
            
            if response.status_code == 200:
                print(f"✅ Thành công! Size: {len(response.text)} chars")
                return response.text
            else:
                print(f"⚠️ Status {response.status_code}, thử lại...")
                time.sleep(2)
                
        except Exception as e:
            print(f"❌ Lần thử {attempt + 1} lỗi: {e}")
            if attempt < 2:
                time.sleep(3)
    
    print("❌ Không thể truy cập sau 3 lần thử")
    return None

def extract_multiple_hashes(html_content):
    """Tạo nhiều hash từ các phần khác nhau để phát hiện chính xác hơn"""
    try:
        # Làm sạch HTML
        clean_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        clean_content = re.sub(r'<style[^>]*>.*?</style>', '', clean_content, flags=re.DOTALL | re.IGNORECASE)
        clean_content = re.sub(r'<!--.*?-->', '', clean_content, flags=re.DOTALL)
        
        # Loại bỏ HTML tags
        text_content = re.sub(r'<[^>]+>', ' ', clean_content)
        text_content = re.sub(r'\s+', ' ', text_content).strip()
        
        # Tạo nhiều hash từ các phần khác nhau
        content_parts = {
            'full_hash': hashlib.md5(text_content[:5000].encode('utf-8', errors='ignore')).hexdigest(),
            'top_hash': hashlib.md5(text_content[:2000].encode('utf-8', errors='ignore')).hexdigest(),
            'mid_hash': hashlib.md5(text_content[1000:3000].encode('utf-8', errors='ignore')).hexdigest(),
            'posts_hash': hashlib.md5(text_content[:4000].encode('utf-8', errors='ignore')).hexdigest()
        }
        
        # Tạo hash tổng hợp
        combined = ''.join(content_parts.values())
        main_hash = hashlib.md5(combined.encode('utf-8')).hexdigest()
        
        return {
            'main_hash': main_hash,
            'content_parts': content_parts,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'content_length': len(text_content),
            'raw_length': len(html_content)
        }
        
    except Exception as e:
        print(f"❌ Lỗi parse HTML: {e}")
        # Fallback với raw content
        fallback_hash = hashlib.md5(html_content[:3000].encode('utf-8', errors='ignore')).hexdigest()
        return {
            'main_hash': fallback_hash,
            'content_parts': {'fallback': fallback_hash},
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'content_length': len(html_content),
            'raw_length': len(html_content),
            'fallback': True
        }

def send_telegram_message(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Thiếu BOT_TOKEN hoặc CHAT_ID")
        return False
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    # Thử gửi nhiều lần để đảm bảo thành công
    for attempt in range(3):
        try:
            data = {
                'chat_id': CHAT_ID,
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            }
            
            response = requests.post(url, data=data, timeout=15)
            
            if response.status_code == 200:
                print(f"✅ Đã gửi thông báo Telegram (lần {attempt + 1})")
                return True
            else:
                print(f"⚠️ Telegram lỗi {response.status_code}, thử lại...")
                time.sleep(1)
                
        except Exception as e:
            print(f"❌ Lần gửi {attempt + 1} lỗi: {e}")
            if attempt < 2:
                time.sleep(2)
    
    print("❌ Không gửi được sau 3 lần thử")
    return False

def load_last_state():
    try:
        with open('last_state.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("📄 Lần chạy đầu tiên - tạo state mới")
        return None
    except Exception as e:
        print(f"❌ Lỗi đọc state: {e}")
        return None

def save_state(state):
    try:
        # Backup state cũ trước khi ghi mới
        try:
            with open('last_state.json', 'r') as f:
                old_state = f.read()
            with open('last_state_backup.json', 'w') as f:
                f.write(old_state)
        except:
            pass
        
        # Ghi state mới
        with open('last_state.json', 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        print("💾 Đã lưu trạng thái mới")
        return True
    except Exception as e:
        print(f"❌ Lỗi lưu state: {e}")
        return False

def detect_changes(current_state, last_state):
    """Phát hiện thay đổi chính xác hơn"""
    if not last_state:
        return False, "Lần đầu chạy"
    
    # So sánh hash chính
    if current_state['main_hash'] != last_state['main_hash']:
        return True, "Hash chính thay đổi"
    
    # So sánh các hash phụ
    current_parts = current_state.get('content_parts', {})
    last_parts = last_state.get('content_parts', {})
    
    for key in current_parts:
        if key in last_parts and current_parts[key] != last_parts[key]:
            return True, f"Phần {key} thay đổi"
    
    # So sánh kích thước nội dung
    current_len = current_state.get('content_length', 0)
    last_len = last_state.get('content_length', 0)
    
    if abs(current_len - last_len) > 500:  # Thay đổi đáng kể
        return True, f"Kích thước thay đổi {current_len - last_len} chars"
    
    return False, "Không có thay đổi"

def main():
    start_time = datetime.now()
    print(f"\n🕐 === BẮT ĐẦU KIỂM TRA LÚC {start_time.strftime('%H:%M:%S %d/%m/%Y')} ===")
    
    # Kiểm tra cấu hình
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ THIẾU CẤU HÌNH!")
        print("Cần thêm BOT_TOKEN và CHAT_ID vào GitHub Secrets")
        return
    
    print(f"✅ Bot: {BOT_TOKEN[:10]}... | Chat: {CHAT_ID}")
    
    # Lấy nội dung trang Facebook
    html_content = get_page_content()
    if not html_content:
        print("❌ KHÔNG THỂ TRUY CẬP FACEBOOK - thử lại lần sau")
        return
    
    # Phân tích nội dung với nhiều hash
    current_state = extract_multiple_hashes(html_content)
    print(f"🔢 Hash chính: {current_state['main_hash'][:12]}...")
    print(f"📏 Kích thước: text={current_state['content_length']}, raw={current_state['raw_length']}")
    
    # So sánh với trạng thái trước
    last_state = load_last_state()
    
    if last_state is None:
        print("🚀 KHỞI ĐỘNG MONITOR")
        if save_state(current_state):
            startup_msg = f"""🤖 <b>Bot bắt đầu theo dõi Ren Devor</b>
⏰ Kiểm tra: mỗi phút
🎯 Sẽ thông báo ngay khi có bài mới!"""
            send_telegram_message(startup_msg)
        return
    
    # Phát hiện thay đổi
    has_changes, reason = detect_changes(current_state, last_state)
    
    if has_changes:
        print(f"🆕 PHÁT HIỆN THAY ĐỔI: {reason}")
        
        # Thông báo ngắn gọn
        message = "Có bài viết mới từ Ren Devor"
        
        # Gửi thông báo và lưu state
        if send_telegram_message(message):
            if save_state(current_state):
                print("✅ ĐÃ XỬ LÝ THÀNH CÔNG!")
            else:
                print("⚠️ Gửi thông báo OK nhưng lưu state lỗi")
        else:
            print("❌ KHÔNG GỬI ĐƯỢC THÔNG BÁO - giữ nguyên state cũ")
    else:
        print(f"✅ Không có thay đổi ({reason})")
    
    # Thống kê thời gian
    duration = (datetime.now() - start_time).total_seconds()
    print(f"⏱️ Thời gian xử lý: {duration:.2f}s")
    print(f"🏁 === KẾT THÚC KIỂM TRA ===\n")

if __name__ == "__main__":
    main()
