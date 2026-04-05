import requests
import base64
import os
import json
import urllib.parse
import re

API_LINKS = "https://vpntest-ad4.pages.dev/api/links"

os.makedirs("subs", exist_ok=True)

def process_node_name(text):
    # Giải mã URL-Encode
    text = urllib.parse.unquote(text)
    
    # 1. NẾU LÀ 3 NODE THÔNG TIN -> Dịch và TRẢ VỀ LUÔN (Không thêm tên VPN Trinh Hg)
    if "剩余流量" in text: return text.replace("剩余流量：", "Data: ").replace("剩余流量:", "Data: ")
    if "距离下次重置剩余" in text: return text.replace("距离下次重置剩余：", "Reset: ").replace("距离下次重置剩余:", "Reset: ").replace(" 天", " Days")
    if "套餐到期" in text: return text.replace("套餐到期：", "Exp: ").replace("套餐到期:", "Exp: ")

    # 2. CÁC NODE BÌNH THƯỜNG -> Dịch tiếng Anh
    text = text.replace("良心云", "") # Xóa chữ Liangxin
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
    
    # 3. Dọn dẹp ký tự thừa (BGP, gạch dọc)
    text = re.sub(r'\|BGP\|', ' ', text)
    text = re.sub(r'\|BGP', ' ', text)
    text = re.sub(r'\|', ' ', text)
    
    # Chuẩn hóa khoảng trắng
    clean_name = " ".join(text.split())
    
    # ĐƯA TÊN VPN TRINH HG RA CUỐI
    return f"{clean_name} | VPN Trinh Hg"

def update_all_subs():
    try:
        print(f"Đang gọi API: {API_LINKS}")
        res = requests.get(API_LINKS, timeout=10)
        links_db = res.json()
        print(f"Tìm thấy {len(links_db)} link.")
        
        for item in links_db:
            orig_url = item.get("orig")
            email = item.get("email")
            
            if not orig_url or not email:
                continue
                
            print(f"-> Đang xử lý: {email}")
            # Phải giả dạng V2rayN thì Liangxin mới nhả dung lượng
            headers = {"User-Agent": "v2rayN/6.23"}
            
            try:
                sub_res = requests.get(orig_url, headers=headers, timeout=15)
                
                if sub_res.status_code == 200:
                    content = sub_res.text.strip()
                    if not content:
                        continue
                        
                    # Trích xuất Header dung lượng từ server gốc
                    user_info = sub_res.headers.get("subscription-userinfo", "")

                    try:
                        content += "=" * ((4 - len(content) % 4) % 4)
                        decoded = base64.b64decode(content).decode('utf-8')
                        lines = decoded.splitlines()
                        
                        new_lines = []
                        for line in lines:
                            if "://" not in line:
                                continue
                            try:
                                parts = line.split("#", 1)
                                if len(parts) == 2:
                                    main_link = parts[0]
                                    new_name = process_node_name(parts[1])
                                    
                                    # Mã hóa URL lại tên node để tránh lỗi
                                    safe_name = urllib.parse.quote(new_name)
                                    new_lines.append(f"{main_link}#{safe_name}")
                                else:
                                    new_lines.append(line)
                            except:
                                pass
                        
                        # Gộp list và mã hóa Base64 cực chuẩn, xóa mọi ký tự ngắt dòng
                        final_string = "\n".join(new_lines)
                        final_b64 = base64.b64encode(final_string.encode('utf-8')).decode('utf-8').replace('\n', '').replace('\r', '')
                        
                        filepath = f"subs/{email}.json"
                        with open(filepath, "w", encoding="utf-8") as f:
                            json.dump({"body": final_b64, "info": user_info}, f)
                        print(f"  [OK] Đã lưu JSON: {filepath}")
                        
                    except Exception as e:
                        print(f"  [!] Lỗi Base64: {e}")
            except Exception as e:
                print(f"  [!] Lỗi kết nối: {e}")
                
    except Exception as e:
        print("Lỗi API:", e)

if __name__ == "__main__":
    update_all_subs()
