from fastapi import FastAPI
from main import run_agent_task
import uvicorn

app = FastAPI()

# 定义一个接口，名字叫 /analyze
@app.get("/analyze")
def analyze_reviews(days: int = 7):
    """
    这个接口接收机器人传过来的天数 (days)
    然后去调用我们写好的爬虫主程序
    """
    print(f"🤖 收到机器人请求！要求抓取近 {days} 天的数据...")
    
    # 调用 main.py 里的函数
    result = run_agent_task(query_days=days)
    
    # 把结果打包发回给机器人
    return result

if __name__ == "__main__":
    # 在 8000 端口启动服务
    print("🌟 智能体后台 API 已启动！正在监听机器人的呼唤...")
    uvicorn.run(app, host="0.0.0.0", port=8000)