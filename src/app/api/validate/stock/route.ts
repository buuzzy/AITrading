import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import path from 'path';
import fs from 'fs';
import util from 'util';

const execAsync = util.promisify(exec);

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

  try {
    const { stdout } = await execAsync(`${pythonCmd} "${pythonScript}" "${code}"`);
    try {
      const result = JSON.parse(stdout.trim());
      return NextResponse.json(result);
    } catch (e) {
      return NextResponse.json({ valid: false, reason: 'Parse Error' }, { status: 500 });
    }
  } catch (error) {
    return NextResponse.json({ valid: false, reason: 'Internal Checker Error' }, { status: 500 });
  }
}
