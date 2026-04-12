import requests
import base64
import urllib.parse
import re
import datetime

WORKER_DOMAIN = "https://vpntest-ad4.pages.dev"
API_LINKS = f"{WORKER_DOMAIN}/api/links"
API_PUSH = f"{WORKER_DOMAIN}/api/push_data"

def clean_text_global(text):
    text = urllib.parse.unquote(text)
    
    # TIÊU DIỆT BGP
    text = re.sub(r'(?i)bgp', '', text)
    
    # Đổi tên Group / Nhà cung cấp để khớp với Rule
    text = text.replace("顶级机场", "VPN Trinh Hg").replace("良心云", "VPN Trinh Hg")
    text = text.replace("自动选择", "Auto Select").replace("故障转移", "Fallback")
    
    # Dịch thuật
    text = text.replace("🇨🇳台湾", "🇹🇼 Taiwan ").replace("台湾", "Taiwan ")
    text = text.replace("🇭🇰香港", "🇭🇰 Hong Kong ").replace("香港", "Hong Kong ")
    text = text.replace("🇸🇬新加坡", "🇸🇬 Singapore ").replace("新加坡", "Singapore ")
    text = text.replace("🇯🇵日本", "🇯🇵 Japan ").replace("日本", "Japan ")
    text = text.replace("🇺🇸美国", "🇺🇸 USA ").replace("美国", "USA ")
    text = text.replace("🇰🇷韩国", "🇰🇷 Korea ").replace("韩国", "Korea ")
    text = text.replace("高速", " High Speed ").replace("专线", " Private ").replace("流媒体", " Streaming").replace("0.1倍", " 0.1x")
    
    # Fix dấu gạch ngang và dấu |
    text = text.replace("|", "-")
    text = re.sub(r'[|\-]+', '-', text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.replace(" -", "-").replace("- ", "-").replace("-", " - ")
    
    if text.endswith("-"): text = text[:-1].strip()
    return text

def update_all_subs():
    try:
        res = requests.get(API_LINKS, timeout=10)
        links_db = res.json()
        
        # Lấy danh sách toàn bộ mã ẩn (Sub-ID) để update
        for item in links_db:
            orig_url = item.get("orig")
            masked_url = item.get("masked")
            if not orig_url or not masked_url: continue
            
            # Lấy token từ link ẩn (Mã Sub-ID)
            parsed_masked = urllib.parse.urlparse(masked_url)
            qs_masked = urllib.parse.parse_qs(parsed_masked.query)
            token = (qs_masked.get("OwO") or qs_masked.get("token") or [None])[0]
            
            if not token: continue
                
            print(f"-> Đang kéo data gốc cho Token (Sub-ID): {token}")
            
            try:
                b64_res = requests.get(orig_url, headers={"User-Agent": "v2rayN/6.23"}, timeout=15)
                yaml_res = requests.get(orig_url, headers={"User-Agent": "Clash-Verge"}, timeout=15)
                
                if b64_res.status_code != 200: continue
                
                content = b64_res.text.strip()
                user_info = b64_res.headers.get("subscription-userinfo", "")
                
                # Cào Data để Web hiển thị
                traffic_data = {"used": "0.00", "total": "0.00", "percent": 0, "expire": "Vĩnh viễn"}
                if user_info:
                    match_up = re.search(r'upload=(\d+)', user_info); match_down = re.search(r'download=(\d+)', user_info); match_total = re.search(r'total=(\d+)', user_info); match_exp = re.search(r'expire=(\d+)', user_info)
                    up = int(match_up.group(1)) if match_up else 0; down = int(match_down.group(1)) if match_down else 0; total = int(match_total.group(1)) if match_total else 0; exp = int(match_exp.group(1)) if match_exp else 0
                    used_gb = (up + down) / 1073741824; total_gb = total / 1073741824
                    percent = round((used_gb / total_gb) * 100) if total_gb > 0 else 0
                    exp_str = datetime.datetime.fromtimestamp(exp).strftime('%d/%m/%Y') if exp > 0 else "Vĩnh viễn"
                    traffic_data = {"used": f"{used_gb:.2f}", "total": f"{total_gb:.2f}", "percent": percent, "expire": exp_str}

                # ==========================
                # 1. BUILD BASE64 SIÊU SẠCH (XOÁ INFO)
                # ==========================
                missing_padding = len(content) % 4
                if missing_padding: content += '=' * (4 - missing_padding)
                decoded = base64.b64decode(content).decode('utf-8', errors='ignore')
                
                new_lines = []
                rename_map = {} 
                
                for line in decoded.splitlines():
                    line = line.strip()
                    if not line: continue
                    if "://" in line:
                        parts = line.split("#", 1)
                        if len(parts) == 2:
                            old_name = urllib.parse.unquote(parts[1])
                            
                            # DIỆT SẠCH DÒNG DATA, RESET VÀ EXP TRONG NODE
                            if "剩余流量" in old_name or "距离下次重置" in old_name or "套餐到期" in old_name:
                                continue
                                
                            new_name = clean_text_global(old_name)
                            final_name = f"{new_name.strip()} - VPN Trinh Hg"
                            
                            rename_map[old_name] = final_name
                            new_lines.append(f"{parts[0]}#{urllib.parse.quote(final_name)}")
                        else: new_lines.append(line)
                    else: new_lines.append(line)

                final_b64 = base64.b64encode("\n".join(new_lines).encode()).decode()
                missing = len(final_b64) % 4
                if missing: final_b64 += "=" * (4 - missing)
                
                # ==========================
                # 2. BUILD YAML (CHỐNG LỖI NOT FOUND)
                # ==========================
                yaml_text = yaml_res.text
                if "proxies:" in yaml_text:
                    # Chém sạch dòng Info trong file YAML
                    yaml_text = re.sub(r'^.*?(?:剩余流量|距离下次重置|套餐到期).*?\r?\n', '', yaml_text, flags=re.MULTILINE)
                    
                    # Áp dụng thay thế toàn cục (Đảm bảo Node, Group, Rule đều khớp)
                    yaml_text = clean_text_global(yaml_text)
                    
                    # Map chính xác tên node từ Base64 sang YAML
                    for old_n, new_n in rename_map.items():
                        yaml_text = yaml_text.replace(old_n, new_n)
                else:
                    yaml_text = ""

                payload = {
                    "key": token,
                    "body_b64": final_b64,
                    "body_yaml": yaml_text,
                    "info": user_info,
                    "traffic": traffic_data
                }
                push_res = requests.post(API_PUSH, json=payload, timeout=10)
                print(f"  [OK] Đã push thành công: {token}" if push_res.status_code == 200 else f"  [FAIL] Push lỗi")
            except Exception as e: print(f"  [!] Lỗi: {e}")
    except Exception as e: print(f"Hệ thống lỗi: {e}")

if __name__ == "__main__":
    update_all_subs()
