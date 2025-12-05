import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  const { prompt, model } = await request.json();

  if (!prompt) {
    return NextResponse.json({ error: 'Missing prompt' }, { status: 400 });
  }

  const apiKey = process.env.DEEPSEEK_API_KEY;
  if (!apiKey) {
    return NextResponse.json({ error: 'Missing DeepSeek API Key' }, { status: 500 });
  }

  const systemPrompt = `你是一位精通 A 股量化交易策略的专家助手。
你的目标是将用户的自然语言策略想法转化为一个具体的“系统提示词 (System Prompt)”，该提示词将用于指导一个 AI 交易代理 (Agent)。

**重要约束（必须遵守）：**
1. **A 股市场规则**：仅支持做多 (Long Only)，严禁生成做空/融券策略。遵守 T+1 交易制度（当日买入次日才能卖）。
2. **单标的/全仓位上下文**：本策略仅用于回测“单只股票”。资金是专款专用的，**严禁**生成任何关于“分散投资”、“行业配置”、“持仓只占总资产X%”的规则（因为这就这一只股，不买它资金就闲置）。
3. **日线级别 (Daily Only)**：决策基于“日K线”收盘数据，执行于“次日开盘”。**严禁**生成日内择时规则（如“收盘前30分钟”、“盘中突破”），因为回测系统无法感知日内时间。
4. **记忆限制**：AI 代理主要依赖当日行情数据。虽然它能看到最近几笔交易记录，但不要生成依赖长期复杂持仓记忆（如“持仓满 N 天”）的规则，除非能通过 K 线推断。

**该 AI 交易代理的输入数据**：
- 价格 (Price)
- 均线: MA5, MA10, MA20, MA60, EMA20
- MACD (DIF, DEA, 柱状图)
- RSI (6, 12, 24)
- 布林带 (上轨, 中轨, 下轨)
- KDJ (K, D, J)
- CCI
- 成交量 (Volume), 涨跌幅 (Pct Change)

**你生成的 System Prompt 结构应包含：**
1. **角色定义**：基于用户的想法定义 Agent 的交易性格（保守/激进/趋势/反转）。
2. **核心哲学**：简述策略逻辑。
3. **入场条件 (Long)**：基于上述指标的明确买入规则。
4. **离场条件 (Sell/Close)**：止盈、止损或趋势破坏的卖出规则。
5. **风险管理**：仓位控制（如单笔 max 30%）、最大回撤控制等。

请仅输出生成的系统提示词文本，直接使用中文。不要添加任何对话式的废话。`;

  try {
    const payload: any = {
      model: model || 'deepseek-chat',
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: `User's Strategy Idea: "${prompt}"\n\nPlease generate the System Prompt following the instructions.` }
      ]
    };

    const res = await fetch('https://api.deepseek.com/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.text();
      return NextResponse.json({ error: `DeepSeek API error: ${err}` }, { status: 500 });
    }

    const data = await res.json();
    const message = data.choices[0].message;
    const result = message.content;
    const reasoning = message.reasoning_content;

    return NextResponse.json({ result, reasoning });

  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 });
  }
}