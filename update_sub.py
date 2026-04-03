import requests
import base64
import os

# QUAN TRỌNG: Đổi domain này thành domain Web Test hoặc Worker Test của bạn
# Ví dụ: "https://vpntest.pages.dev/api/links" hoặc "https://vpn-worker-test.taikhoancuaban.workers.dev/api/links"
API_LINKS = "https://THAY-BANG-DOMAIN-WEB-TEST-CUA-BAN/api/links"

# Tạo thư mục chứa file txt
os.makedirs("subs", exist_ok=True)

def update_all_subs():
    try:
        print("Đang lấy danh sách khách hàng từ Database...")
        res = requests.get(API_LINKS)
        links_db = res.json()
        
        for item in links_db:
            orig_url = item.get("orig")
            email = item.get("email")
            
            if not orig_url or not email:
                continue
                
            print(f"-> Đang xử lý node cho khách: {email}")
            try:
                sub_res = requests.get(orig_url, timeout=15)
                if sub_res.status_code == 200:
                    content = sub_res.text.strip()
                    
                    if not content:
                        continue

                    decoded = base64.b64decode(content).decode('utf-8')
                    lines = decoded.splitlines()
                    
                    new_lines = []
                    for line in lines:
                        if "#" in line:
                            parts = line.split("#", 1)
                            new_lines.append(f"{parts[0]}#🚀 VPN Trinh Hg | {parts[1]}")
                        else:
                            new_lines.append(line)
                    
                    final_content = base64.b64encode("\n".join(new_lines).encode('utf-8')).decode('utf-8')
                    
                    filepath = f"subs/{email}.txt"
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(final_content)
                        
            except Exception as e:
                print(f"[!] Lỗi khi xử lý {email}: {e}")
                
    except Exception as e:
        print("Lỗi fetch API Database:", e)

if __name__ == "__main__":
    update_all_subs()
