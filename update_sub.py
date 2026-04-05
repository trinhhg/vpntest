import requests
import base64
import urllib.parse
import re
import json

# Cấu hình địa chỉ Worker
WORKER_DOMAIN = "https://vpntest-ad4.pages.dev"
API_LINKS = f"{WORKER_DOMAIN}/api/links"
API_PUSH = f"{WORKER_DOMAIN}/api/push_data"

def process_node_name(text):
    text = urllib.parse.unquote(text)
    
    # 1. Xử lý 3 node thông tin
    if "剩余流量" in text: 
        return text.replace("剩余流量：", "Data: ").replace("剩余流量:", "Data: ")
    if "距离下次重置剩余" in text: 
        return text.replace("距离下次重置剩余：", "Reset: ").replace("距离下次重置剩余:", "Reset: ").replace(" 天", " Days")
    if "套餐到期" in text: 
        return text.replace("套餐到期：", "Exp: ").replace("套餐到期:", "Exp: ")

    # 2. Dịch và rename các node bình thường
    text = text.replace("良心云", "") 
    text = text.replace("自动选择", "Auto Select")
    text = text.replace("故障转移", "Fallback")
    text = text.replace("🇨🇳台湾", "🇹🇼 Taiwan ")
    text = text.replace("🇭🇰香港", "🇭🇰 Hong Kong ")
    text = text.replace("🇸🇬新加坡", "🇸🇬 Singapore ")
    text = text.replace("🇯🇵日本", "🇯🇵 Japan ")
    text = text.replace("🇺🇸美国", "🇺🇸 USA ")
    text = text.replace("🇰🇷韩国", "🇰🇷 Korea ")
    text = text.replace("台湾", "Taiwan ")
    text = text.replace("香港", "Hong Kong ")
    text = text.replace("新加坡", "Singapore ")
    text = text.replace("日本", "Japan ")
    text = text.replace("美国", "USA ")
    text = text.replace("韩国", "Korea ")
    text = text.replace("高速", " High Speed ")
    text = text.replace("专线", " Private ")
    text = text.replace("流媒体", " Streaming")
    text = text.replace("0.1倍", " 0.1x")
    
    text = re.sub(r'\|BGP\|', ' ', text)
    text = re.sub(r'\|BGP', ' ', text)
    text = re.sub(r'\|', ' ', text)
    
    clean_name = " ".join(text.split())
    # Thương hiệu VPN Trinh Hg ở cuối
    return f"{clean_name} | VPN Trinh Hg"

def update_all_subs():
    try:
        print(f"--- BẮT ĐẦU CẬP NHẬT TỪ KV ---")
        res = requests.get(API_LINKS, timeout=10)
        links_db = res.json()
        
        for item in links_db:
            orig_url = item.get("orig")
            email = item.get("email")
            if not orig_url or not email: continue
                
            print(f"\n[*] Đang xử lý: {email}")
            headers = {"User-Agent": "v2rayN/6.23"}
            try:
                sub_res = requests.get(orig_url, headers=headers, timeout=15)
                if sub_res.status_code == 200:
                    content = sub_res.text.strip()
                    if not content: 
                        print(f"  [!] Link gốc trả về rỗng.")
                        continue
                    
                    # Lấy thông tin dung lượng từ Header
                    user_info = sub_res.headers.get("subscription-userinfo", "")
                    
                    # Xử lý Padding Base64 an toàn
                    missing_padding = len(content) % 4
                    if missing_padding:
                        content += '=' * (4 - missing_padding)
                    
                    try:
                        decoded = base64.b64decode(content).decode('utf-8', errors='ignore')
                        print(f"  [DEBUG] Độ dài nội dung giải mã: {len(decoded)}")
                        print(f"  [DEBUG] Sample: {decoded[:150]}...")
                        
                        lines = decoded.splitlines()
                        new_lines = []
                        
                        for line in lines:
                            line = line.strip()
                            if not line: continue
                            
                            # Nếu dòng chứa link node
                            if "://" in line:
                                try:
                                    parts = line.split("#", 1)
                                    if len(parts) == 2:
                                        main_link = parts[0]
                                        new_name = process_node_name(parts[1])
                                        safe_name = urllib.parse.quote(new_name)
                                        new_lines.append(f"{main_link}#{safe_name}")
                                    else:
                                        new_lines.append(line)
                                except:
                                    new_lines.append(line)
                            else:
                                # Nếu là dòng thông tin hoặc format khác (giữ lại để tránh mất node)
                                new_lines.append(line)
                        
                        print(f"  [DEBUG] Số lượng node sau khi parse: {len(new_lines)}")

                        # Cơ chế Fallback: Nếu lọc xong không còn gì thì dùng bản gốc
                        if not new_lines:
                            print("  [!] Không parse được node nào -> Dùng bản gốc để tránh IA==")
                            final_string = decoded
                        else:
                            final_string = "\n".join(new_lines)
                        
                        # Encode lại Base64 thuần
                        final_b64 = base64.b64encode(final_string.encode('utf-8')).decode('utf-8').replace('\n', '').replace('\r', '')
                        
                        # Đẩy data lên KV qua API của Worker
                        payload = {
                            "email": email,
                            "body": final_b64,
                            "info": user_info
                        }
                        
                        push_res = requests.post(API_PUSH, json=payload, timeout=10)
                        if push_res.status_code == 200:
                            print(f"  [OK] Đã đẩy dữ liệu lên KV thành công.")
                        else:
                            print(f"  [FAIL] Không thể đẩy lên KV. Mã lỗi: {push_res.status_code}")
                            
                    except Exception as e:
                        print(f"  [!] Lỗi giải mã Base64: {e}")
                else:
                    print(f"  [X] Liangxin trả về mã lỗi: {sub_res.status_code}")
                        
            except Exception as e:
                print(f"  [!] Lỗi kết nối tới sub gốc: {e}")
                
    except Exception as e:
        print(f"--- LỖI HỆ THỐNG: {e} ---")

if __name__ == "__main__":
    update_all_subs()
