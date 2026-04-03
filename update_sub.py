import requests
import base64
import os

# ĐÃ ĐIỀN CHUẨN LINK API CỦA BẠN:
API_LINKS = "https://vpntest-ad4.pages.dev/api/links"

# Tạo thư mục chứa file txt
os.makedirs("subs", exist_ok=True)

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
                print(f"Bỏ qua link do thiếu orig hoặc email: {item}")
                continue
                
            print(f"-> Đang tải Node gốc cho khách: {email}")
            try:
                sub_res = requests.get(orig_url, timeout=15)
                if sub_res.status_code == 200:
                    content = sub_res.text.strip()
                    if not content:
                        print(" [!] File gốc của Liangxin trả về rỗng!")
                        continue

                    # Giải mã Base64
                    decoded = base64.b64decode(content).decode('utf-8')
                    lines = decoded.splitlines()
                    
                    new_lines = []
                    for line in lines:
                        if "#" in line:
                            # Cắt đôi dòng ở dấu # và chèn tên của bạn vào
                            parts = line.split("#", 1)
                            new_lines.append(f"{parts[0]}#🚀 VPN Trinh Hg | {parts[1]}")
                        else:
                            new_lines.append(line)
                    
                    # Mã hóa ngược lại thành Base64
                    final_content = base64.b64encode("\n".join(new_lines).encode('utf-8')).decode('utf-8')
                    
                    # Lưu thành file
                    filepath = f"subs/{email}.txt"
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(final_content)
                    print(f"  [OK] Đã Rename và lưu thành công: {filepath}")
                        
            except Exception as e:
                print(f"  [!] Lỗi tải hoặc xử lý link của {email}: {e}")
                
    except Exception as e:
        print("Lỗi không thể kết nối tới Database API:", e)

if __name__ == "__main__":
    update_all_subs()
