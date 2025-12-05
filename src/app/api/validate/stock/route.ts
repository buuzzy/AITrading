import { NextResponse } from 'next/server';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const code = searchParams.get('code');

  // 1. Basic Format: 6 digits
  if (!code || !/^\d{6}$/.test(code)) {
    return NextResponse.json({ valid: false, reason: 'Invalid format (must be 6 digits)' });
  }

  // 2. A-Share Prefix Logic
  // Rules:
  // SH: 60xxxx (Main), 68xxxx (Star), 5xxxxx (ETF/Fund)
  // SZ: 00xxxx (Main), 30xxxx (ChiNext), 15xxxx (ETF)
  // BJ: 43xxxx, 83xxxx, 87xxxx
  
  const validPrefixes = [
    '60', '68', // SH Stock
    '00', '30', '02', // SZ Stock
    '43', '83', '87', // BJ Stock
    '51', '56', '58', // SH ETF (Common)
    '15', '16', '18'  // SZ ETF (Common)
  ];

  const isValidPrefix = validPrefixes.some(prefix => code.startsWith(prefix));

  if (!isValidPrefix) {
    return NextResponse.json({ 
      valid: false, 
      reason: '请输入正确的股票代码' 
    });
  }

  return NextResponse.json({ valid: true, name: `Valid Format (${code})` });
}