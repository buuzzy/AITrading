import { NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs';

export const dynamic = 'force-dynamic';

export async function POST(request: Request) {
  try {
    const { messages } = await request.json();

    if (!messages || !Array.isArray(messages)) {
      return NextResponse.json({ error: 'Messages array is required' }, { status: 400 });
    }

    // Environment Setup
    const pythonScript = path.join(process.cwd(), 'specs/demo/strategy_generator.py');
    const venvPython = path.join(process.cwd(), 'venv/bin/python');
    const pythonCmd = fs.existsSync(venvPython) ? venvPython : 'python3';

    // Prepare messages JSON string
    const messagesJson = JSON.stringify(messages);

    console.log(`[Strategy Chat] Starting R1 stream via STDIN...`);

    const encoder = new TextEncoder();

    const stream = new ReadableStream({
      start(controller) {
        // Remove 'messagesJson' from args, we will write it to stdin
        const child = spawn(pythonCmd, ['-u', pythonScript]);

        // --- STDIN WRITING ---
        child.stdin.write(messagesJson);
        child.stdin.end(); // Important: Close stdin so Python knows input is done
        // ---------------------

        child.stdout.on('data', (data) => {
          controller.enqueue(data);
        });

        child.stderr.on('data', (data) => {
          console.error(`[Strategy Chat] Stderr: ${data}`);
          // Optional: Forward stderr as error json if critical
        });

        child.on('close', (code) => {
          if (code !== 0) {
             // If Python exits with error, frontend will see the stream end.
             // Usually the script itself would have printed an error JSON before exiting.
             console.log(`[Strategy Chat] Exited with code ${code}`);
          }
          controller.close();
        });

        child.on('error', (err) => {
          const errorJson = JSON.stringify({ type: 'error', message: `Spawn Error: ${err.message}` }) + "\n";
          controller.enqueue(encoder.encode(errorJson));
          controller.close();
        });
      }
    });

    return new Response(stream, {
      headers: {
        'Content-Type': 'application/x-ndjson',
        'Transfer-Encoding': 'chunked',
      },
    });

  } catch (error: any) {
    console.error('[Strategy Chat] Error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}