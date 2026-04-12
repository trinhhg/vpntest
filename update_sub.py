import requests
import base64
import urllib.parse
import re
import datetime
import yaml # BẮT BUỘC THÊM pyyaml VÀO GITHUB ACTIONS

WORKER_DOMAIN = "https://vpntest-ad4.pages.dev"
API_LINKS = f"{WORKER_DOMAIN}/api/links"
API_PUSH = f"{WORKER_DOMAIN}/api/push_data"

def clean_text_global(text):
    text = urllib.parse.unquote(text)
    text = text.replace("🇨🇳台湾", "🇹🇼 Taiwan ").replace("台湾", "Taiwan ")
    text = text.replace("🇭🇰香港", "🇭🇰 Hong Kong ").replace("香港", "Hong Kong ")
    text = text.replace("🇸🇬新加坡", "🇸🇬 Singapore ").replace("新加坡", "Singapore ")
    text = text.replace("🇯🇵日本", "🇯🇵 Japan ").replace("日本", "Japan ")
    text = text.replace("🇺🇸美国", "🇺🇸 USA ").replace("美国", "USA ")
    text = text.replace("🇰🇷韩国", "🇰🇷 Korea ").replace("韩国", "Korea ")
    text = text.replace("高速", " High Speed ").replace("专线", " Private ").replace("流媒体", " Streaming").replace("0.1倍", " 0.1x")
    
    text = re.sub(r'(?i)bgp', '', text)
    text = re.sub(r'[|\-]+', '-', text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.replace(" -", "-").replace("- ", "-").replace("-", " - ")
    if text.endswith("-"): text = text[:-1].strip()
    return text

def update_all_subs():
    try:
        res = requests.get(API_LINKS, timeout=10)
        links_db = res.json()
        
        # Chỉ lấy danh sách Token GỐC để fetch data (không fetch link phụ)
        unique_origins = {}
        for item in links_db:
            orig_url = item.get("orig")
            if not orig_url: continue
            parsed_orig = urllib.parse.urlparse(orig_url)
            qs_orig = urllib.parse.parse_qs(parsed_orig.query)
            token_list = qs_orig.get("OwO") or qs_orig.get("token")
            if token_list:
                unique_origins[token_list[0]] = orig_url
                
        for token, orig_url in unique_origins.items():
            print(f"-> Đang cào gốc Token: {token}")
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

                # ==========================
                # 1. BÓC BASE64 - LẤY MAP ĐỔI TÊN
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
                            
                            # DIỆT DÒNG INFO
                            if "剩余流量" in old_name or "距离下次重置" in old_name or "套餐到期" in old_name:
                                continue
                                
                            clean_n = clean_text_global(old_name)
                            clean_n = clean_n.replace("良心云", "").replace("顶级机场", "").strip()
                            if clean_n.startswith("-"): clean_n = clean_n[1:].strip()
                            final_name = f"{clean_n} - VPN Trinh Hg" if clean_n else "VPN Trinh Hg"
                            
                            rename_map[old_name] = final_name
                            new_lines.append(f"{parts[0]}#{urllib.parse.quote(final_name)}")
                        else: new_lines.append(line)
                    else: new_lines.append(line)

                final_b64 = base64.b64encode("\n".join(new_lines).encode()).decode()
                
                # ==========================
                # 2. PARSE YAML CHUẨN CẤU TRÚC
                # ==========================
                final_yaml = ""
                try:
                    y_obj = yaml.safe_load(yaml_res.text)
                    
                    # 2.1 Rename Proxies & Remove Info Nodes
                    if 'proxies' in y_obj:
                        valid_proxies = []
                        for p in y_obj['proxies']:
                            n = p.get('name', '')
                            if "剩余流量" in n or "距离下次重置" in n or "套餐到期" in n:
                                continue
                            p['name'] = rename_map.get(n, clean_text_global(n) + " - VPN Trinh Hg")
                            valid_proxies.append(p)
                        y_obj['proxies'] = valid_proxies

                    # 2.2 Rename Groups & Update Their Proxy Lists
                    if 'proxy-groups' in y_obj:
                        for g in y_obj['proxy-groups']:
                            g_name = g.get('name', '')
                            if '顶级机场' in g_name or '良心云' in g_name:
                                g['name'] = 'VPN Trinh Hg'
                            elif '自动选择' in g_name:
                                g['name'] = 'Auto Select'
                            elif '故障转移' in g_name:
                                g['name'] = 'Fallback'
                            
                            if 'proxies' in g:
                                updated_group_proxies = []
                                for px in g['proxies']:
                                    if "剩余流量" in px or "距离下次重置" in px or "套餐到期" in px:
                                        continue
                                    updated_group_proxies.append(rename_map.get(px, px))
                                g['proxies'] = updated_group_proxies

                    # 2.3 Rename Rules to match Group Names
                    if 'rules' in y_obj:
                        new_rules = []
                        for r in y_obj['rules']:
                            parts = r.split(',')
                            if len(parts) >= 3:
                                target = parts[2]
                                if '顶级机场' in target or '良心云' in target: parts[2] = 'VPN Trinh Hg'
                                elif '自动选择' in target: parts[2] = 'Auto Select'
                                elif '故障转移' in target: parts[2] = 'Fallback'
                                else: parts[2] = rename_map.get(target, target)
                                new_rules.append(','.join(parts))
                            else:
                                new_rules.append(r)
                        y_obj['rules'] = new_rules

                    # Dump lại chuẩn YAML không lỗi
                    final_yaml = yaml.dump(y_obj, allow_unicode=True, sort_keys=False, Dumper=yaml.SafeDumper)
                except Exception as ye:
                    print(f"YAML Parse Lỗi, dùng chuỗi fallback: {ye}")

                payload = {"key": token, "body_b64": final_b64, "body_yaml": final_yaml, "info": user_info, "traffic": traffic_data}
                requests.post(API_PUSH, json=payload, timeout=10)
                print(f"  [OK] Đã push thành công Token Gốc: {token}")
            except Exception as e: print(f"  [!] Lỗi: {e}")
    except Exception as e: print(f"Hệ thống lỗi: {e}")

if __name__ == "__main__":
    update_all_subs()
