import requests
import base64
import urllib.parse
import re
import datetime

WORKER_DOMAIN = "https://vpntest-ad4.pages.dev"
API_LINKS = f"{WORKER_DOMAIN}/api/links"
API_PUSH = f"{WORKER_DOMAIN}/api/push_data"

def clean_name_string(text):
    text = urllib.parse.unquote(text)
    # Dịch thuật & Rename
    text = text.replace("良心云", "VPN Trinh Hg").replace("顶级机场", "VPN Trinh Hg")
    text = text.replace("自动选择", "Auto Select").replace("故障转移", "Fallback")
    text = text.replace("🇨🇳台湾", "🇹🇼 Taiwan ").replace("🇭🇰香港", "🇭🇰 Hong Kong ").replace("🇸🇬新加坡", "🇸🇬 Singapore ")
    text = text.replace("🇯🇵日本", "🇯🇵 Japan ").replace("🇺🇸美国", "🇺🇸 USA ").replace("🇰🇷韩国", "🇰🇷 Korea ")
    
    # FIX LỖI YAML: Bỏ dấu | và dấu :
    text = text.replace("|", "-").replace(":", " ")
    
    clean_name = " ".join(text.split())
    return clean_name

def update_all_subs():
    try:
        res = requests.get(API_LINKS, timeout=10)
        links_db = res.json()
        processed_tokens = set()
        
        for item in links_db:
            orig_url = item.get("orig")
            masked_url = item.get("masked")
            if not orig_url or not masked_url: continue
            
            parsed_url = urllib.parse.urlparse(masked_url)
            qs = urllib.parse.parse_qs(parsed_url.query)
            token_list = qs.get("OwO") or qs.get("token")
            if not token_list: continue
            token = token_list[0]
            
            if token in processed_tokens: continue
            processed_tokens.add(token)
                
            print(f"-> Đang xử lý Token: {token}")
            
            try:
                b64_res = requests.get(orig_url, headers={"User-Agent": "v2rayN/6.23"}, timeout=15)
                yaml_res = requests.get(orig_url, headers={"User-Agent": "Clash-Verge"}, timeout=15)
                
                if b64_res.status_code != 200: continue
                
                content = b64_res.text.strip()
                user_info = b64_res.headers.get("subscription-userinfo", "")
                
                # Tính dung lượng cho Web
                traffic_data = {"used": "0.00", "total": "0.00", "percent": 0, "expire": "Vĩnh viễn"}
                if user_info:
                    match_up = re.search(r'upload=(\d+)', user_info); match_down = re.search(r'download=(\d+)', user_info); match_total = re.search(r'total=(\d+)', user_info); match_exp = re.search(r'expire=(\d+)', user_info)
                    up = int(match_up.group(1)) if match_up else 0; down = int(match_down.group(1)) if match_down else 0; total = int(match_total.group(1)) if match_total else 0; exp = int(match_exp.group(1)) if match_exp else 0
                    used_gb = (up + down) / 1073741824; total_gb = total / 1073741824
                    percent = round((used_gb / total_gb) * 100) if total_gb > 0 else 0
                    exp_str = datetime.datetime.fromtimestamp(exp).strftime('%d/%m/%Y') if exp > 0 else "Vĩnh viễn"
                    traffic_data = {"used": f"{used_gb:.2f}", "total": f"{total_gb:.2f}", "percent": percent, "expire": exp_str}

                # Xử lý Base64
                missing_padding = len(content) % 4
                if missing_padding: content += '=' * (4 - missing_padding)
                decoded = base64.b64decode(content).decode('utf-8', errors='ignore')
                lines = decoded.splitlines()
                
                new_lines = []
                rename_map = {}
                
                for line in lines:
                    line = line.strip()
                    if "://" in line:
                        parts = line.split("#", 1)
                        if len(parts) == 2:
                            old_name = urllib.parse.unquote(parts[1])
                            if "剩余流量" in old_name or "距离下次重置" in old_name: continue
                            
                            new_name = clean_name_string(old_name)
                            if "套餐到期" in new_name:
                                new_name = new_name.replace("套餐到期", "Exp ")
                            
                            final_name = f"{new_name} - VPN Trinh Hg"
                            rename_map[old_name] = final_name
                            new_lines.append(f"{parts[0]}#{urllib.parse.quote(final_name)}")
                    else: new_lines.append(line)

                final_b64 = base64.b64encode("\n".join(new_lines).encode()).decode()
                
                # Xử lý YAML
                yaml_text = yaml_res.text
                if "proxies:" in yaml_text:
                    # Rename Groups
                    yaml_text = yaml_text.replace("良心云", "VPN Trinh Hg").replace("顶级机场", "VPN Trinh Hg")
                    yaml_text = yaml_text.replace("自动选择", "Auto Select").replace("故障转移", "Fallback")
                    # Xóa node rác
                    yaml_text = re.sub(r'^\s*-\s*\{?name:\s*[\'"]?.*?(剩余流量|距离下次重置).*?\}?\s*$\n?', '', yaml_text, flags=re.MULTILINE)
                    # Sửa Exp
                    yaml_text = re.sub(r'套餐到期[:：]\s*(\d{4}-\d{2}-\d{2})', r'Exp \1 - VPN Trinh Hg', yaml_text)
                    # Rename Nodes
                    for old_n, new_n in rename_map.items():
                        yaml_text = yaml_text.replace(f"name: {old_n}", f"name: '{new_n}'") # Bọc ngoặc đơn fix lỗi Block Collections
                        yaml_text = yaml_text.replace(f"name: '{old_n}'", f"name: '{new_n}'")

                push_res = requests.post(API_PUSH, json={"key": token, "body_b64": final_b64, "body_yaml": yaml_text, "info": user_info, "traffic": traffic_data}, timeout=10)
                print(f"  [OK] {token}")
            except Exception as e: print(f"  [!] Error: {e}")
    except Exception as e: print(f"System Error: {e}")

if __name__ == "__main__":
    update_all_subs()
