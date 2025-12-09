import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import path from 'path';
import fs from 'fs';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const code = searchParams.get('code');

  if (!code) {
    return NextResponse.json({ valid: false, reason: 'Missing code' }, { status: 400 });
  }

  const pythonScript = path.join(process.cwd(), 'specs/demo/validate_stock.py');
  const venvPython = path.join(process.cwd(), 'venv/bin/python');
  const pythonCmd = fs.existsSync(venvPython) ? venvPython : 'python3';

  // 安全起见，只允许数字
  if (!/^\d{6}$/.test(code)) {
      return NextResponse.json({ valid: false, reason: 'Invalid format' });
  }

  return new Promise((resolve) => {
    exec(`${pythonCmd} "${pythonScript}" "${code}"`, (error, stdout) => {
      if (error) {
        resolve(NextResponse.json({ valid: false, reason: 'Internal Checker Error' }, { status: 500 }));
        return;
      }
      try {
        const result = JSON.parse(stdout.trim());
        resolve(NextResponse.json(result));
      } catch (e) {
        resolve(NextResponse.json({ valid: false, reason: 'Parse Error' }, { status: 500 }));
      }
    });
  });
}
