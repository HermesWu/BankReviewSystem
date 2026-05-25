# huawei_spider.py
from playwright.sync_api import sync_playwright
import pandas as pd
import re
import base64

def get_huawei_data(app_id="C10350054", days_limit=30):
    print(f"🚀 启动华为渠道采集 (DOM雷达强制穿透版, 近 {days_limit} 天)...")
    raw_reviews = []
    threshold_date = pd.Timestamp.now().tz_localize(None) - pd.Timedelta(days=days_limit)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True, 
            executable_path='/root/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome',
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        page = browser.new_page()
        
        try:
            url = f"https://appgallery.huawei.com/app/{app_id}"
            page.goto(url, timeout=60000)
            page.wait_for_timeout(2000) 
            
            # ==============================================================
            print("⏬ 正在执行【动态雷达扫雷】平滑滚动...")
            clicked = False
            
            # ⏱️ 使用键盘 PageDown 滚动，并用原生 JS 强点，大幅提升稳定性
            for _ in range(12): 
                # 模拟真实键盘向下翻页，比 scrollBy 更有可能触发前端组件渲染
                page.keyboard.press("PageDown")
                page.wait_for_timeout(800)
                
                try:
                    # 🌟 终极必杀：不要用 is_visible()，直接用 count() 查内存
                    # 只要这个外壳渲染到了 DOM 里（哪怕是隐藏的、透明的、或者大小为0的）
                    btn = page.locator(".pcscorecommentlistcard .more").first
                    if btn.count() > 0:
                        print("🎯 内存中捕获到底层 DOM 节点，直接注入原生 JS 强点...")
                        # 放弃 Playwright 的物理模拟鼠标点击，直接底层触发前端事件
                        btn.evaluate("node => node.click()")
                        page.wait_for_timeout(2500)
                        print("✅ 成功破门进入华为评论详情页！")
                        clicked = True
                        break 
                except:
                    pass 
            
            if not clicked:
                print("⚠️ 警告：雷达扫描完毕未发现节点，将直接抓取当前可视评价！")
            # ==============================================================

            print("🔄 正在深挖加载新评论...")
            for _ in range(8):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1000)
                
            divs = page.locator("div").all()
            for div in divs:
                try:
                    class_name = div.get_attribute("class") or ""
                    
                    if re.search(r'comment|review', class_name, re.IGNORECASE) and \
                       not re.search(r'list|container|wrapper|section|group|box', class_name, re.IGNORECASE):
                       
                        text = div.inner_text()
                        if not text or len(text) < 15: continue
                        
                        html_content = div.inner_html()
                        review_score = 0
                        star_box_match = re.search(r'class="[^"]*newStarBox[^"]*"[^>]*>(.*?)</div>', html_content, re.IGNORECASE | re.DOTALL)
                        
                        if star_box_match:
                            box_html = star_box_match.group(1)
                            img_b64_list = re.findall(r'src="data:image/svg\+xml;base64,([^"]+)"', box_html)
                            for b64_str in img_b64_list:
                                try:
                                    svg_text = base64.b64decode(b64_str).decode('utf-8', errors='ignore')
                                    if 'FDC51E' in svg_text.upper(): review_score += 1
                                except: pass
                            if review_score == 0 and len(img_b64_list) > 0:
                                first_star = img_b64_list[0]
                                review_score = img_b64_list.count(first_star)

                        text_clean = text.replace('\n', ' | ')
                        if "查看全部" in text_clean and "人评分" in text_clean: continue
                            
                        date_count_A = len(re.findall(r'202\d[-/\.年]\d{1,2}[-/\.月]\d{1,2}', text_clean))
                        date_count_B = len(re.findall(r'(?<!\d)\d{1,2}/\d{1,2}/202\d', text_clean))
                        if (date_count_A + date_count_B) > 2: continue
                        
                        date_match_A = re.search(r'(202\d)[-/\.年](\d{1,2})[-/\.月](\d{1,2})', text_clean)
                        date_match_B = re.search(r'(?<!\d)(\d{1,2})/(\d{1,2})/(202\d)', text_clean)
                        
                        review_date = None
                        if date_match_A:
                            y, m, d = date_match_A.groups()
                            review_date = pd.to_datetime(f"{y}-{m}-{d}")
                        elif date_match_B:
                            m, d, y = date_match_B.groups()
                            review_date = pd.to_datetime(f"{y}-{m}-{d}")
                        
                        if review_date:
                            if review_date < threshold_date: 
                                # 🌟 华为版智能熔断：遇到旧评价直接停止！
                                print(f"  🛑 [华为熔断触发] 发现过期评论 ({review_date.strftime('%Y-%m-%d')})，停止解析！")
                                break 
                                
                            lines = [line.strip() for line in text.split('\n') if line.strip()]
                            pure_content_lines = []
                            for line in lines:
                                if '***' in line: continue
                                if re.search(r'202\d[-/\.年]\d{1,2}[-/\.月]\d{1,2}', line) or re.search(r'(?<!\d)\d{1,2}/\d{1,2}/202\d', line): continue
                                if re.search(r'^\(?\d+\.\d+\.\d+\)?$', line): continue
                                pure_content_lines.append(line)
                                
                            final_content = " ".join(pure_content_lines)
                            if not final_content: continue

                            date_str = review_date.strftime('%Y-%m-%d')
                            raw_reviews.append({
                                "来源": "华为市场", "日期": date_str, "具体时间": date_str + " 00:00:00",
                                "标题": "无标题", "内容": final_content, "评分": review_score
                            })
                except Exception:
                    continue
        except Exception as e:
            print(f"❌ 华为抓取异常: {e}")
        finally:
            browser.close() 
            
    return [dict(t) for t in {tuple(d.items()) for d in raw_reviews}]