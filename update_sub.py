import requests
import base64
import urllib.parse
import re
import datetime

WORKER_DOMAIN = "https://vpntest-ad4.pages.dev"
API_LINKS = f"{WORKER_DOMAIN}/api/links"
API_PUSH = f"{WORKER_DOMAIN}/api/push_data"

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
                
                traffic_data = {"used": "0.00", "total": "0.00", "percent": 0, "expire": "Không giới hạn"}
                if user_info:
                    match_up = re.search(r'upload=(\d+)', user_info)
                    match_down = re.search(r'download=(\d+)', user_info)
                    match_total = re.search(r'total=(\d+)', user_info)
                    match_exp = re.search(r'expire=(\d+)', user_info)
                    
                    up = int(match_up.group(1)) if match_up else 0
                    down = int(match_down.group(1)) if match_down else 0
                    total = int(match_total.group(1)) if match_total else 0
                    exp = int(match_exp.group(1)) if match_exp else 0
                    
                    used_gb = (up + down) / 1073741824
                    total_gb = total / 1073741824
                    percent = round((used_gb / total_gb) * 100) if total_gb > 0 else 0
                    exp_str = datetime.datetime.fromtimestamp(exp).strftime('%d/%m/%Y') if exp > 0 else "Vĩnh viễn"
                        
                    traffic_data = {"used": f"{used_gb:.2f}", "total": f"{total_gb:.2f}", "percent": percent, "expire": exp_str}

                missing_padding = len(content) % 4
                if missing_padding: content += '=' * (4 - missing_padding)
                
                decoded = base64.b64decode(content).decode('utf-8', errors='ignore')
                lines = decoded.splitlines()
                
                new_lines = []
                rename_map = {} # Bản đồ ánh xạ tên cũ -> tên mới để fix YAML
                
                for line in lines:
                    line = line.strip()
                    if not line: continue
                    if "://" in line:
                        try:
                            parts = line.split("#", 1)
                            if len(parts) == 2:
                                old_name = urllib.parse.unquote(parts[1])
                                
                                # XÓA BỎ DÒNG DATA VÀ RESET (Chỉ giữ Exp)
                                if "剩余流量" in old_name or "距离下次重置剩余" in old_name:
                                    continue
                                
                                new_name = old_name
                                if "套餐到期" in new_name: 
                                    new_name = new_name.replace("套餐到期：", "Exp: ").replace("套餐到期:", "Exp: ")
                                else:
                                    # Translate
                                    new_name = new_name.replace("良心云", "").replace("自动选择", "Auto Select").replace("故障转移", "Fallback")
                                    new_name = new_name.replace("🇨🇳台湾", "🇹🇼 Taiwan ").replace("🇭🇰香港", "🇭🇰 Hong Kong ").replace("🇸🇬新加坡", "🇸🇬 Singapore ")
                                    new_name = new_name.replace("🇯🇵日本", "🇯🇵 Japan ").replace("🇺🇸美国", "🇺🇸 USA ").replace("🇰🇷韩国", "🇰🇷 Korea ")
                                    new_name = new_name.replace("台湾", "Taiwan ").replace("香港", "Hong Kong ").replace("新加坡", "Singapore ")
                                    new_name = new_name.replace("日本", "Japan ").replace("美国", "USA ").replace("韩国", "Korea ")
                                    new_name = new_name.replace("高速", " High Speed ").replace("专线", " Private ").replace("流媒体", " Streaming").replace("0.1倍", " 0.1x")
                                    new_name = re.sub(r'\|BGP\|?', ' ', new_name)
                                    new_name = re.sub(r'\|', ' ', new_name)
                                
                                clean_name = " ".join(new_name.split())
                                final_name = f"{clean_name} | VPN Trinh Hg"
                                
                                rename_map[old_name] = final_name
                                new_lines.append(f"{parts[0]}#{urllib.parse.quote(final_name)}")
                            else: new_lines.append(line)
                        except: new_lines.append(line)
                    else: new_lines.append(line)

                final_string = "\n".join(new_lines) if new_lines else decoded
                final_b64 = base64.b64encode(final_string.encode()).decode()
                missing = len(final_b64) % 4
                if missing: final_b64 += "=" * (4 - missing)
                
                # --- QUÉT SẠCH YAML BẰNG RENAME MAP ---
                yaml_text = yaml_res.text
                if "proxies:" in yaml_text:
                    # Thay thế toàn bộ tên cũ thành tên mới (Fix luôn cả cụm Proxy-groups)
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
            except Exception as e:
                print(f"  [!] Lỗi xử lý Node: {e}")
    except Exception as e: print(f"Lỗi hệ thống: {e}")

if __name__ == "__main__":
    update_all_subs()
