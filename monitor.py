import requests
import json
import os
from datetime import datetime
import hashlib
import re
import time

# Config - CHỈ CẦN THAY ĐỔI 2 DÒNG NÀY
FACEBOOK_URL = "https://www.facebook.com/setiawan.djordy.507"  # ← Thay URL tại đây
PERSON_NAME = "Ren Devor"  # ← Thay tên người tại đây

BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

def get_page_content():
    """Lấy nội dung trang Facebook với retry mechanism"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    }
    
    # Retry mechanism để tăng độ tin cậy
    for attempt in range(3):
        try:
            print(f"🔍 Đang truy cập: {FACEBOOK_URL} (lần {attempt + 1})")
            response = requests.get(FACEBOOK_URL, headers=headers, timeout=30)
            print(f"📊 Status code: {response.status_code}")
            print(f"📏 Content length: {len(response.text)} chars")
            
            if response.status_code == 200:
                return response.text
            else:
                print(f"⚠️ Status code không OK: {response.status_code}")
                if attempt < 2:
                    time.sleep(5)  # Đợi 5s trước khi retry
                    
        except Exception as e:
            print(f"❌ Lỗi khi lấy trang (lần {attempt + 1}): {e}")
            if attempt < 2:
                time.sleep(5)
    
    return None

def extract_post_indicators(html_content):
    """
    Tạo fingerprint từ các chỉ số bài viết thay vì hash toàn bộ content
    Tập trung vào các phần tử thường thay đổi khi có bài mới
    """
    try:
        # Loại bỏ script và style tags
        cleaned_html = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        cleaned_html = re.sub(r'<style[^>]*>.*?</style>', '', cleaned_html, flags=re.DOTALL | re.IGNORECASE)
        
        # Tìm các pattern thường xuất hiện trong bài viết Facebook
        post_patterns = [
            r'data-testid="post_message"',
            r'data-testid="story-subtitle"',
            r'data-ft="{[^}]*story_fbid[^}]*}"',
            r'timestampContent',
            r'story_fbid',
            r'data-testid="story-title"'
        ]
        
        post_indicators = []
        for pattern in post_patterns:
            matches = re.findall(pattern, cleaned_html, re.IGNORECASE)
            post_indicators.extend(matches)
        
        # Tìm timestamp và story ID
        story_ids = re.findall(r'story_fbid["\s]*[:=]["\s]*([0-9]+)', cleaned_html)
        timestamps = re.findall(r'timestampContent[^>]*>([^<]*)</.*?>', cleaned_html)
        
        # Tạo một fingerprint từ các indicators
        fingerprint_data = {
            'post_count': len(post_indicators),
            'story_ids': sorted(story_ids[:10]),  # Lấy 10 story ID mới nhất
            'timestamps': sorted(timestamps[:10]),  # Lấy 10 timestamp mới nhất
            'content_length': len(cleaned_html)
        }
        
        # Tạo hash từ fingerprint
        fingerprint_str = json.dumps(fingerprint_data, sort_keys=True)
        content_hash = hashlib.md5(fingerprint_str.encode('utf-8')).hexdigest()
        
        # Tạo preview ngắn gọn
        text_content = re.sub(r'<[^>]+>', ' ', cleaned_html)
        text_content = re.sub(r'\s+', ' ', text_content).strip()
        preview = text_content[:200] if text_content else "Không có nội dung"
        
        return {
            'hash': content_hash,
            'preview': preview,
            'timestamp': datetime.now().isoformat(),
            'content_length': len(cleaned_html),
            'post_indicators': len(post_indicators),
            'story_count': len(story_ids),
            'fingerprint': fingerprint_data
        }
        
    except Exception as e:
        print(f"❌ Lỗi parse HTML: {e}")
        # Fallback: dùng hash đơn giản
        simple_hash = hashlib.md5(html_content[:2000].encode('utf-8', errors='ignore')).hexdigest()
        return {
            'hash': simple_hash,
            'preview': "Lỗi parse HTML, dùng fallback hash",
            'timestamp': datetime.now().isoformat(),
            'content_length': len(html_content),
            'post_indicators': 0,
            'story_count': 0
        }

def send_telegram_message(message):
    """Gửi thông báo Telegram đơn giản"""
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
    
    # Retry mechanism cho Telegram API
    for attempt in range(3):
        try:
            response = requests.post(url, data=data, timeout=15)
            if response.status_code == 200:
                print(f"✅ Gửi thông báo Telegram thành công")
                return True
            else:
                print(f"❌ Lỗi Telegram API: {response.status_code}")
                print(f"Response: {response.text}")
                if attempt < 2:
                    time.sleep(3)
        except Exception as e:
            print(f"❌ Lỗi gửi Telegram (lần {attempt + 1}): {e}")
            if attempt < 2:
                time.sleep(3)
    
    return False

def load_last_state():
    """Load trạng thái lần kiểm tra trước"""
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
    """Lưu trạng thái hiện tại"""
    try:
        with open('last_state.json', 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        print("💾 Đã lưu state mới")
        return True
    except Exception as e:
        print(f"❌ Lỗi lưu state: {e}")
        return False

def should_send_heartbeat():
    """Kiểm tra có nên gửi heartbeat không (mỗi 60 phút)"""
    try:
        with open('last_heartbeat.txt', 'r') as f:
            last_heartbeat = datetime.fromisoformat(f.read().strip())
            time_diff = datetime.now() - last_heartbeat
            if time_diff.total_seconds() > 3600:  # 60 phút
                with open('last_heartbeat.txt', 'w') as f:
                    f.write(datetime.now().isoformat())
                return True
    except (FileNotFoundError, ValueError):
        # Lần đầu hoặc file lỗi
        with open('last_heartbeat.txt', 'w') as f:
            f.write(datetime.now().isoformat())
        return True
    return False

def send_status_report():
    """Gửi báo cáo trạng thái chi tiết"""
    print("📊 Đang gửi báo cáo trạng thái...")
    
    # Đọc trạng thái hiện tại
    try:
        with open('last_state.json', 'r', encoding='utf-8') as f:
            state = json.load(f)
        last_check = state.get('timestamp', 'Không rõ')
        hash_info = state.get('hash', 'N/A')[:8]
        post_count = state.get('post_indicators', 0)
        story_count = state.get('story_count', 0)
    except:
        last_check = "Chưa có dữ liệu"
        hash_info = "N/A"
        post_count = 0
        story_count = 0
    
    # Đọc heartbeat
    try:
        with open('last_heartbeat.txt', 'r') as f:
            last_heartbeat = f.read().strip()
    except:
        last_heartbeat = "Chưa có"
    
    message = f"""
🔍 <b>BÁO CÁO TRẠNG THÁI BOT</b>

⏰ Kiểm tra lúc: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}
📊 Lần check cuối: {last_check}
💚 Heartbeat cuối: {last_heartbeat}

📈 Thống kê:
- Hash hiện tại: {hash_info}...
- Post indicators: {post_count}
- Story count: {story_count}

✅ <b>Bot đang hoạt động bình thường!</b>
📱 Theo dõi: {PERSON_NAME}
🔔 Sẵn sàng thông báo bài viết mới
"""
    
    if send_telegram_message(message):
        print("✅ Đã gửi báo cáo trạng thái")
    else:
        print("❌ Không gửi được báo cáo")

def has_significant_change(current_state, last_state):
    """
    Kiểm tra xem có thay đổi đáng kể không
    Sử dụng nhiều chỉ số để tăng độ chính xác
    """
    if not last_state:
        return False
    
    # Kiểm tra hash chính
    if current_state['hash'] != last_state['hash']:
        # Kiểm tra thêm các chỉ số khác để tránh false positive
        story_count_changed = current_state.get('story_count', 0) != last_state.get('story_count', 0)
        post_indicators_changed = current_state.get('post_indicators', 0) != last_state.get('post_indicators', 0)
        content_length_change = abs(current_state.get('content_length', 0) - last_state.get('content_length', 0))
        
        # Chỉ báo thay đổi nếu có ít nhất 2 chỉ số thay đổi hoặc thay đổi content length > 1000 chars
        if story_count_changed or post_indicators_changed or content_length_change > 1000:
            return True
        else:
            print("⚠️ Hash thay đổi nhưng các chỉ số khác không đáng kể - có thể là false positive")
            return False
    
    return False

def main():
    print(f"\n🕐 === BẮT ĐẦU KIỂM TRA LÚC {datetime.now().strftime('%H:%M:%S %d/%m/%Y')} ===")
    
    # Xử lý tham số dòng lệnh để kiểm tra trạng thái
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'status':
        send_status_report()
        return
    
    # Kiểm tra cấu hình
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Thiếu cấu hình BOT_TOKEN hoặc CHAT_ID")
        print("Hãy kiểm tra Settings → Secrets and variables → Actions")
        return
    
    print(f"✅ Bot Token: {BOT_TOKEN[:10]}...")
    print(f"✅ Chat ID: {CHAT_ID}")
    
    # Lấy nội dung trang
    html_content = get_page_content()
    if not html_content:
        print("❌ Không thể lấy nội dung trang sau 3 lần thử")
        return
    
    # Phân tích nội dung
    current_state = extract_post_indicators(html_content)
    print(f"🔢 Hash hiện tại: {current_state['hash']}")
    print(f"📊 Post indicators: {current_state.get('post_indicators', 0)}")
    print(f"📄 Story count: {current_state.get('story_count', 0)}")
    
    # So sánh với lần kiểm tra trước
    last_state = load_last_state()
    
    if last_state is None:
        print("🚀 Lần đầu chạy, lưu trạng thái hiện tại")
        if save_state(current_state):
            # Gửi thông báo khởi động đơn giản
            startup_message = f"🤖 Bot Facebook Monitor đã khởi động và sẵn sàng theo dõi bài viết mới từ {PERSON_NAME}!"
            send_telegram_message(startup_message)
        return
    
    # Kiểm tra thay đổi với logic cải tiến
    if has_significant_change(current_state, last_state):
        print("🆕 PHÁT HIỆN THAY ĐỔI ĐÁNG KỂ!")
        
        # Thông báo đơn giản theo yêu cầu
        message = f"📱 Có bài viết mới từ {PERSON_NAME}!"
        
        # Gửi thông báo và chỉ lưu state nếu gửi thành công
        if send_telegram_message(message):
            if save_state(current_state):
                print("✅ Đã cập nhật state sau khi thông báo thành công")
            else:
                print("⚠️ Thông báo thành công nhưng không lưu được state")
        else:
            print("❌ Không gửi được thông báo, giữ nguyên state cũ")
    else:
        print("✅ Không có thay đổi đáng kể")
        # Vẫn cập nhật timestamp để track
        current_state['last_check'] = datetime.now().isoformat()
        save_state(current_state)
        
        # Gửi heartbeat mỗi 60 phút để biết bot còn sống
        if should_send_heartbeat():
            heartbeat_msg = f"💚 Bot đang hoạt động - {datetime.now().strftime('%H:%M %d/%m')}"
            send_telegram_message(heartbeat_msg)
    
    print(f"🏁 === KẾT THÚC KIỂM TRA ===\n")

if __name__ == "__main__":
    main()
