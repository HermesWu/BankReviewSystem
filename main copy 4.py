# main.py
import pandas as pd
import json
import time
import os
import concurrent.futures  # 👈 新增：用于多线程并发抓取
import re
from openai import OpenAI
from datetime import datetime

# ======= 1. 导入采集模块 =======
from apple_fetcher import get_apple_data
from huawei_spider import get_huawei_data
from myapp_spider import get_myapp_data

# ======= 2. 核心配置区 =======
YOUR_API_KEY = "sk-cd07e5b69144417186adf31b2f94f426"
QUERY_DAYS = 14  
TOP_N = 5  

client = OpenAI(api_key=YOUR_API_KEY, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")

APPLE_ID = "422844108"   
HUAWEI_ID = "C10350054" 
MYAPP_PKG = "com.ecitic.bank.mobile"     

# ======= 3. AI 批处理核心逻辑 (极速版) =======
def batch_analyze_reviews(reviews, batch_size=10):
    analyzed_data = []
    
    for i in range(0, len(reviews), batch_size):
        batch = reviews[i:i + batch_size]
        print(f"🧠 正在并发分析第 {i//batch_size + 1} 批数据 (包含 {len(batch)} 条)...")

        batch_text = ""
        for idx, review in enumerate(batch):
            content = review.get('内容', review.get('content', ''))[:200]
            batch_text += f"【序号 {idx}】内容：{content}\n"

        prompt = f"""
        你是一个严谨的数据分析专家。请仔细阅读以下 {len(batch)} 条应用评价，并为每一条提取核心信息。
        
        待分析内容：
        {batch_text}
        
        【🚨 绝对红线】：
        请严格返回一个 JSON 对象 (Object)，该对象必须包含一个名为 "results" 的数组。
        "results" 数组的长度必须正好是 {len(batch)}，且顺序必须与输入的序号完全对应！
        
        数组中的每个元素必须包含以下三个 key：
        - "情感倾向" (仅限：正向/负向/中性)
        - "问题分类" (如：功能Bug/UI体验/闪退/登录/服务/其他)
        - "一句话总结" (用10个字以内的短句总结核心槽点或夸奖点)
        """

        try:
            res = client.chat.completions.create(
                model="qwen-plus", 
                messages=[{"role": "user", "content": prompt}], 
                response_format={"type": "json_object"}
            )
            
            response_text = res.choices[0].message.content
            
            backticks = chr(96) * 3
            clean_text = response_text.replace(backticks + "json", "").replace(backticks, "").strip()
            
            parsed_json = json.loads(clean_text)
            ai_results = parsed_json.get("results", [])
            
            for idx, review in enumerate(batch):
                if idx < len(ai_results):
                    review["情感倾向"] = ai_results[idx].get("情感倾向", "未知")
                    review["问题分类"] = ai_results[idx].get("问题分类", "未知")
                    review["一句话总结"] = ai_results[idx].get("一句话总结", "暂无总结")
                else:
                    review["情感倾向"] = "解析丢失"
                    review["问题分类"] = "解析丢失"
                    review["一句话总结"] = "解析丢失"
                analyzed_data.append(review)
                
        except Exception as e:
            print(f"❌ 第 {i//batch_size + 1} 批解析失败，原因：{e}")
            for review in batch:
                review["情感倾向"] = "解析失败"
                review["问题分类"] = "解析失败"
                review["一句话总结"] = "解析失败"
                analyzed_data.append(review)
                
        time.sleep(1)
                
    return analyzed_data


# ======= 4. 报告生成模块 =======
def generate_report(results, top_n=5):
    df_final = pd.DataFrame(results)
    
    for col in ['日期', '评分', '情感倾向', '来源', '内容', '问题分类', '一句话总结']:
        if col not in df_final.columns:
            df_final[col] = "暂无"

    df_final = df_final.sort_values(by=['日期', '评分'], ascending=[False, True])
    
    total_reviews = len(df_final)
    sentiment_counts = df_final['情感倾向'].value_counts().to_dict()
    pos_count = sentiment_counts.get('正向', 0)
    neu_count = sentiment_counts.get('中性', 0)
    neg_count = sentiment_counts.get('负向', 0)

    pos_pct = f"{(pos_count / total_reviews * 100):.1f}%" if total_reviews > 0 else "0%"
    neu_pct = f"{(neu_count / total_reviews * 100):.1f}%" if total_reviews > 0 else "0%"
    neg_pct = f"{(neg_count / total_reviews * 100):.1f}%" if total_reviews > 0 else "0%"

    sources = df_final['来源'].value_counts().to_dict()
    apple_c = sources.get("App Store", 0) + sources.get("Apple Store", 0)
    huawei_c = sources.get("华为市场", 0) + sources.get("华为应用市场", 0)
    myapp_c = sources.get("腾讯应用宝", 0)

    if total_reviews > 0:
        daily_df = df_final.groupby(['日期', '来源']).size().unstack(fill_value=0).reset_index()
        daily_df.columns.name = None 
        for col in ['华为市场', '腾讯应用宝', 'App Store', 'Apple Store']:
            if col not in daily_df.columns:
                daily_df[col] = 0
        daily_df['苹果App Store'] = daily_df['App Store'] + daily_df['Apple Store']
        daily_df = daily_df[['日期', '华为市场', '腾讯应用宝', '苹果App Store']]
        daily_df['合计'] = daily_df['华为市场'] + daily_df['腾讯应用宝'] + daily_df['苹果App Store']
        daily_df = daily_df.sort_values(by='日期', ascending=False)
        for col in ['华为市场', '腾讯应用宝', '苹果App Store', '合计']:
            daily_df[col] = daily_df[col].astype(str) + " 条"
        daily_table_html = daily_df.to_html(index=False, classes="data-table daily-table", escape=False)
    else:
        daily_table_html = "<p>暂无每日数据统计</p>"

    neg_df = df_final[df_final['情感倾向'] == '负向']
    neg_issues_list = "<li>暂无</li>"
    bad_cards = ""
    if not neg_df.empty:
        neg_top = neg_df['问题分类'].value_counts().head(top_n)
        neg_issues_list = "".join([f"<li>🔴 <b>{k}</b>：{v}次</li>" for k, v in neg_top.items()])
        for _, row in neg_df.sort_values(by='评分').head(top_n).iterrows():
            bad_cards += f'<div class="review-mini-card bad-card"><div class="rmc-header"><span class="rmc-tag bad-tag">【{row["问题分类"]}】</span><span>{row["评分"]}星</span></div><div class="rmc-content">"{row["内容"][:150]}..."</div><div class="rmc-ai">🤖 AI总结：{row["一句话总结"]}</div></div>'

    pos_df = df_final[df_final['情感倾向'] == '正向']
    pos_issues_list = "<li>暂无</li>"
    good_cards = ""
    if not pos_df.empty:
        pos_top = pos_df['问题分类'].value_counts().head(top_n)
        pos_issues_list = "".join([f"<li>🟢 <b>{k}</b>：{v}次</li>" for k, v in pos_top.items()])
        for _, row in pos_df.sort_values(by='评分', ascending=False).head(top_n).iterrows():
            good_cards += f'<div class="review-mini-card good-card"><div class="rmc-header"><span class="rmc-tag good-tag">【{row["问题分类"]}】</span><span>{row["评分"]}星</span></div><div class="rmc-content">"{row["内容"][:150]}..."</div><div class="rmc-ai">🤖 AI总结：{row["一句话总结"]}</div></div>'

    display_columns = ['来源', '具体时间', '标题', '内容', '评分', '情感倾向', '问题分类', '一句话总结']
    actual_display_columns = [col for col in display_columns if col in df_final.columns]
    detail_display_df = df_final[actual_display_columns]
    table_html = detail_display_df.to_html(index=False, classes="data-table", escape=False)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>全渠道评价分析报告</title>
        <style>
            body {{ font-family: sans-serif; background: #f5f7fa; padding: 20px; color:#333; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
            .dashboard {{ display: flex; gap: 15px; margin-bottom: 30px; }}
            .card {{ flex: 1; padding: 20px; border-radius: 8px; text-align: center; color: white; }}
            .card-total {{ background: #34495e; }} .card-pos {{ background: #27ae60; }} .card-neg {{ background: #e74c3c; }} .card-neu {{ background: #f39c12; }}
            .card h2 {{ margin: 10px 0 0; font-size: 32px; }}
            .pct {{ font-size: 16px; opacity: 0.85; margin-left: 5px; font-weight: normal; }}
            .insights {{ display: flex; gap: 20px; margin-bottom: 30px; }}
            .insight-box {{ flex: 1; border: 1px solid #eee; padding: 20px; border-radius: 8px; border-top: 4px solid #ccc; background:#fcfcfc; }}
            .box-title {{ margin-top: 0; color: #2c3e50; border-bottom: 1px dashed #ddd; padding-bottom: 10px; margin-bottom: 15px; }}
            .review-mini-card {{ background: #f9f9f9; padding: 10px; margin-top: 10px; border-radius: 4px; font-size: 13px; }}
            .bad-card {{ border-left: 4px solid #e74c3c; }} .good-card {{ border-left: 4px solid #27ae60; }}
            .rmc-header {{ display: flex; justify-content: space-between; margin-bottom: 6px; font-weight: bold; }}
            .rmc-ai {{ background: #e8f4f8; display: inline-block; padding: 3px 6px; border-radius: 4px; font-size: 12px; font-weight:bold; color: #333; }}
            .data-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 12px; }}
            .data-table th, .data-table td {{ border: 1px solid #eee; padding: 10px; text-align: left; }}
            .data-table th {{ background: #f8f9fa; }}
            .daily-table th {{ background: #e8f4f8; text-align: center; }}
            .daily-table td {{ text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1 style="text-align:center; padding-bottom:15px; border-bottom: 2px solid #eee;">📊 APP 全渠道评价智能分析报告</h1>
            <div class="dashboard">
                <div class="card card-total"><h3>总数</h3><h2>{total_reviews}</h2></div>
                <div class="card card-pos"><h3>好评</h3><h2>{pos_count}<span class="pct">({pos_pct})</span></h2></div>
                <div class="card card-neu"><h3>中评</h3><h2>{neu_count}<span class="pct">({neu_pct})</span></h2></div>
                <div class="card card-neg"><h3>差评</h3><h2>{neg_count}<span class="pct">({neg_pct})</span></h2></div>
            </div>
            <div class="insights">
                <div class="insight-box" style="flex: 1; border-top-color: #3498db;">
                    <h3 class="box-title">📊 总体渠道概况</h3>
                    <p style="font-weight: bold;">总评论数：{total_reviews} 条</p>
                    <ul style="list-style: none; padding: 0; line-height: 2.0;">
                        <li>🔹 华为应用市场：<b>{huawei_c}</b> 条</li>
                        <li>🔹 腾讯应用宝：<b>{myapp_c}</b> 条</li>
                        <li>🔹 苹果App Store：<b>{apple_c}</b> 条</li>
                    </ul>
                </div>
                <div class="insight-box" style="flex: 2; border-top-color: #9b59b6;">
                    <h3 class="box-title">📈 每日市场评论数量统计</h3>
                    <div style="overflow-x: auto;">{daily_table_html}</div>
                </div>
            </div>
            <div class="insights">
                <div class="insight-box" style="border-top-color: #e74c3c;">
                    <h3>📉 差评雷区 TOP {top_n}</h3><ul>{neg_issues_list}</ul>{bad_cards}
                </div>
                <div class="insight-box" style="border-top-color: #27ae60;">
                    <h3>📈 好评亮点 TOP {top_n}</h3><ul>{pos_issues_list}</ul>{good_cards}
                </div>
            </div>
            <h3 style="margin-top:20px; padding-bottom: 10px; border-bottom: 2px solid #eee;">🔍 评价明细清单</h3>
            <div style="overflow-x: auto;">{table_html}</div>
        </div>
    </body>
    </html>
    """
    with open("全渠道评价分析报告.html", "w", encoding="utf-8") as f:
        f.write(html_content)

# ======= 5. 调度中心 (支持多爬虫并发) =======
def run_agent_task(query_days=7):
    print(f"\n🚀 API任务启动：正在全网搜寻近 {query_days} 天的三端最新评价...")
    all_data = []

    # 定义包装函数以捕获异常
    def fetch_apple():
        try: return get_apple_data(APPLE_ID, days_limit=query_days)
        except: return []
    def fetch_huawei():
        try: return get_huawei_data(HUAWEI_ID, days_limit=query_days)
        except: return []
    def fetch_myapp():
        try: return get_myapp_data(MYAPP_PKG, days_limit=query_days)
        except: return []

    # 💡 核心：使用线程池让三个爬虫同时出发！
    print("🕸️ 正在并发启动三端抓取引擎...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_apple = executor.submit(fetch_apple)
        future_huawei = executor.submit(fetch_huawei)
        future_myapp = executor.submit(fetch_myapp)
        
        # 收集结果
        all_data.extend(future_apple.result())
        all_data.extend(future_huawei.result())
        all_data.extend(future_myapp.result())

    if not all_data:
        return {"status": "empty", "message": f"最近 {query_days} 天内，三端均未产生新评价。"}

    final_results = batch_analyze_reviews(all_data, batch_size=10)
    generate_report(final_results, top_n=TOP_N)
    
    total = len(final_results)
    bad_count = len([x for x in final_results if x.get('情感倾向') == '负向'])
    summary = f"报告已生成！共抓取 {total} 条有效评价，其中发现 {bad_count} 条差评。"
    
    print(f"🎉 {summary}")
    return {"status": "success", "message": summary, "data": final_results}

if __name__ == "__main__":
    run_agent_task(query_days=QUERY_DAYS)