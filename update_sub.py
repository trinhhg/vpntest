import requests
import base64
import os
import json

API_LINKS = "https://vpntest-ad4.pages.dev/api/links"

os.makedirs("subs", exist_ok=True)

def process_text(text):
    # 1. ĐỔI TÊN THƯƠNG HIỆU & GROUP
    text = text.replace("良心云", "VPN Trinh Hg")
    text = text.replace("自动选择", "Auto Select")
    text = text.replace("故障转移", "Fallback")

    # 2. ĐỔI THÔNG TIN DUNG LƯỢNG
    text = text.replace("剩余流量：", "Data: ")
    text = text.replace("距离下次重置剩余：", "Reset: ")
    text = text.replace(" 天", " Days")
    text = text.replace("套餐到期：", "Exp: ")

    # 3. ĐỔI CỜ VÀ TÊN QUỐC GIA
    text = text.replace("🇨🇳台湾", "🇹🇼 Taiwan ")
    text = text.replace("🇭🇰香港", "🇭🇰 Hong Kong ")
    text = text.replace("🇸🇬新加坡", "🇸🇬 Singapore ")
    text = text.replace("🇯🇵日本", "🇯🇵 Japan ")
    text = text.replace("🇺🇸美国", "🇺🇸 USA ")
    text = text.replace("🇰🇷韩国", "🇰🇷 Korea ")
    
    # Đề phòng các node bị thiếu cờ ở bản gốc
    text = text.replace("香港", "Hong Kong ")
    text = text.replace("新加坡", "Singapore ")
    text = text.replace("日本", "Japan ")
    text = text.replace("美国", "USA ")
    text = text.replace("韩国", "Korea ")
    text = text.replace("台湾", "Taiwan ")

    # 4. XÓA BGP, ĐỔI HẬU TỐ VÀ CĂN CHỈNH KHOẢNG TRẮNG
    text = text.replace("高速", "High Speed ")
    text = text.replace("专线", "Private Line ")
    text = text.replace("|BGP|", " ")
    text = text.replace("|", " ")
    text = text.replace("流媒体", " Streaming")
    text = text.replace("0.1倍", "0.1x")
    
    return text

def update_all_subs():
    try:
        print(f"Đang gọi API lấy danh sách link: {API_LINKS}")
        res = requests.get(API_LINKS, timeout=10)
        links_db = res.json()
        print(f"Tìm thấy {len(links_db)} link trong Database.")
        
        for item in links_db:
            orig_url = item.get("orig")
            email = item.get("email")
            
            if not orig_url or not email:
                continue
                
            print(f"-> Đang xử lý: {email}")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            }
            
            try:
                sub_res = requests.get(orig_url, headers=headers, timeout=15)
                
                if sub_res.status_code == 200:
                    content = sub_res.text.strip()
                    if not content:
                        print("  [!] Lỗi: Link gốc rỗng!")
                        continue
                        
                    # LẤY THÔNG SỐ DUNG LƯỢNG TỪ SERVER GỐC
                    user_info = sub_res.headers.get("subscription-userinfo", "")

                    try:
                        content += "=" * ((4 - len(content) % 4) % 4)
                        decoded = base64.b64decode(content).decode('utf-8')
                        
                        # CHẠY HÀM DỊCH TIẾNG ANH
                        decoded = process_text(decoded)
                        
                        lines = decoded.splitlines()
                        new_lines = []
                        for line in lines:
                            if "#" in line:
                                parts = line.split("#", 1)
                                node_name = parts[1]
                                # Đảm bảo có icon tên lửa
                                if "VPN Trinh Hg" not in node_name:
                                    node_name = f"🚀 VPN Trinh Hg | {node_name}"
                                else:
                                    node_name = f"🚀 {node_name}"
                                new_lines.append(f"{parts[0]}#{node_name}")
                            else:
                                new_lines.append(line)
                        
                        final_content = base64.b64encode("\n".join(new_lines).encode('utf-8')).decode('utf-8')
                        
                        # LƯU THÀNH FILE JSON ĐỂ CHỨA CẢ DATA VÀ DUNG LƯỢNG
                        filepath = f"subs/{email}.json"
                        data_to_save = {
                            "body": final_content,
                            "info": user_info
                        }
                        
                        with open(filepath, "w", encoding="utf-8") as f:
                            json.dump(data_to_save, f)
                        print(f"  [OK] Đã lưu thành công: {filepath}")
                        
                    except Exception as decode_err:
                        print(f"  [!] Lỗi giải mã Base64: {decode_err}")
                else:
                    print(f"  [X] Web gốc báo lỗi {sub_res.status_code}")
                    
            except Exception as req_err:
                print(f"  [!] Lỗi kết nối: {req_err}")
                
    except Exception as e:
        print("Lỗi không thể kết nối tới Database API:", e)

if __name__ == "__main__":
    update_all_subs()
