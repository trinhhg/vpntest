import requests
import base64
import os
import json
import urllib.parse

API_LINKS = "https://vpntest-ad4.pages.dev/api/links"

os.makedirs("subs", exist_ok=True)

def process_text(text):
    # Giải mã URL-Encode để đọc được tiếng Trung bị ẩn
    text = urllib.parse.unquote(text)
    
    # 1. DỊCH 3 NODE THÔNG TIN (DUNG LƯỢNG, HẾT HẠN) MÀ ÔNG MUỐN GIỮ
    text = text.replace("剩余流量：", "Data: ")
    text = text.replace("距离下次重置剩余：", "Reset: ")
    text = text.replace(" 天", " Days")
    text = text.replace("套餐到期：", "Exp: ")

    # 2. DỊCH TÊN THƯƠNG HIỆU & QUỐC GIA
    text = text.replace("良心云", "VPN Trinh Hg")
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
    
    # 3. DỊCH HẬU TỐ
    text = text.replace("高速", "High Speed ")
    text = text.replace("专线", "Private ")
    text = text.replace("流媒体", " Streaming")
    text = text.replace("0.1倍", "0.1x")
    
    # 4. XÓA KÝ TỰ RÁC
    text = text.replace("|BGP|", " ")
    text = text.replace("|BGP", " ")
    text = text.replace("|", " ")
    
    # Xóa dư thừa khoảng trắng
    return " ".join(text.split())

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
            # Giả dạng App VPN để lấy Header Dung lượng thật
            headers = {
                "User-Agent": "v2rayN/6.23"
            }
            
            try:
                sub_res = requests.get(orig_url, headers=headers, timeout=15)
                
                if sub_res.status_code == 200:
                    content = sub_res.text.strip()
                    if not content:
                        continue
                        
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
                                    node_name = parts[1]
                                    
                                    # CHỈ DỊCH TÊN NODE VÀ GIỮ LẠI TẤT CẢ
                                    node_name = process_text(node_name)
                                    
                                    # THÊM TÊN LỬA VÀ THƯƠNG HIỆU VÀO ĐẦU
                                    if "VPN Trinh Hg" not in node_name:
                                        node_name = f"🚀 VPN Trinh Hg | {node_name}"
                                    else:
                                        node_name = f"🚀 {node_name}"
                                        
                                    new_lines.append(f"{main_link}#{node_name}")
                                else:
                                    new_lines.append(line)
                            except:
                                pass
                        
                        final_content = base64.b64encode("\n".join(new_lines).encode('utf-8')).decode('utf-8')
                        
                        filepath = f"subs/{email}.json"
                        data_to_save = {"body": final_content, "info": user_info}
                        
                        with open(filepath, "w", encoding="utf-8") as f:
                            json.dump(data_to_save, f)
                        print(f"  [OK] Đã lưu thành công JSON: {filepath}")
                        
                    except Exception as e:
                        print(f"  [!] Lỗi xử lý Base64: {e}")
            except Exception as e:
                print(f"  [!] Lỗi kết nối: {e}")
                
    except Exception as e:
        print("Lỗi API:", e)

if __name__ == "__main__":
    update_all_subs()
