import { NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs';
import { v4 as uuidv4 } from 'uuid';
import os from 'os';

// 强制动态模式
export const dynamic = 'force-dynamic';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { strategy_config, symbol, start_date, end_date } = body;

    if (!strategy_config || !symbol || !start_date || !end_date) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
    }

    // 1. 准备 Config 文件
    const runId = uuidv4();
    const tempDir = os.tmpdir();
    const configFilePath = path.join(tempDir, `strategy_${runId}.json`);
    fs.writeFileSync(configFilePath, JSON.stringify(strategy_config, null, 2));

    // 2. 准备环境
    const pythonScript = path.join(process.cwd(), 'specs/demo/cli_runner.py');
    const venvPython = path.join(process.cwd(), 'venv/bin/python');
    const pythonCmd = fs.existsSync(venvPython) ? venvPython : 'python3';

    console.log(`[Backtest API] Starting stream for ${symbol}...`);

    // 3. 创建流式响应
    const encoder = new TextEncoder();
    
    const stream = new ReadableStream({
      start(controller) {
        const child = spawn(pythonCmd, [
          '-u', // 关键：禁用 Python 缓冲，强制实时输出
          pythonScript,
          '--run_id', runId,
          '--symbol', symbol,
          '--start', start_date,
          '--end', end_date,
          '--config', configFilePath
        ]);

        // 实时转发 stdout
        child.stdout.on('data', (data) => {
          // 发送数据块
          controller.enqueue(encoder.encode(data.toString()));
        });

        // 实时转发 stderr (作为日志)
        child.stderr.on('data', (data) => {
          controller.enqueue(encoder.encode(`[STDERR] ${data.toString()}`));
        });

        child.on('close', (code) => {
          // 清理文件
          try { fs.unlinkSync(configFilePath); } catch (e) {}
          
          if (code !== 0) {
            controller.enqueue(encoder.encode(`\n[Process exited with code ${code}]`));
          }
          controller.close();
        });

        child.on('error', (err) => {
          controller.enqueue(encoder.encode(`\n[Spawn Error] ${err.message}`));
          controller.close();
        });
      }
    });

    return new Response(stream, {
      headers: {
        'Content-Type': 'text/plain; charset=utf-8',
        'Transfer-Encoding': 'chunked',
        'X-Content-Type-Options': 'nosniff',
      },
    });

  } catch (error: any) {
    console.error('[Backtest API] Error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}