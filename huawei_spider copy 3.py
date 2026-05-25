# huawei_spider.py
from playwright.sync_api import sync_playwright
import pandas as pd
import re

def get_huawei_data(app_id="C10350054", days_limit=14):
    print(f"🚀 启动华为渠道采集 (精准内容提纯版, 近 {days_limit} 天)...")
    raw_reviews = []
    threshold_date = pd.Timestamp.now().tz_localize(None) - pd.Timedelta(days=days_limit)
    
    with sync_playwright() as p:
        browser = p.webkit.launch(headless=True)
        page = browser.new_page()
        
        try:
            url = f"https://appgallery.huawei.com/app/{app_id}"
            page.goto(url, timeout=60000)
            page.wait_for_timeout(5000) 
            
            # 滚动加载更多
            for _ in range(8):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2000)
                
            divs = page.locator("div").all()
            for div in divs:
                try:
                    class_name = div.get_attribute("class") or ""
                    
                    # 防线1：排除明显的“父容器”或“列表框”
                    if re.search(r'comment|review', class_name, re.IGNORECASE) and \
                       not re.search(r'list|container|wrapper|section|group|box', class_name, re.IGNORECASE):
                       
                        text = div.inner_text()
                        if not text or len(text) < 15: continue
                        
                        text_clean = text.replace('\n', ' | ')
                        
                        # 防线2：拦截带页面头部的巨型外框容器
                        if "查看全部" in text_clean and "人评分" in text_clean:
                            continue
                            
                        # 防线3：拦截包含多个评价日期的“一锅端”文本
                        date_count = len(re.findall(r'202\d[-/\.年]\d{1,2}[-/\.月]\d{1,2}', text_clean))
                        if date_count > 2:
                            continue
                        
                        # 提取完整的年月日作为时间戳
                        date_match = re.search(r'(202\d)[-/\.年](\d{1,2})[-/\.月](\d{1,2})', text_clean)
                        
                        if date_match:
                            y, m, d = date_match.groups()
                            review_date = pd.to_datetime(f"{y}-{m}-{d}")
                            
                            if review_date < threshold_date: 
                                continue # 超过设定天数，丢弃
                                
                            # ====== 🧹 新增：内容提纯逻辑 ======
                            # 将原始文本按行拆开，逐行过滤不要的杂质
                            lines = [line.strip() for line in text.split('\n') if line.strip()]
                            pure_content_lines = []
                            for line in lines:
                                # 过滤 1: 用户名 (通常包含华为的打码星号 ***)
                                if '***' in line: continue
                                # 过滤 2: 日期和时间行
                                if re.search(r'202\d[-/\.年]\d{1,2}[-/\.月]\d{1,2}', line): continue
                                # 过滤 3: 版本号和评级星星 (如 (12.1.0) 或 ⭐️)
                                if re.search(r'^\(?\d+\.\d+\.\d+\)?$', line) or '⭐' in line or '★' in line: continue
                                
                                # 经过过滤后留下的，就是真正的纯文本内容
                                pure_content_lines.append(line)
                                
                            final_content = " ".join(pure_content_lines)
                            if not final_content: continue # 如果清洗后啥也不剩了，直接跳过
                            # =====================================

                            date_str = review_date.strftime('%Y-%m-%d')
                            raw_reviews.append({
                                "来源": "华为市场",
                                "日期": date_str,
                                "具体时间": date_str + " 00:00:00",
                                "标题": "无标题",
                                "内容": final_content, # 👈 这里替换为清洗后的纯正文
                                "评分": 0
                            })
                            
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"❌ 华为抓取异常: {e}")
        finally:
            browser.close() 
            
    # 去重返回
    return [dict(t) for t in {tuple(d.items()) for d in raw_reviews}]