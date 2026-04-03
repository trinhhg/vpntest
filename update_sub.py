import requests
import base64
import os

API_LINKS = "https://vpntest-ad4.pages.dev/api/links"

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
                continue
                
            print(f"-> Đang tải Node gốc cho khách: {email}")
            
            # GIẢ DẠNG TRÌNH DUYỆT CHROME ĐỂ KHÔNG BỊ CHẶN
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            }
            
            try:
                sub_res = requests.get(orig_url, headers=headers, timeout=15)
                
                # NẾU TẢI THÀNH CÔNG (MÃ 200)
                if sub_res.status_code == 200:
                    content = sub_res.text.strip()
                    if not content:
                        print("  [!] Lỗi: Link gốc không có dữ liệu (File rỗng)!")
                        continue

                    try:
                        # FIX LỖI THIẾU DẤU BẰNG (=) CỦA BASE64 (Rất hay gặp)
                        content += "=" * ((4 - len(content) % 4) % 4)
                        
                        # Giải mã Base64
                        decoded = base64.b64decode(content).decode('utf-8')
                        lines = decoded.splitlines()
                        
                        new_lines = []
                        for line in lines:
                            if "#" in line:
                                parts = line.split("#", 1)
                                new_lines.append(f"{parts[0]}#🚀 VPN Trinh Hg | {parts[1]}")
                            else:
                                new_lines.append(line)
                        
                        # Mã hóa ngược lại
                        final_content = base64.b64encode("\n".join(new_lines).encode('utf-8')).decode('utf-8')
                        
                        filepath = f"subs/{email}.txt"
                        with open(filepath, "w", encoding="utf-8") as f:
                            f.write(final_content)
                        print(f"  [OK] Đã Rename và tạo file thành công: {filepath}")
                        
                    except Exception as decode_err:
                        print(f"  [!] Lỗi giải mã Base64: Dữ liệu link gốc bị sai định dạng - {decode_err}")

                # NẾU BỊ CHẶN HOẶC WEB GỐC LỖI
                else:
                    print(f"  [X] THẤT BẠI: Web gốc trả về mã lỗi {sub_res.status_code}")
                    print(f"  [X] Chi tiết lỗi: {sub_res.text[:100]}...")
                    
            except Exception as req_err:
                print(f"  [!] Lỗi kết nối đến web gốc: {req_err}")
                
    except Exception as e:
        print("Lỗi không thể kết nối tới Database API:", e)

if __name__ == "__main__":
    update_all_subs()
