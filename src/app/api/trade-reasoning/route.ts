import { NextResponse } from 'next/server';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const stock_code = searchParams.get('stock_code');
  const date = searchParams.get('date');

  if (!stock_code || !date) {
    return NextResponse.json({ error: 'Missing parameters' }, { status: 400 });
  }

  const dateStr = date.replace(/-/g, '');
  let run_id = searchParams.get('run_id');

  // 0. Fetch latest run_id if missing
  if (!run_id) {
    const url = (process.env.AITRADE_SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL) as string;
    const key = (process.env.AITRADE_SUPABASE_KEY || process.env.NEXT_PUBLIC_SUPABASE_KEY) as string;
    if (url && key) {
      try {
        const runsRes = await fetch(`${url}/rest/v1/runs?stock_code=eq.${stock_code}&order=created_at.desc&limit=1&select=run_id`, {
          headers: { apikey: key, Authorization: `Bearer ${key}` },
          cache: 'no-store'
        });
        if (runsRes.ok) {
          const runsData = await runsRes.json();
          if (runsData && runsData.length > 0) {
            run_id = runsData[0].run_id;
          }
        }
      } catch (e) {}
    }
  }

  // 1. Determine Base URL and Fetcher (Public vs Authenticated)
  let fetcher = global.fetch;
  let baseUrl = '';
  
  const storageDomain = process.env.STORAGE_DOMAIN || process.env.NEXT_PUBLIC_STORAGE_DOMAIN;
  
  // Check R2 credentials
  const r2AccessKey = process.env.R2_ACCESS_KEY_ID;
  const r2SecretKey = process.env.R2_SECRET_ACCESS_KEY;
  const r2Endpoint = process.env.R2_ENDPOINT_URL;
  const r2Bucket = process.env.R2_BUCKET_NAME;

  if (storageDomain) {
    // Public Domain Mode
    baseUrl = storageDomain.startsWith('http') ? storageDomain : `https://${storageDomain}`;
  } else if (r2AccessKey && r2SecretKey && r2Endpoint && r2Bucket) {
    // Authenticated R2 Mode
    try {
      const { AwsClient } = await import("aws4fetch");
      const client = new AwsClient({
        accessKeyId: r2AccessKey,
        secretAccessKey: r2SecretKey,
        service: 's3',
      });
      fetcher = client.fetch.bind(client);
      // Remove trailing slash from endpoint to avoid double slashes
      baseUrl = `${r2Endpoint.replace(///$/, '')}/${r2Bucket}`;
    } catch (e) {
      console.error("Failed to init AwsClient", e);
      return NextResponse.json({ error: 'R2 client init failed' }, { status: 500 });
    }
  }
  else {
    return NextResponse.json({ error: 'Storage domain not configured' }, { status: 500 });
  }

  // 2. Try Paths
  const pathsToTry = [];
  
  // Priority: Isolated Run Path
  if (run_id) {
      pathsToTry.push(`aitrading/runs/${run_id}/${dateStr}/llm_${stock_code}.json`);
  }

  // Legacy Paths
  pathsToTry.push(
    `aitrading/${stock_code}/${dateStr}/llm_${stock_code}.json`,
    `aitrading/${stock_code}/${date}/llm_${stock_code}.json`,
    `${stock_code}/${dateStr}/llm_${stock_code}.json`,
    `${stock_code}/${date}/llm_${stock_code}.json`
  );


  const triedUrls: string[] = [];

  try {
    for (const path of pathsToTry) {
      // Ensure no double slashes if baseUrl ends with /
      const cleanBase = baseUrl.replace(///$/, '');
      const url = `${cleanBase}/${path}`;
      triedUrls.push(url);
      
      try {
        const res = await fetcher(url, { next: { revalidate: 3600 } });
        if (res.ok) {
          return processResponse(res, date);
        }
      } catch (e) {
        console.warn(`Failed to fetch ${url}:`, e);
        continue;
      }
    }
    
    return NextResponse.json({ error: 'Data not found in storage', triedUrls }, { status: 404 });

  } catch (error) {
    console.error(error);
    return NextResponse.json({ error: 'Failed to fetch reasoning' }, { status: 500 });
  }
}

async function processResponse(res: Response, dateKey: string) {
  const json = await res.json();
  
  let data = json;
  
  if (json[dateKey]) {
    data = json[dateKey];
  } else {
    const keys = Object.keys(json);
    if (keys.length === 1 && keys[0].match(/^\d{4}-\d{2}-\d{2}$/)) {
      data = json[keys[0]];
    }
  }

  const market_prompt = data.market_prompt || '';
  const { thinking, analysis } = splitThinkingAndAnalysis(market_prompt);
  
  const reasoning = extractReasoning(data.reasoning || '', market_prompt);
  const technical_analysis = extractTA(analysis);

  return NextResponse.json({
    reasoning,
    technical_analysis,
    thinking: normalizeText(thinking)
  });
}

function splitThinkingAndAnalysis(text: string) {
  const detailsRegex = /<details[^>]*>([\s\S]*?)<\/details>/i;
  const match = text.match(detailsRegex);
  
  if (match) {
    let rawThinking = match[1] || '';
    // Remove summary tag
    rawThinking = rawThinking.replace(/<summary>[^<]*<\/summary>/i, '');
    const thinking = stripHtml(rawThinking).trim();
    
    // The rest is analysis
    const analysis = text.replace(detailsRegex, '').trim();
    return { thinking, analysis };
  }
  
  return { thinking: '', analysis: text };
}

function stripHtml(s: string) {
  return s.replace(/<[^>]+>/g, "");
}

function normalizeText(s: string) {
  return s
    .replace(/[\t ]+/g, " ")
    .replace(/\r\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function markdownToPlain(s: string) {
  let text = s;
  text = text.replace(/```[\s\S]*?```/g, "");
  text = text.replace(/`([^`]+)`/g, "$1");
  text = text.replace(/^#{1,6}\s*(.+)$/gm, "\n【$1】\n\n");
  text = text.replace(/\*\*(.+?)\*\*/g, "【$1】");
  text = text.replace(/(^|\n)\s*[-*]\s+/g, "$1• ");
  text = text.replace(/(\n• .+)(\n(• .+))+?/g, (m) => `\n${m}\n\n`);
  text = text.replace(/\n{3,}/g, "\n\n");
  text = text.replace(/【{2,}/g, "【");
  text = text.replace(/】{2,}/g, "】");
  return text;
}

function addSentenceBreaks(s: string) {
  let t = s;
  t = t.replace(/([。！？])(?![”’）\)])/g, '$1\n');
  t = t.replace(/([.!?])\s+(?=[A-Z])/g, '$1\n');
  t = t.replace(/\n\s*•\s+/g, '\n• ');
  t = t.replace(/\n{3,}/g, '\n\n');
  return t.trim();
}

function extractReasoning(reasoning: string, prompt: string) {
    return normalizeText(stripHtml(reasoning));
}

function extractTA(s: string) {
  // Since we pre-split, 's' is now just the analysis part (after </details>)
  let text = stripHtml(s);
  
  // Still keep this cleanup just in case
  let start = text.indexOf("EXTERNAL TECHNICAL ANALYSIS");
  if (start >= 0) {
    text = text.slice(start);
    text = text.replace(/^.*EXTERNAL TECHNICAL ANALYSIS[^\n]*\n?/, "");
  }
  
  const stops = [
    "DATA FOR ",
    "PORTFOLIO SNAPSHOT",
    "BACKTEST STATE",
    "STRATEGY FLAGS",
    "STRATEGY CORRECTIONS",
  ];
  const stopIndexes = stops
    .map((m) => text.indexOf(m))
    .filter((i) => i >= 0);
  if (stopIndexes.length > 0) {
    const end = Math.min(...stopIndexes);
    text = text.slice(0, end);
  }
  text = markdownToPlain(text);
  text = addSentenceBreaks(text);
  return normalizeText(text);
}
